"""
Rotas de Administração de Usuários
Dashboard completo para gerenciar usuários e métricas da plataforma.
"""

import csv
import json
import logging
import os
import traceback
import zipfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO, StringIO

from flask import (
    Response,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import and_, func

from app import db, limiter
from app.admin import bp
from app.decorators import master_required, validate_with_schema
from app.models import (
    AICreditConfig,
    AIGeneration,
    AuditLog,
    BillingPlan,
    Client,
    CreditPackage,
    CreditTransaction,
    Payment,
    PetitionModel,
    PetitionModelSection,
    PetitionSection,
    PetitionType,
    PetitionUsage,
    PromoCoupon,
    RoadmapCategory,
    RoadmapFeedback,
    RoadmapItem,
    SavedPetition,
    User,
    UserCredits,
    UserPlan,
)
from app.rate_limits import ADMIN_API_LIMIT, COUPON_LIMIT
from app.schemas import (
    BillingPlanSchema,
    PetitionModelSchema,
    PetitionSectionSchema,
    PetitionTypeSchema,
    RoadmapCategorySchema,
    RoadmapItemSchema,
)
from app.utils.audit import AuditManager


# === Funções Helper para Compatibilidade SQLite/PostgreSQL ===
def _is_sqlite():
    """Detecta se está usando SQLite"""
    try:
        return "sqlite" in str(db.engine.url)
    except Exception:
        return False


def _date_trunc_month(column):
    """Trunca data para início do mês de forma compatível com SQLite e PostgreSQL"""
    if _is_sqlite():
        # SQLite: usar strftime para extrair ano-mês e depois converter de volta
        return func.strftime("%Y-%m-01", column)
    else:
        # PostgreSQL: usar date_trunc nativo
        return func.date_trunc("month", column)


# Configurar logging específico para admin
admin_logger = logging.getLogger("admin")
admin_logger.setLevel(logging.DEBUG)

# Criar handler para arquivo
admin_log_file = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs", "admin.log"
)
os.makedirs(os.path.dirname(admin_log_file), exist_ok=True)

admin_file_handler = logging.FileHandler(admin_log_file, encoding="utf-8")
admin_file_handler.setLevel(logging.DEBUG)

# Criar formatter
admin_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
)
admin_file_handler.setFormatter(admin_formatter)

# Adicionar handler ao logger
if not admin_logger.handlers:
    admin_logger.addHandler(admin_file_handler)
from app.utils import generate_unique_slug


def _require_admin():
    """Verifica se o usuário é admin (master)"""
    if not current_user.is_authenticated:
        admin_logger.warning("Tentativa de acesso admin sem autenticação")
        abort(403)

    if current_user.user_type != "master":
        admin_logger.warning(
            f"Usuário {current_user.email} (tipo: {current_user.user_type}) tentou acessar área admin sem permissões"
        )
        abort(403)

    admin_logger.info(f"Usuário admin {current_user.email} acessou área administrativa")


def _get_dashboard_alerts():
    """Gera alertas para métricas críticas dos dashboards"""
    alerts = []
    now = datetime.now(timezone.utc)

    # === Alerta: Churn Rate Alto (último mês > 5%) ===
    last_month_start = now - timedelta(days=30)
    last_month_end = now

    churned_last_month = UserPlan.query.filter(
        UserPlan.renewal_date >= last_month_start,
        UserPlan.renewal_date < last_month_end,
        UserPlan.status == "canceled",
    ).count()

    active_last_month = UserPlan.query.filter(
        UserPlan.started_at < last_month_start,
        db.or_(
            UserPlan.renewal_date.is_(None), UserPlan.renewal_date >= last_month_start
        ),
        UserPlan.status.in_(["active", "canceled"]),
    ).count()

    churn_rate = (
        (churned_last_month / active_last_month * 100) if active_last_month > 0 else 0
    )

    if churn_rate > 5:
        alerts.append(
            {
                "type": "warning",
                "title": "Churn Rate Elevado",
                "message": f"Taxa de cancelamento do último mês: {churn_rate:.1f}% (meta: < 5%)",
                "icon": "fas fa-exclamation-triangle",
            }
        )

    # === Alerta: Receita em Queda (comparação mês atual vs anterior) ===
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)

    current_revenue = (
        db.session.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(
            Payment.paid_at >= current_month_start,
            Payment.payment_status == "completed",
        )
        .scalar()
        or 0
    )

    last_month_revenue = (
        db.session.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(
            Payment.paid_at >= last_month_start,
            Payment.paid_at < current_month_start,
            Payment.payment_status == "completed",
        )
        .scalar()
        or 0
    )

    if last_month_revenue > 0:
        revenue_change = (
            (current_revenue - last_month_revenue) / last_month_revenue
        ) * 100
        if revenue_change < -10:  # Queda > 10%
            alerts.append(
                {
                    "type": "danger",
                    "title": "Queda na Receita",
                    "message": f"Receita mensal caiu {abs(revenue_change):.1f}% em relação ao mês anterior",
                    "icon": "fas fa-chart-line",
                }
            )

    # === Alerta: Usuários Inativos (não logam há 30+ dias) ===
    # Comentado pois User não tem campo last_login_at
    # thirty_days_ago = now - timedelta(days=30)
    # inactive_users = User.query.filter(
    #     User.last_login_at < thirty_days_ago,
    #     User.is_active.is_(True),
    #     User.user_type != "master",
    # ).count()

    # total_active_users = User.query.filter(
    #     User.is_active.is_(True), User.user_type != "master"
    # ).count()

    # if total_active_users > 0:
    #     inactive_percentage = (inactive_users / total_active_users) * 100
    #     if inactive_percentage > 30:  # Mais de 30% inativos
    #         alerts.append(
    #             {
    #                 "type": "info",
    #                 "title": "Usuários Inativos",
    #                 "message": f"{inactive_percentage:.1f}% dos usuários não fazem login há mais de 30 dias",
    #                 "icon": "fas fa-user-clock",
    #             }
    #         )

    # === Alerta: Créditos Baixos (usuários com menos de 10 créditos) ===
    low_credit_users = (
        UserCredits.query.filter(
            UserCredits.balance < 10,
            UserCredits.balance > 0,  # Ainda têm alguns créditos
        )
        .join(User)
        .filter(User.is_active.is_(True))
        .count()
    )

    if low_credit_users > 0:
        alerts.append(
            {
                "type": "warning",
                "title": "Usuários com Créditos Baixos",
                "message": f"{low_credit_users} usuários têm menos de 10 créditos restantes",
                "icon": "fas fa-coins",
            }
        )

    # === Alerta: Erros de Sistema (últimas 24h) ===
    # Nota: Isso seria implementado se houvesse logging de erros estruturado
    # Por enquanto, é um placeholder para futura implementação

    return alerts


@bp.route("/usuarios")
@login_required
@master_required
@limiter.limit(ADMIN_API_LIMIT)
def users_list():
    """Lista todos os usuários com métricas detalhadas"""
    from sqlalchemy.orm import joinedload

    try:
        admin_logger.info(f"Admin {current_user.email} acessando lista de usuários")

        # Parâmetros de filtro e ordenação
        search = request.args.get("search", "").strip()
        status_filter = request.args.get("status", "all")
        user_type_filter = request.args.get("user_type", "all")
        sort_by = request.args.get("sort", "created_at")
        sort_order = request.args.get("order", "desc")
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)

        admin_logger.debug(
            f"Filtros aplicados - search: '{search}', status: {status_filter}, type: {user_type_filter}"
        )

        # Query base com eager loading para evitar N+1
        # Nota: subscriptions é dinâmico e não pode usar eager loading
        query = User.query

        # Filtro de busca
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                db.or_(
                    User.username.ilike(search_term),
                    User.email.ilike(search_term),
                    User.full_name.ilike(search_term),
                    User.oab_number.ilike(search_term),
                )
            )

        # Filtro de status
        if status_filter == "active":
            query = query.filter(User.is_active.is_(True))
        elif status_filter == "inactive":
            query = query.filter(User.is_active.is_(False))
        elif status_filter == "delinquent":
            query = query.filter(User.billing_status == "delinquent")
        elif status_filter == "trial":
            query = query.filter(User.billing_status == "trial")

        # Filtro de tipo de usuário
        if user_type_filter != "all":
            query = query.filter(User.user_type == user_type_filter)

        # Ordenação
        sort_column = getattr(User, sort_by, User.created_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Paginação
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        users = pagination.items

        # Calcular métricas em bulk (evita N+1 queries)
        users_with_metrics = _get_bulk_user_metrics(users)

        admin_logger.info(
            f"Lista de usuários carregada: {len(users)} usuários encontrados (página {page})"
        )

        return render_template(
            "admin/users_list.html",
            title="Gerenciar Usuários",
            users=users_with_metrics,
            pagination=pagination,
            search=search,
            status_filter=status_filter,
            user_type_filter=user_type_filter,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    except Exception as e:
        admin_logger.error(
            f"Erro ao carregar lista de usuários para {current_user.email}: {str(e)}"
        )
        admin_logger.error(f"Traceback: {traceback.format_exc()}")

        # Importar helper de mensagens de erro
        from app.utils.error_messages import format_error_for_user

        # Determinar tipo de erro baseado na mensagem
        error_msg = str(e).lower()
        error_type = (
            "database" if "database" in error_msg or "sql" in error_msg else "general"
        )

        # Exibir erro real ou genérico baseado na configuração
        user_message = format_error_for_user(e, error_type)
        flash(user_message, "danger")
        return redirect(url_for("admin.dashboard"))


@bp.route("/usuarios/<int:user_id>")
@login_required
def user_detail(user_id):
    """Detalhes completos de um usuário"""
    _require_admin()

    user = User.query.get_or_404(user_id)
    metrics = _get_user_metrics(user, detailed=True)

    # Histórico de petições
    petitions = (
        PetitionUsage.query.filter_by(user_id=user_id)
        .order_by(PetitionUsage.generated_at.desc())
        .limit(20)
        .all()
    )

    # Histórico de gerações IA
    ai_generations = (
        AIGeneration.query.filter_by(user_id=user_id)
        .order_by(AIGeneration.created_at.desc())
        .limit(20)
        .all()
    )

    # Histórico de transações de créditos
    credit_transactions = (
        CreditTransaction.query.filter_by(user_id=user_id)
        .order_by(CreditTransaction.created_at.desc())
        .limit(20)
        .all()
    )

    # Histórico de pagamentos
    payments = (
        Payment.query.filter_by(user_id=user_id)
        .order_by(Payment.paid_at.desc())
        .limit(20)
        .all()
    )

    return render_template(
        "admin/user_detail.html",
        title=f"Usuário: {user.full_name or user.username}",
        user=user,
        metrics=metrics,
        petitions=petitions,
        ai_generations=ai_generations,
        credit_transactions=credit_transactions,
        payments=payments,
    )


@bp.route("/usuarios/<int:user_id>/toggle-status", methods=["POST"])
@login_required
def toggle_user_status(user_id):
    """Ativa/desativa um usuário"""
    _require_admin()

    user = User.query.get_or_404(user_id)

    if user.user_type in ["master", "admin"]:
        flash("Não é possível desativar um usuário administrador.", "danger")
        return redirect(url_for("admin.users_list"))

    user.is_active = not user.is_active
    db.session.commit()

    status = "ativado" if user.is_active else "desativado"
    flash(f"Usuário {user.username} foi {status} com sucesso.", "success")

    return redirect(url_for("admin.user_detail", user_id=user_id))


@bp.route("/usuarios/<int:user_id>/add-credits", methods=["POST"])
@login_required
def add_user_credits(user_id):
    """Adiciona créditos de IA para um usuário (bônus admin)"""
    _require_admin()

    user = User.query.get_or_404(user_id)
    amount = request.form.get("amount", 0, type=int)
    reason = request.form.get("reason", "Bônus administrativo")

    if amount <= 0:
        flash("A quantidade de créditos deve ser maior que zero.", "danger")
        return redirect(url_for("admin.user_detail", user_id=user_id))

    # Obtém ou cria registro de créditos
    user_credits = UserCredits.get_or_create(user.id)

    # Adiciona os créditos
    new_balance = user_credits.add_credits(amount, source="bonus")

    # Registra a transação
    transaction = CreditTransaction(
        user_id=user.id,
        transaction_type="bonus",
        amount=amount,
        balance_after=new_balance,
        description=f"Bônus admin: {reason}",
    )
    db.session.add(transaction)
    db.session.commit()

    flash(
        f"{amount} créditos adicionados para {user.username}. Novo saldo: {new_balance}",
        "success",
    )

    return redirect(url_for("admin.user_detail", user_id=user_id))


@bp.route("/usuarios/<int:user_id>/manage-trial", methods=["POST"])
@login_required
def manage_user_trial(user_id):
    """Gerencia o período de trial de um usuário"""
    _require_admin()

    user = User.query.get_or_404(user_id)
    action = request.form.get("action")

    if action == "start":
        days = request.form.get(
            "trial_days", current_app.config["DEFAULT_TRIAL_DAYS"], type=int
        )
        if days <= 0:
            flash("A quantidade de dias deve ser maior que zero.", "danger")
        else:
            user.start_trial(days)
            db.session.commit()
            flash(
                f"Período de teste de {days} dias iniciado para {user.username}.",
                "success",
            )

    elif action == "end":
        user.end_trial()
        db.session.commit()
        flash(f"Período de teste encerrado para {user.username}.", "success")

    elif action == "extend":
        additional_days = request.form.get("additional_days", 7, type=int)
        if additional_days <= 0:
            flash("A quantidade de dias deve ser maior que zero.", "danger")
        else:
            if user.trial_active and user.trial_days:
                user.trial_days += additional_days
                db.session.commit()
                flash(
                    f"Trial estendido em {additional_days} dias para {user.username}.",
                    "success",
                )
            else:
                flash("Usuário não está em período de teste ativo.", "warning")

    return redirect(url_for("admin.user_detail", user_id=user_id))


@bp.route("/dashboard")
@login_required
def dashboard():
    """Dashboard administrativo com visão geral da plataforma"""
    _require_admin()

    # Período atual
    now = datetime.now(timezone.utc)
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)

    # Data de 12 meses atrás para as queries agregadas
    twelve_months_ago = now - timedelta(days=365)

    # === DADOS PARA GRÁFICOS - Últimos 12 meses ===
    chart_labels = []
    chart_revenue = []
    chart_revenue_by_plan = {}
    chart_ai_usage = []
    chart_ai_cost = []
    chart_ai_credits_sold = []

    # Buscar planos existentes
    all_plans = BillingPlan.query.filter(BillingPlan.active.is_(True)).all()
    for plan in all_plans:
        chart_revenue_by_plan[plan.name] = []
    chart_revenue_by_plan["Avulso"] = []

    # Gerar labels dos meses
    month_ranges = []
    for i in range(11, -1, -1):
        month_date = now - timedelta(days=i * 30)
        month_start = month_date.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        if i > 0:
            next_month = month_date + timedelta(days=32)
            month_end = next_month.replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
        else:
            month_end = now
        chart_labels.append(month_start.strftime("%b/%y"))
        month_ranges.append((month_start, month_end))

    # Query agregada: Faturamento por mês
    revenue_by_month = dict(
        db.session.query(
            _date_trunc_month(Payment.paid_at),
            func.coalesce(func.sum(Payment.amount), 0),
        )
        .filter(
            Payment.paid_at >= twelve_months_ago, Payment.payment_status == "completed"
        )
        .group_by(_date_trunc_month(Payment.paid_at))
        .all()
    )

    # Query agregada: Uso de IA por mês
    ai_by_month = dict(
        db.session.query(
            _date_trunc_month(AIGeneration.created_at),
            func.count(AIGeneration.id),
        )
        .filter(AIGeneration.created_at >= twelve_months_ago)
        .group_by(_date_trunc_month(AIGeneration.created_at))
        .all()
    )

    # Query agregada: Custo de IA por mês
    ai_cost_by_month = dict(
        db.session.query(
            _date_trunc_month(AIGeneration.created_at),
            func.coalesce(func.sum(AIGeneration.cost_usd), 0),
        )
        .filter(AIGeneration.created_at >= twelve_months_ago)
        .group_by(_date_trunc_month(AIGeneration.created_at))
        .all()
    )

    # Query agregada: Créditos vendidos por mês
    credits_by_month = dict(
        db.session.query(
            _date_trunc_month(CreditTransaction.created_at),
            func.coalesce(func.sum(CreditTransaction.amount), 0),
        )
        .filter(
            CreditTransaction.created_at >= twelve_months_ago,
            CreditTransaction.transaction_type == "purchase",
        )
        .group_by(_date_trunc_month(CreditTransaction.created_at))
        .all()
    )

    # Preencher arrays dos gráficos a partir das queries agregadas
    for month_start, month_end in month_ranges:
        month_key = month_start.replace(tzinfo=None)

        # Faturamento
        chart_revenue.append(float(revenue_by_month.get(month_key, 0)))

        # Uso de IA
        chart_ai_usage.append(int(ai_by_month.get(month_key, 0)))

        # Custo de IA
        chart_ai_cost.append(float(ai_cost_by_month.get(month_key, 0)))

        # Créditos vendidos
        chart_ai_credits_sold.append(int(credits_by_month.get(month_key, 0)))

        # Placeholder para faturamento por plano (simplificado)
        for plan in all_plans:
            chart_revenue_by_plan[plan.name].append(0)
        chart_revenue_by_plan["Avulso"].append(0)

    # === Métricas de Usuários ===
    total_users = User.query.filter(User.user_type != "master").count()
    active_users = User.query.filter(
        User.is_active.is_(True), User.user_type != "master"
    ).count()
    new_users_month = User.query.filter(
        User.created_at >= current_month_start, User.user_type != "master"
    ).count()
    new_users_last_month = User.query.filter(
        User.created_at >= last_month_start,
        User.created_at < current_month_start,
        User.user_type != "master",
    ).count()

    # === Métricas de Clientes ===
    total_clients = Client.query.count()
    new_clients_month = Client.query.filter(
        Client.created_at >= current_month_start
    ).count()

    # === Métricas de Petições ===
    total_petitions = PetitionUsage.query.count()
    petitions_month = PetitionUsage.query.filter(
        PetitionUsage.generated_at >= current_month_start
    ).count()
    petitions_last_month = PetitionUsage.query.filter(
        PetitionUsage.generated_at >= last_month_start,
        PetitionUsage.generated_at < current_month_start,
    ).count()

    # Valor total de petições no mês
    petitions_value_month = db.session.query(
        func.coalesce(func.sum(PetitionUsage.amount), 0)
    ).filter(PetitionUsage.generated_at >= current_month_start).scalar() or Decimal(
        "0.00"
    )

    # === Métricas de IA ===
    ai_generations_month = AIGeneration.query.filter(
        AIGeneration.created_at >= current_month_start
    ).count()

    # Tokens usados no mês
    tokens_month = (
        db.session.query(func.coalesce(func.sum(AIGeneration.tokens_total), 0))
        .filter(AIGeneration.created_at >= current_month_start)
        .scalar()
        or 0
    )

    # Custo de IA no mês (em USD)
    ai_cost_month = db.session.query(
        func.coalesce(func.sum(AIGeneration.cost_usd), 0)
    ).filter(AIGeneration.created_at >= current_month_start).scalar() or Decimal("0.00")

    # Créditos vendidos no mês
    credits_sold_month = (
        db.session.query(func.coalesce(func.sum(CreditTransaction.amount), 0))
        .filter(
            CreditTransaction.created_at >= current_month_start,
            CreditTransaction.transaction_type == "purchase",
        )
        .scalar()
        or 0
    )

    # === Métricas Financeiras ===
    # Pagamentos do mês
    payments_month = db.session.query(
        func.coalesce(func.sum(Payment.amount), 0)
    ).filter(
        Payment.paid_at >= current_month_start, Payment.payment_status == "completed"
    ).scalar() or Decimal("0.00")

    # Usuários pagantes (com plano ativo)
    paying_users = (
        User.query.join(UserPlan)
        .filter(UserPlan.status == "active", UserPlan.is_current.is_(True))
        .distinct()
        .count()
    )

    # === Top Usuários (mais petições no mês) ===
    top_users_petitions = (
        db.session.query(
            User.id,
            User.username,
            User.full_name,
            User.email,
            func.count(PetitionUsage.id).label("petition_count"),
            func.coalesce(func.sum(PetitionUsage.amount), 0).label("total_value"),
        )
        .join(PetitionUsage, User.id == PetitionUsage.user_id)
        .filter(PetitionUsage.generated_at >= current_month_start)
        .group_by(User.id, User.username, User.full_name, User.email)
        .order_by(func.count(PetitionUsage.id).desc())
        .limit(10)
        .all()
    )

    # === Top Usuários (mais uso de IA no mês) ===
    top_users_ai = (
        db.session.query(
            User.id,
            User.username,
            User.full_name,
            func.count(AIGeneration.id).label("generation_count"),
            func.coalesce(func.sum(AIGeneration.tokens_total), 0).label("total_tokens"),
            func.coalesce(func.sum(AIGeneration.cost_usd), 0).label("total_cost"),
        )
        .join(AIGeneration, User.id == AIGeneration.user_id)
        .filter(AIGeneration.created_at >= current_month_start)
        .group_by(User.id, User.username, User.full_name)
        .order_by(func.sum(AIGeneration.tokens_total).desc())
        .limit(10)
        .all()
    )

    # === Usuários recentes ===
    recent_users = (
        User.query.filter(User.user_type != "master")
        .order_by(User.created_at.desc())
        .limit(10)
        .all()
    )

    return render_template(
        "admin/dashboard.html",
        title="Dashboard Administrativo",
        # Usuários
        total_users=total_users,
        active_users=active_users,
        new_users_month=new_users_month,
        new_users_last_month=new_users_last_month,
        paying_users=paying_users,
        # Clientes
        total_clients=total_clients,
        new_clients_month=new_clients_month,
        # Petições
        total_petitions=total_petitions,
        petitions_month=petitions_month,
        petitions_last_month=petitions_last_month,
        petitions_value_month=petitions_value_month,
        # IA
        ai_generations_month=ai_generations_month,
        tokens_month=tokens_month,
        ai_cost_month=ai_cost_month,
        credits_sold_month=credits_sold_month,
        # Financeiro
        payments_month=payments_month,
        # Tops
        top_users_petitions=top_users_petitions,
        top_users_ai=top_users_ai,
        recent_users=recent_users,
        # Datas
        current_month=now.strftime("%B %Y"),
        # Dados para gráficos
        chart_labels=chart_labels,
        chart_revenue=chart_revenue,
        chart_revenue_by_plan=chart_revenue_by_plan,
        chart_ai_usage=chart_ai_usage,
        chart_ai_cost=chart_ai_cost,
        chart_ai_credits_sold=chart_ai_credits_sold,
        # Dashboard ativo
        active_dashboard="overview",
    )


@bp.route("/dashboard/regional")
@login_required
def dashboard_regional():
    """Dashboard focado em análise regional"""
    _require_admin()

    # Parâmetros de filtro
    period = request.args.get(
        "period", "all", type=str
    )  # all, 30days, 90days, 6months, 1year
    plan_filter = request.args.get("plan", "all", type=str)
    status_filter = request.args.get("status", "all", type=str)

    # Calcular datas baseado no período
    now = datetime.now(timezone.utc)
    if period == "30days":
        start_date = now - timedelta(days=30)
    elif period == "90days":
        start_date = now - timedelta(days=90)
    elif period == "6months":
        start_date = now - timedelta(days=180)
    elif period == "1year":
        start_date = now - timedelta(days=365)
    else:  # all
        start_date = None

    # === DISTRIBUIÇÃO DE USUÁRIOS POR UF ===
    users_query = db.session.query(
        User.uf,
        func.count(User.id).label("user_count"),
        func.count(User.id).filter(User.is_active.is_(True)).label("active_count"),
        func.count(User.id)
        .filter(User.created_at >= _date_trunc_month(func.now()))
        .label("new_this_month"),
    ).filter(User.uf.isnot(None), User.uf != "", User.user_type != "master")

    # Aplicar filtros
    if start_date:
        users_query = users_query.filter(User.created_at >= start_date)
    if status_filter == "active":
        users_query = users_query.filter(User.is_active.is_(True))
    elif status_filter == "inactive":
        users_query = users_query.filter(User.is_active.is_(False))
    if plan_filter != "all":
        if plan_filter == "free":
            users_query = users_query.filter(
                ~User.user_plans.any()
            )  # Usuários sem plano
        else:
            users_query = (
                users_query.join(UserPlan)
                .join(BillingPlan)
                .filter(
                    BillingPlan.name == plan_filter,
                    UserPlan.status == "active",
                    UserPlan.is_current.is_(True),
                )
            )

    users_by_uf = (
        users_query.group_by(User.uf).order_by(func.count(User.id).desc()).all()
    )

    # === PETIÇÕES POR UF ===
    petitions_query = (
        db.session.query(
            User.uf,
            func.count(PetitionUsage.id).label("petition_count"),
            func.coalesce(func.sum(PetitionUsage.amount), 0).label("total_value"),
            func.avg(PetitionUsage.amount).label("avg_value"),
        )
        .join(PetitionUsage, User.id == PetitionUsage.user_id)
        .filter(User.uf.isnot(None), User.uf != "")
    )

    if start_date:
        petitions_query = petitions_query.filter(
            PetitionUsage.generated_at >= start_date
        )

    petitions_by_uf = (
        petitions_query.group_by(User.uf)
        .order_by(func.count(PetitionUsage.id).desc())
        .all()
    )

    # === RECEITA POR UF ===
    revenue_query = (
        db.session.query(
            User.uf,
            func.coalesce(func.sum(Payment.amount), 0).label("total_revenue"),
            func.count(Payment.id).label("payment_count"),
        )
        .join(Payment, User.id == Payment.user_id)
        .filter(
            User.uf.isnot(None), User.uf != "", Payment.payment_status == "completed"
        )
    )

    if start_date:
        revenue_query = revenue_query.filter(Payment.paid_at >= start_date)

    revenue_by_uf = (
        revenue_query.group_by(User.uf)
        .order_by(func.coalesce(func.sum(Payment.amount), 0).desc())
        .all()
    )

    # === TOP CIDADES ===
    cities_query = db.session.query(
        User.uf,
        User.city,
        func.count(User.id).label("user_count"),
    ).filter(
        User.uf.isnot(None),
        User.uf != "",
        User.city.isnot(None),
        User.city != "",
        User.user_type != "master",
    )

    if start_date:
        cities_query = cities_query.filter(User.created_at >= start_date)
    if status_filter == "active":
        cities_query = cities_query.filter(User.is_active.is_(True))
    elif status_filter == "inactive":
        cities_query = cities_query.filter(User.is_active.is_(False))

    users_by_city = (
        cities_query.group_by(User.uf, User.city)
        .order_by(func.count(User.id).desc())
        .limit(20)
        .all()
    )

    # === CRESCIMENTO REGIONAL (últimos 6 meses) ===
    regional_growth = []
    for months_back in range(5, -1, -1):
        start_date_growth = datetime.now(timezone.utc) - timedelta(
            days=30 * months_back
        )
        end_date_growth = start_date_growth + timedelta(days=30)

        growth_data = (
            db.session.query(
                User.uf,
                func.count(User.id).label("new_users"),
            )
            .filter(
                User.created_at >= start_date_growth,
                User.created_at < end_date_growth,
                User.uf.isnot(None),
                User.uf != "",
                User.user_type != "master",
            )
            .group_by(User.uf)
            .all()
        )

        regional_growth.append(
            {
                "month": start_date_growth.strftime("%Y-%m"),
                "data": {item.uf: item.new_users for item in growth_data},
            }
        )

    # Opções para filtros
    plan_options = ["all"] + [
        plan.name
        for plan in BillingPlan.query.filter(BillingPlan.active.is_(True)).all()
    ]

    # Alertas do dashboard
    alerts = _get_dashboard_alerts()

    # Tendências
    trends = _calculate_trends()

    return render_template(
        "admin/dashboard_regional.html",
        title="Dashboard Regional",
        users_by_uf=users_by_uf,
        petitions_by_uf=petitions_by_uf,
        revenue_by_uf=revenue_by_uf,
        users_by_city=users_by_city,
        regional_growth=regional_growth,
        active_dashboard="regional",
        # Filtros
        period=period,
        plan_filter=plan_filter,
        status_filter=status_filter,
        plan_options=plan_options,
        # Alertas
        alerts=alerts,
        # Tendências
        trends=trends,
    )


@bp.route("/dashboard/peticoes")
@login_required
def dashboard_peticoes():
    """Dashboard focado em análise de petições"""
    _require_admin()

    # Parâmetros de filtro
    period = request.args.get(
        "period", "30days", type=str
    )  # 7days, 30days, 90days, 6months, 1year
    plan_filter = request.args.get("plan", "all", type=str)
    status_filter = request.args.get("status", "all", type=str)

    # Calcular datas baseado no período
    now = datetime.now(timezone.utc)
    if period == "7days":
        start_date = now - timedelta(days=7)
        days_range = 7
    elif period == "30days":
        start_date = now - timedelta(days=30)
        days_range = 30
    elif period == "90days":
        start_date = now - timedelta(days=90)
        days_range = 90
    elif period == "6months":
        start_date = now - timedelta(days=180)
        days_range = 180
    elif period == "1year":
        start_date = now - timedelta(days=365)
        days_range = 365
    else:
        start_date = now - timedelta(days=30)
        days_range = 30

    # === PETIÇÕES POR TIPO ===
    petitions_query = db.session.query(
        PetitionUsage.petition_type,
        func.count(PetitionUsage.id).label("count"),
        func.coalesce(func.sum(PetitionUsage.amount), 0).label("total_value"),
        func.avg(PetitionUsage.amount).label("avg_value"),
    )

    if start_date:
        petitions_query = petitions_query.filter(
            PetitionUsage.generated_at >= start_date
        )

    # Aplicar filtros de usuário se necessário
    if plan_filter != "all" or status_filter != "all":
        petitions_query = petitions_query.join(User, PetitionUsage.user_id == User.id)

        if status_filter == "active":
            petitions_query = petitions_query.filter(User.is_active.is_(True))
        elif status_filter == "inactive":
            petitions_query = petitions_query.filter(User.is_active.is_(False))

        if plan_filter != "all":
            if plan_filter == "free":
                petitions_query = petitions_query.filter(~User.user_plans.any())
            else:
                petitions_query = (
                    petitions_query.join(UserPlan)
                    .join(BillingPlan)
                    .filter(
                        BillingPlan.name == plan_filter,
                        UserPlan.status == "active",
                        UserPlan.is_current.is_(True),
                    )
                )

    petitions_by_type = (
        petitions_query.group_by(PetitionUsage.petition_type)
        .order_by(func.count(PetitionUsage.id).desc())
        .all()
    )

    # === PETIÇÕES POR DIA ===
    petitions_daily = []
    for days_back in range(days_range - 1, -1, -1):
        date = now - timedelta(days=days_back)
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_start + timedelta(days=1)

        count = PetitionUsage.query.filter(
            PetitionUsage.generated_at >= date_start,
            PetitionUsage.generated_at < date_end,
        ).count()

        value = (
            db.session.query(func.coalesce(func.sum(PetitionUsage.amount), 0))
            .filter(
                PetitionUsage.generated_at >= date_start,
                PetitionUsage.generated_at < date_end,
            )
            .scalar()
            or 0
        )

        petitions_daily.append(
            {"date": date.strftime("%Y-%m-%d"), "count": count, "value": float(value)}
        )

    # === TOP PETIÇÕES POR USUÁRIO ===
    top_users_query = db.session.query(
        User.username,
        User.full_name,
        User.uf,
        func.count(PetitionUsage.id).label("petition_count"),
        func.coalesce(func.sum(PetitionUsage.amount), 0).label("total_value"),
        func.max(PetitionUsage.generated_at).label("last_petition"),
    ).join(PetitionUsage, User.id == PetitionUsage.user_id)

    if start_date:
        top_users_query = top_users_query.filter(
            PetitionUsage.generated_at >= start_date
        )

    if status_filter == "active":
        top_users_query = top_users_query.filter(User.is_active.is_(True))
    elif status_filter == "inactive":
        top_users_query = top_users_query.filter(User.is_active.is_(False))

    if plan_filter != "all":
        if plan_filter == "free":
            top_users_query = top_users_query.filter(~User.user_plans.any())
        else:
            top_users_query = (
                top_users_query.join(UserPlan)
                .join(BillingPlan)
                .filter(
                    BillingPlan.name == plan_filter,
                    UserPlan.status == "active",
                    UserPlan.is_current.is_(True),
                )
            )

    top_petition_users = (
        top_users_query.group_by(User.id, User.username, User.full_name, User.uf)
        .order_by(func.count(PetitionUsage.id).desc())
        .limit(20)
        .all()
    )

    # === PETIÇÕES POR HORA DO DIA ===
    petitions_by_hour = []
    for hour in range(24):
        hour_query = db.session.query(func.count(PetitionUsage.id)).filter(
            func.extract("hour", PetitionUsage.generated_at) == hour
        )

        if start_date:
            hour_query = hour_query.filter(PetitionUsage.generated_at >= start_date)

        count = hour_query.scalar() or 0
        petitions_by_hour.append({"hour": hour, "count": count})

    # === CONVERSÃO DE TRIAL PARA PAGO ===
    trial_conversions = (
        db.session.query(
            func.count(User.id).label("total_trials"),
            func.count(User.id)
            .filter(User.billing_status != "trial")
            .label("converted"),
        )
        .filter(User.trial_active.is_(True))
        .first()
    )

    # Opções para filtros
    plan_options = ["all"] + [
        plan.name
        for plan in BillingPlan.query.filter(BillingPlan.active.is_(True)).all()
    ]

    # Alertas do dashboard
    alerts = _get_dashboard_alerts()

    # Tendências
    trends = _calculate_trends()

    return render_template(
        "admin/dashboard_peticoes.html",
        title="Dashboard de Petições",
        petitions_by_type=petitions_by_type,
        petitions_daily=petitions_daily,
        top_petition_users=top_petition_users,
        petitions_by_hour=petitions_by_hour,
        trial_conversions=trial_conversions,
        active_dashboard="peticoes",
        # Filtros
        period=period,
        plan_filter=plan_filter,
        status_filter=status_filter,
        plan_options=plan_options,
        # Alertas
        alerts=alerts,
        # Tendências
        trends=trends,
    )


@bp.route("/dashboard/financeiro")
@login_required
def dashboard_financeiro():
    """Dashboard focado em análise financeira"""
    _require_admin()

    # Parâmetros de filtro
    period = request.args.get(
        "period", "12months", type=str
    )  # 6months, 12months, 24months
    plan_filter = request.args.get("plan", "all", type=str)
    status_filter = request.args.get("status", "all", type=str)

    # Calcular período para análise
    now = datetime.now(timezone.utc)
    if period == "6months":
        months_range = 6
    elif period == "12months":
        months_range = 12
    elif period == "24months":
        months_range = 24
    else:
        months_range = 12

    # === RECEITA POR MÊS ===
    monthly_revenue = []
    for months_back in range(months_range - 1, -1, -1):
        start_date = now - timedelta(days=30 * months_back)
        end_date = start_date + timedelta(days=30)

        revenue_query = db.session.query(
            func.coalesce(func.sum(Payment.amount), 0)
        ).filter(
            Payment.paid_at >= start_date,
            Payment.paid_at < end_date,
            Payment.payment_status == "completed",
        )

        # Aplicar filtros
        if plan_filter != "all":
            revenue_query = revenue_query.join(BillingPlan).filter(
                BillingPlan.name == plan_filter
            )

        if status_filter != "all":
            revenue_query = revenue_query.join(User).filter(
                User.is_active.is_(True)
                if status_filter == "active"
                else User.is_active.is_(False)
            )

        revenue = revenue_query.scalar() or 0

        monthly_revenue.append(
            {"month": start_date.strftime("%Y-%m"), "revenue": float(revenue)}
        )

    # === RECEITA POR PLANO ===
    revenue_plan_query = (
        db.session.query(
            BillingPlan.name,
            func.coalesce(func.sum(PetitionUsage.amount), 0).label("total_revenue"),
            func.count(PetitionUsage.id).label("subscription_count"),
        )
        .join(PetitionUsage, BillingPlan.id == PetitionUsage.plan_id)
        .filter(PetitionUsage.billable.is_(True))
    )

    if period != "all":
        start_date_filter = now - timedelta(days=30 * months_range)
        revenue_plan_query = revenue_plan_query.filter(
            PetitionUsage.generated_at >= start_date_filter
        )

    if status_filter != "all":
        revenue_plan_query = revenue_plan_query.join(
            User, PetitionUsage.user_id == User.id
        ).filter(
            User.is_active.is_(True)
            if status_filter == "active"
            else User.is_active.is_(False)
        )

    revenue_by_plan = (
        revenue_plan_query.group_by(BillingPlan.id, BillingPlan.name)
        .order_by(func.coalesce(func.sum(PetitionUsage.amount), 0).desc())
        .all()
    )

    # === CHURN RATE ===
    churn_data = []
    for months_back in range(months_range - 1, -1, -1):
        start_date = now - timedelta(days=30 * months_back)
        end_date = start_date + timedelta(days=30)

        # Usuários que cancelaram no mês
        churn_query = UserPlan.query.filter(
            UserPlan.renewal_date >= start_date,
            UserPlan.renewal_date < end_date,
            UserPlan.status == "canceled",
        )

        if plan_filter != "all":
            churn_query = churn_query.join(BillingPlan).filter(
                BillingPlan.name == plan_filter
            )

        churned = churn_query.count()

        # Usuários ativos no início do mês
        active_query = UserPlan.query.filter(
            UserPlan.started_at < start_date,
            db.or_(
                UserPlan.renewal_date.is_(None), UserPlan.renewal_date >= start_date
            ),
            UserPlan.status.in_(["active", "canceled"]),
        )

        if plan_filter != "all":
            active_query = active_query.join(BillingPlan).filter(
                BillingPlan.name == plan_filter
            )

        active_start = active_query.count()

        churn_rate = (churned / active_start * 100) if active_start > 0 else 0

        churn_data.append(
            {
                "month": start_date.strftime("%Y-%m"),
                "churned": churned,
                "active_start": active_start,
                "churn_rate": round(churn_rate, 2),
            }
        )

    # === LTV (Lifetime Value) ===
    ltv_query = db.session.query(
        func.avg(Payment.amount).label("avg_payment"),
        func.count(Payment.id).label("total_payments"),
        func.count(Payment.user_id.distinct()).label("unique_users"),
    ).filter(Payment.payment_status == "completed")

    if period != "all":
        start_date_filter = now - timedelta(days=30 * months_range)
        ltv_query = ltv_query.filter(Payment.paid_at >= start_date_filter)

    if plan_filter != "all":
        ltv_query = (
            ltv_query.join(User, Payment.user_id == User.id)
            .join(UserPlan, User.id == UserPlan.user_id)
            .join(BillingPlan, UserPlan.plan_id == BillingPlan.id)
            .filter(BillingPlan.name == plan_filter)
        )

    if status_filter != "all":
        ltv_query = ltv_query.join(User).filter(
            User.is_active.is_(True)
            if status_filter == "active"
            else User.is_active.is_(False)
        )

    ltv_data = ltv_query.first()

    # === RECEITA RECORRENTE MENSAL (MRR) ===
    mrr_query = (
        db.session.query(func.coalesce(func.sum(BillingPlan.monthly_fee), 0))
        .join(UserPlan, BillingPlan.id == UserPlan.plan_id)
        .filter(UserPlan.status == "active", UserPlan.is_current.is_(True))
    )

    if plan_filter != "all":
        mrr_query = mrr_query.filter(BillingPlan.name == plan_filter)

    if status_filter == "active":
        mrr_query = mrr_query.join(User).filter(User.is_active.is_(True))
    elif status_filter == "inactive":
        mrr_query = mrr_query.join(User).filter(User.is_active.is_(False))

    current_mrr = mrr_query.scalar() or 0

    # Opções para filtros
    plan_options = ["all"] + [
        plan.name
        for plan in BillingPlan.query.filter(BillingPlan.active.is_(True)).all()
    ]

    # Alertas do dashboard
    alerts = _get_dashboard_alerts()

    # Tendências
    trends = _calculate_trends()

    return render_template(
        "admin/dashboard_financeiro.html",
        title="Dashboard Financeiro",
        monthly_revenue=monthly_revenue,
        revenue_by_plan=revenue_by_plan,
        churn_data=churn_data,
        ltv_data=ltv_data,
        current_mrr=float(current_mrr),
        active_dashboard="financeiro",
        # Filtros
        period=period,
        plan_filter=plan_filter,
        status_filter=status_filter,
        plan_options=plan_options,
        # Alertas
        alerts=alerts,
        # Tendências
        trends=trends,
    )


@bp.route("/dashboard-financeiro")
@login_required
def dashboard_financeiro_alt():
    """Alias para dashboard financeiro (com hífen) - para compatibilidade com testes"""
    return dashboard_financeiro()


@bp.route("/dashboard/regional/export")
@login_required
def export_dashboard_regional():
    """Exporta dados do dashboard regional em CSV"""
    _require_admin()

    # Parâmetros de filtro
    period = request.args.get("period", "30days", type=str)
    plan_filter = request.args.get("plan", "all", type=str)
    status_filter = request.args.get("status", "all", type=str)

    # Calcular período
    now = datetime.now(timezone.utc)
    if period == "7days":
        days = 7
    elif period == "30days":
        days = 30
    elif period == "90days":
        days = 90
    elif period == "6months":
        days = 180
    elif period == "1year":
        days = 365
    else:
        days = 30

    start_date = now - timedelta(days=days)

    # Query para dados regionais
    query = (
        db.session.query(
            User.state,
            func.count(User.id).label("user_count"),
            func.count(Client.id).label("client_count"),
            func.count(PetitionUsage.id).label("petition_count"),
            func.coalesce(func.sum(Payment.amount), 0).label("revenue"),
        )
        .outerjoin(Client, User.id == Client.lawyer_id)
        .outerjoin(PetitionUsage, User.id == PetitionUsage.user_id)
        .outerjoin(Payment, User.id == Payment.user_id)
        .filter(User.created_at >= start_date, User.user_type != "master")
    )

    # Aplicar filtros
    if plan_filter != "all":
        query = (
            query.join(UserPlan)
            .join(BillingPlan)
            .filter(BillingPlan.name == plan_filter)
        )

    if status_filter != "all":
        query = query.filter(
            User.is_active.is_(True)
            if status_filter == "active"
            else User.is_active.is_(False)
        )

    regional_data = (
        query.group_by(User.state).order_by(func.count(User.id).desc()).all()
    )

    # Criar CSV
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Estado", "Usuários", "Clientes", "Petições", "Receita (R$)"])

    for row in regional_data:
        writer.writerow(
            [
                row.state or "Não informado",
                row.user_count,
                row.client_count,
                row.petition_count,
                f"{row.revenue:.2f}",
            ]
        )

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=dashboard_regional_{period}.csv"
        },
    )


@bp.route("/dashboard/peticoes/export")
@login_required
def export_dashboard_peticoes():
    """Exporta dados do dashboard de petições em CSV"""
    _require_admin()

    # Parâmetros de filtro
    period = request.args.get("period", "30days", type=str)
    plan_filter = request.args.get("plan", "all", type=str)
    status_filter = request.args.get("status", "all", type=str)

    # Calcular período
    now = datetime.now(timezone.utc)
    if period == "7days":
        days = 7
    elif period == "30days":
        days = 30
    elif period == "90days":
        days = 90
    elif period == "6months":
        days = 180
    elif period == "1year":
        days = 365
    else:
        days = 30

    start_date = now - timedelta(days=days)

    # Query para dados de petições
    query = db.session.query(
        PetitionUsage.petition_type,
        func.count(PetitionUsage.id).label("usage_count"),
        func.count(PetitionUsage.user_id.distinct()).label("unique_users"),
        func.avg(PetitionUsage.credits_used).label("avg_credits"),
    ).filter(PetitionUsage.created_at >= start_date)

    # Aplicar filtros
    if plan_filter != "all":
        query = (
            query.join(User)
            .join(UserPlan)
            .join(BillingPlan)
            .filter(BillingPlan.name == plan_filter)
        )

    if status_filter != "all":
        query = query.join(User).filter(
            User.is_active.is_(True)
            if status_filter == "active"
            else User.is_active.is_(False)
        )

    petition_data = (
        query.group_by(PetitionUsage.petition_type)
        .order_by(func.count(PetitionUsage.id).desc())
        .all()
    )

    # Criar CSV
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["Tipo de Petição", "Uso Total", "Usuários Únicos", "Créditos Médios"]
    )

    for row in petition_data:
        writer.writerow(
            [
                row.petition_type,
                row.usage_count,
                row.unique_users,
                f"{row.avg_credits:.2f}" if row.avg_credits else "0.00",
            ]
        )

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=dashboard_peticoes_{period}.csv"
        },
    )


@bp.route("/dashboard/financeiro/export")
@login_required
def export_dashboard_financeiro():
    """Exporta dados do dashboard financeiro em CSV"""
    _require_admin()

    # Parâmetros de filtro
    period = request.args.get("period", "12months", type=str)
    plan_filter = request.args.get("plan", "all", type=str)
    status_filter = request.args.get("status", "all", type=str)

    # Calcular período
    now = datetime.now(timezone.utc)
    if period == "6months":
        months_range = 6
    elif period == "12months":
        months_range = 12
    elif period == "24months":
        months_range = 24
    else:
        months_range = 12

    # Receita mensal
    monthly_revenue = []
    for months_back in range(months_range - 1, -1, -1):
        start_date = now - timedelta(days=30 * months_back)
        end_date = start_date + timedelta(days=30)

        revenue_query = db.session.query(
            func.coalesce(func.sum(Payment.amount), 0)
        ).filter(
            Payment.paid_at >= start_date,
            Payment.paid_at < end_date,
            Payment.payment_status == "completed",
        )

        # Aplicar filtros
        if plan_filter != "all":
            revenue_query = revenue_query.join(BillingPlan).filter(
                BillingPlan.name == plan_filter
            )

        if status_filter != "all":
            revenue_query = revenue_query.join(User).filter(
                User.is_active.is_(True)
                if status_filter == "active"
                else User.is_active.is_(False)
            )

        revenue = revenue_query.scalar() or 0

        monthly_revenue.append(
            {"month": start_date.strftime("%Y-%m"), "revenue": float(revenue)}
        )

    # Receita por plano
    revenue_plan_query = (
        db.session.query(
            BillingPlan.name,
            func.coalesce(func.sum(Payment.amount), 0).label("total_revenue"),
            func.count(Payment.id).label("subscription_count"),
        )
        .join(Payment, BillingPlan.id == Payment.plan_id)
        .filter(Payment.payment_status == "completed")
    )

    if period != "all":
        start_date_filter = now - timedelta(days=30 * months_range)
        revenue_plan_query = revenue_plan_query.filter(
            Payment.paid_at >= start_date_filter
        )

    if status_filter != "all":
        revenue_plan_query = revenue_plan_query.join(
            User, Payment.user_id == User.id
        ).filter(
            User.is_active.is_(True)
            if status_filter == "active"
            else User.is_active.is_(False)
        )

    revenue_by_plan = (
        revenue_plan_query.group_by(BillingPlan.id, BillingPlan.name)
        .order_by(func.coalesce(func.sum(Payment.amount), 0).desc())
        .all()
    )

    # Churn rate
    churn_data = []
    for months_back in range(months_range - 1, -1, -1):
        start_date = now - timedelta(days=30 * months_back)
        end_date = start_date + timedelta(days=30)

        churn_query = UserPlan.query.filter(
            UserPlan.canceled_at >= start_date,
            UserPlan.canceled_at < end_date,
            UserPlan.status == "canceled",
        )

        if plan_filter != "all":
            churn_query = churn_query.join(BillingPlan).filter(
                BillingPlan.name == plan_filter
            )

        churned = churn_query.count()

        active_query = UserPlan.query.filter(
            UserPlan.created_at < start_date,
            db.or_(UserPlan.canceled_at.is_(None), UserPlan.canceled_at >= start_date),
            UserPlan.status.in_(["active", "canceled"]),
        )

        if plan_filter != "all":
            active_query = active_query.join(BillingPlan).filter(
                BillingPlan.name == plan_filter
            )

        active_start = active_query.count()

        churn_rate = (churned / active_start * 100) if active_start > 0 else 0

        churn_data.append(
            {
                "month": start_date.strftime("%Y-%m"),
                "churned": churned,
                "active_start": active_start,
                "churn_rate": round(churn_rate, 2),
            }
        )

    # Criar CSV com múltiplas abas (usando ZIP)
    import zipfile
    from io import BytesIO

    zip_buffer = BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # Receita mensal
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Mês", "Receita (R$)"])
        for item in monthly_revenue:
            writer.writerow([item["month"], f"{item['revenue']:.2f}"])
        zip_file.writestr("receita_mensal.csv", output.getvalue())

        # Receita por plano
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Plano", "Receita Total (R$)", "Assinaturas"])
        for row in revenue_by_plan:
            writer.writerow(
                [row.name, f"{row.total_revenue:.2f}", row.subscription_count]
            )
        zip_file.writestr("receita_por_plano.csv", output.getvalue())

        # Churn rate
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Mês", "Cancelamentos", "Ativos Início", "Taxa Churn (%)"])
        for item in churn_data:
            writer.writerow(
                [
                    item["month"],
                    item["churned"],
                    item["active_start"],
                    f"{item['churn_rate']:.2f}",
                ]
            )
        zip_file.writestr("churn_rate.csv", output.getvalue())

    zip_buffer.seek(0)
    return Response(
        zip_buffer.getvalue(),
        mimetype="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=dashboard_financeiro_{period}.zip"
        },
    )


@bp.route("/api/users/export")
@login_required
def export_users():
    """Exporta lista de usuários em JSON"""
    _require_admin()

    users = User.query.filter(User.user_type != "master").all()

    data = []
    for user in users:
        metrics = _get_user_metrics(user)
        data.append(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "oab_number": user.oab_number,
                "user_type": user.user_type,
                "is_active": user.is_active,
                "billing_status": user.billing_status,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "metrics": metrics,
            }
        )

    return jsonify(data)


def _get_bulk_user_metrics(users):
    """
    Calcula métricas para múltiplos usuários em bulk (otimizado).
    Evita N+1 queries fazendo agregações em uma única consulta.
    """
    if not users:
        return []

    user_ids = [u.id for u in users]
    now = datetime.now(timezone.utc)
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # 1. Contagem de clientes (usa lawyer_id)
    clients_count = dict(
        db.session.query(Client.lawyer_id, func.count(Client.id))
        .filter(Client.lawyer_id.in_(user_ids))
        .group_by(Client.lawyer_id)
        .all()
    )

    # 2. Petições totais e mensais
    petitions_total = dict(
        db.session.query(PetitionUsage.user_id, func.count(PetitionUsage.id))
        .filter(PetitionUsage.user_id.in_(user_ids))
        .group_by(PetitionUsage.user_id)
        .all()
    )

    petitions_month = dict(
        db.session.query(PetitionUsage.user_id, func.count(PetitionUsage.id))
        .filter(
            PetitionUsage.user_id.in_(user_ids),
            PetitionUsage.generated_at >= current_month_start,
        )
        .group_by(PetitionUsage.user_id)
        .all()
    )

    # 3. Valor total de petições
    petitions_value = dict(
        db.session.query(
            PetitionUsage.user_id, func.coalesce(func.sum(PetitionUsage.amount), 0)
        )
        .filter(PetitionUsage.user_id.in_(user_ids))
        .group_by(PetitionUsage.user_id)
        .all()
    )

    petitions_value_month = dict(
        db.session.query(
            PetitionUsage.user_id, func.coalesce(func.sum(PetitionUsage.amount), 0)
        )
        .filter(
            PetitionUsage.user_id.in_(user_ids),
            PetitionUsage.generated_at >= current_month_start,
        )
        .group_by(PetitionUsage.user_id)
        .all()
    )

    # 4. Créditos de IA
    credits_data = {}
    for row in (
        db.session.query(
            UserCredits.user_id, UserCredits.balance, UserCredits.total_used
        )
        .filter(UserCredits.user_id.in_(user_ids))
        .all()
    ):
        credits_data[row[0]] = (row[1], row[2])

    # 5. Gerações de IA totais e mensais
    ai_total = dict(
        db.session.query(AIGeneration.user_id, func.count(AIGeneration.id))
        .filter(AIGeneration.user_id.in_(user_ids))
        .group_by(AIGeneration.user_id)
        .all()
    )

    ai_month = dict(
        db.session.query(AIGeneration.user_id, func.count(AIGeneration.id))
        .filter(
            AIGeneration.user_id.in_(user_ids),
            AIGeneration.created_at >= current_month_start,
        )
        .group_by(AIGeneration.user_id)
        .all()
    )

    # 6. Tokens e custo de IA
    ai_stats = {}
    for row in (
        db.session.query(
            AIGeneration.user_id,
            func.coalesce(func.sum(AIGeneration.tokens_total), 0),
            func.coalesce(func.sum(AIGeneration.cost_usd), 0),
        )
        .filter(AIGeneration.user_id.in_(user_ids))
        .group_by(AIGeneration.user_id)
        .all()
    ):
        ai_stats[row[0]] = (row[1], row[2])

    # 7. Plano atual
    current_plans = {}
    plans_query = (
        db.session.query(UserPlan, BillingPlan)
        .join(BillingPlan)
        .filter(UserPlan.user_id.in_(user_ids), UserPlan.is_current.is_(True))
        .all()
    )
    for user_plan, billing_plan in plans_query:
        current_plans[user_plan.user_id] = billing_plan.name

    # 8. Total pago
    total_paid = dict(
        db.session.query(Payment.user_id, func.coalesce(func.sum(Payment.amount), 0))
        .filter(Payment.user_id.in_(user_ids), Payment.payment_status == "completed")
        .group_by(Payment.user_id)
        .all()
    )

    # 9. Primeiro pagamento (para calcular days_paying)
    first_payments = {}
    payments_query = (
        db.session.query(Payment.user_id, func.min(Payment.paid_at))
        .filter(
            Payment.user_id.in_(user_ids),
            Payment.payment_status == "completed",
            Payment.paid_at.isnot(None),
        )
        .group_by(Payment.user_id)
        .all()
    )
    for user_id, first_paid_at in payments_query:
        if first_paid_at:
            # Garantir que ambas as datas tenham timezone
            paid_at = (
                first_paid_at.replace(tzinfo=timezone.utc)
                if first_paid_at.tzinfo is None
                else first_paid_at
            )
            first_payments[user_id] = (now - paid_at).days

    # Montar resultado
    results = []
    for user in users:
        uid = user.id
        credits = credits_data.get(uid, (0, 0))
        ai_stat = ai_stats.get(uid, (0, Decimal("0.00")))

        # Proteger days_on_platform com timezone awareness
        days_on_platform = 0
        if user.created_at:
            created_at = user.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            days_on_platform = (now - created_at).days

        metrics = {
            "days_on_platform": days_on_platform,
            "days_paying": first_payments.get(uid, 0),
            "plan_name": current_plans.get(uid, "Sem plano"),
            "total_clients": clients_count.get(uid, 0),
            "total_petitions": petitions_total.get(uid, 0),
            "petitions_month": petitions_month.get(uid, 0),
            "petitions_value_total": float(petitions_value.get(uid, Decimal("0.00"))),
            "petitions_value_month": float(
                petitions_value_month.get(uid, Decimal("0.00"))
            ),
            "ai_credits_balance": credits[0] if isinstance(credits, tuple) else 0,
            "ai_credits_total_used": credits[1] if isinstance(credits, tuple) else 0,
            "ai_generations_total": ai_total.get(uid, 0),
            "ai_generations_month": ai_month.get(uid, 0),
            "ai_tokens_month": ai_stat[0] if len(ai_stat) > 0 else 0,
            "ai_cost_month": float(ai_stat[1]) if len(ai_stat) > 1 else 0.0,
            "total_paid": float(total_paid.get(uid, Decimal("0.00"))),
        }

        results.append({"user": user, "metrics": metrics})

    return results


def _get_user_metrics(user, detailed=False):
    """Calcula métricas de um usuário"""
    now = datetime.now(timezone.utc)
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Dias na plataforma
    if user.created_at:
        # Garantir que ambas as datas tenham timezone
        user_created_at = (
            user.created_at.replace(tzinfo=timezone.utc)
            if user.created_at.tzinfo is None
            else user.created_at
        )
        days_on_platform = (now - user_created_at).days
    else:
        days_on_platform = 0

    # Clientes (Client usa lawyer_id, não user_id)
    clients_count = Client.query.filter_by(lawyer_id=user.id).count()
    clients_month = Client.query.filter(
        Client.lawyer_id == user.id,
        Client.created_at >= current_month_start,
    ).count()

    # Petições
    petitions_total = PetitionUsage.query.filter_by(user_id=user.id).count()
    petitions_month = PetitionUsage.query.filter(
        PetitionUsage.user_id == user.id,
        PetitionUsage.generated_at >= current_month_start,
    ).count()

    # Valor total de petições
    petitions_value = db.session.query(
        func.coalesce(func.sum(PetitionUsage.amount), 0)
    ).filter(PetitionUsage.user_id == user.id).scalar() or Decimal("0.00")

    petitions_value_month = db.session.query(
        func.coalesce(func.sum(PetitionUsage.amount), 0)
    ).filter(
        PetitionUsage.user_id == user.id,
        PetitionUsage.generated_at >= current_month_start,
    ).scalar() or Decimal("0.00")

    # Créditos de IA
    user_credits = UserCredits.query.filter_by(user_id=user.id).first()
    ai_credits_balance = user_credits.balance if user_credits else 0
    ai_credits_used = user_credits.total_used if user_credits else 0

    # Uso de IA
    ai_generations_total = AIGeneration.query.filter_by(user_id=user.id).count()
    ai_generations_month = AIGeneration.query.filter(
        AIGeneration.user_id == user.id, AIGeneration.created_at >= current_month_start
    ).count()

    # Tokens e custo de IA
    ai_stats = (
        db.session.query(
            func.coalesce(func.sum(AIGeneration.tokens_total), 0).label("tokens"),
            func.coalesce(func.sum(AIGeneration.cost_usd), 0).label("cost"),
        )
        .filter(AIGeneration.user_id == user.id)
        .first()
    )

    ai_tokens_total = ai_stats.tokens if ai_stats and ai_stats.tokens is not None else 0
    ai_cost_total = (
        ai_stats.cost if ai_stats and ai_stats.cost is not None else Decimal("0.00")
    )

    # Plano atual
    current_plan = UserPlan.query.filter_by(user_id=user.id, is_current=True).first()
    plan_name = "Sem plano"
    if current_plan:
        try:
            plan_name = current_plan.plan.name if current_plan.plan else "Sem plano"
        except AttributeError:
            plan_name = "Plano não encontrado"

    # Dias como pagante
    first_payment = (
        Payment.query.filter(
            Payment.user_id == user.id, Payment.payment_status == "completed"
        )
        .order_by(Payment.paid_at.asc())
        .first()
    )

    days_paying = 0
    if first_payment and first_payment.paid_at:
        # Garantir que ambas as datas tenham timezone
        paid_at = (
            first_payment.paid_at.replace(tzinfo=timezone.utc)
            if first_payment.paid_at.tzinfo is None
            else first_payment.paid_at
        )
        days_paying = (now - paid_at).days

    # Total pago
    total_paid = db.session.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
        Payment.user_id == user.id, Payment.payment_status == "completed"
    ).scalar() or Decimal("0.00")

    metrics = {
        "days_on_platform": days_on_platform,
        "days_paying": days_paying,
        "plan_name": plan_name,
        "clients_count": clients_count,
        "clients_month": clients_month,
        "petitions_total": petitions_total,
        "petitions_month": petitions_month,
        "petitions_value": float(petitions_value),
        "petitions_value_month": float(petitions_value_month),
        "ai_credits_balance": ai_credits_balance,
        "ai_credits_used": ai_credits_used,
        "ai_generations_total": ai_generations_total,
        "ai_generations_month": ai_generations_month,
        "ai_tokens_total": ai_tokens_total,
        "ai_cost_total": float(ai_cost_total),
        "total_paid": float(total_paid),
    }

    return metrics


# =============================================================================
# GESTÃO DE TIPOS DE PETIÇÃO E SEÇÕES
# =============================================================================


@bp.route("/petitions")
@login_required
def petitions_admin():
    """Página principal de administração de petições"""
    _require_admin()

    # Estatísticas gerais
    total_petition_types = PetitionType.query.count()
    active_petition_types = PetitionType.query.filter_by(is_active=True).count()
    dynamic_petition_types = PetitionType.query.filter_by(use_dynamic_form=True).count()
    total_sections = PetitionSection.query.filter_by(is_active=True).count()

    # Tipos de petição recentes (últimos 10)
    recent_petition_types = (
        PetitionType.query.order_by(PetitionType.created_at.desc()).limit(10).all()
    )

    return render_template(
        "admin/petitions_dashboard.html",
        title="Administração de Petições",
        total_petition_types=total_petition_types,
        active_petition_types=active_petition_types,
        dynamic_petition_types=dynamic_petition_types,
        total_sections=total_sections,
        recent_petition_types=recent_petition_types,
    )


# =============================================================================
# ROTAS PARA SEÇÕES DE PETIÇÃO
# =============================================================================


@bp.route("/petitions/sections")
@login_required
@master_required
@limiter.limit(ADMIN_API_LIMIT)
def petition_sections_list():
    """Lista todas as seções de petição"""
    from app.utils.error_messages import format_error_for_user

    current_app.logger.info("🔍 [SECTIONS] Iniciando petition_sections_list")
    current_app.logger.info("✅ [SECTIONS] Usuário admin autenticado")

    try:
        # type_sections é dynamic (lazy="dynamic"), não pode ser eagerly loaded
        sections = PetitionSection.query.order_by(PetitionSection.order).all()
        current_app.logger.info(
            f"📊 [SECTIONS] Encontradas {len(sections)} seções no banco"
        )

        for section in sections[:3]:  # Log das primeiras 3 seções
            current_app.logger.info(
                f"📋 [SECTIONS] Seção: {section.name} (ID: {section.id}, Ativo: {section.is_active})"
            )

        current_app.logger.info(
            "🎨 [SECTIONS] Renderizando template petition_sections_list.html"
        )
        return render_template(
            "admin/petition_sections_list.html",
            title="Seções de Petição",
            sections=sections,
        )
    except Exception as e:
        current_app.logger.error(
            f"❌ [SECTIONS] Erro em petition_sections_list: {str(e)}"
        )
        current_app.logger.error(f"❌ [SECTIONS] Traceback: {traceback.format_exc()}")
        error_message = format_error_for_user(e, "general")
        flash(error_message, "danger")
        return redirect(url_for("admin.petitions_admin"))


@bp.route("/petitions/sections/new", methods=["GET", "POST"])
@login_required
@master_required
@limiter.limit(ADMIN_API_LIMIT)
@validate_with_schema(PetitionSectionSchema, location="form")
def petition_section_new():
    """Cria uma nova seção de petição"""
    current_app.logger.info("🔍 [SECTIONS] Iniciando petition_section_new")
    _require_admin()
    current_app.logger.info("✅ [SECTIONS] Usuário admin autenticado")

    if request.method == "POST":
        current_app.logger.info("📝 [SECTIONS] Processando POST para nova seção")

        # Dados já foram validados!
        data = request.validated_data

        name = data.get("name")
        description = data.get("description")
        icon = data.get("icon", "fa-file-alt")
        color = data.get("color", "primary")
        order = int(data.get("order", 0))
        is_active = data.get("is_active", False)
        fields_schema_raw = data.get("fields_schema", "[]")

        # Gerar slug único baseado no nome
        slug = generate_unique_slug(name, PetitionSection)

        # Parse do JSON string para objeto Python
        try:
            fields_schema = json.loads(fields_schema_raw) if fields_schema_raw else []
            current_app.logger.info(
                f"📋 [SECTIONS] Fields Schema parsed successfully: {len(fields_schema)} campos"
            )
        except json.JSONDecodeError as e:
            current_app.logger.warning(
                f"⚠️ [SECTIONS] Erro ao fazer parse do fields_schema JSON: {e}. Usando array vazio."
            )
            fields_schema = []

        current_app.logger.info(
            f"📋 [SECTIONS] Dados recebidos - Nome: {name}, Slug gerado: {slug}, Ícone: {icon}"
        )

        try:
            # Criar seção
            section = PetitionSection(
                name=name,
                slug=slug,
                description=description,
                icon=icon,
                color=color,
                order=order,
                is_active=is_active,
                fields_schema=fields_schema,
            )

            db.session.add(section)
            db.session.commit()
            current_app.logger.info(
                f"✅ [SECTIONS] Seção criada com sucesso - ID: {section.id}"
            )

            flash("Seção criada com sucesso!", "success")
            return redirect(url_for("admin.petition_sections_list"))
        except Exception as e:
            current_app.logger.error(f"❌ [SECTIONS] Erro ao criar seção: {str(e)}")
            current_app.logger.error(
                f"❌ [SECTIONS] Traceback: {traceback.format_exc()}"
            )
            db.session.rollback()
            flash("Erro ao criar seção.", "danger")
            return redirect(url_for("admin.petition_section_new"))

    current_app.logger.info(
        "🎨 [SECTIONS] Renderizando template petition_section_form.html para nova seção"
    )
    return render_template(
        "admin/petition_section_form.html",
        title="Nova Seção",
        section=None,
    )


@bp.route("/petitions/sections/<int:section_id>/edit", methods=["GET", "POST"])
@login_required
@master_required
@limiter.limit(ADMIN_API_LIMIT)
@validate_with_schema(PetitionSectionSchema, location="form")
def petition_section_edit(section_id):
    """Edita uma seção de petição"""
    current_app.logger.info(
        f"🔍 [SECTIONS] Iniciando petition_section_edit - ID: {section_id}"
    )
    _require_admin()
    current_app.logger.info("✅ [SECTIONS] Usuário admin autenticado")

    try:
        section = PetitionSection.query.get_or_404(section_id)
        current_app.logger.info(
            f"📋 [SECTIONS] Seção encontrada: {section.name} (ID: {section.id})"
        )
    except Exception as e:
        current_app.logger.error(
            f"❌ [SECTIONS] Seção não encontrada - ID: {section_id}, Erro: {str(e)}"
        )
        raise

    if request.method == "POST":
        current_app.logger.info(
            f"📝 [SECTIONS] Processando POST para editar seção {section_id}"
        )

        try:
            # Dados já foram validados!
            data = request.validated_data

            name = data.get("name")
            description = data.get("description")
            icon = data.get("icon", "fa-file-alt")
            color = data.get("color", "primary")
            order = int(data.get("order", 0))
            is_active = data.get("is_active", False)

            # Gerar slug único baseado no nome, considerando o slug atual
            new_slug = generate_unique_slug(name, PetitionSection, section.slug)

            section.name = name
            section.slug = new_slug
            section.description = description
            section.icon = icon
            section.color = color
            section.order = order
            section.is_active = is_active

            # Processar fields_schema
            fields_schema_raw = data.get("fields_schema", "[]")
            try:
                section.fields_schema = (
                    json.loads(fields_schema_raw) if fields_schema_raw else []
                )
                current_app.logger.info(
                    f"📋 [SECTIONS] Fields Schema atualizado: {len(section.fields_schema)} campos"
                )
            except json.JSONDecodeError as e:
                current_app.logger.warning(
                    f"⚠️ [SECTIONS] Erro ao fazer parse do fields_schema JSON: {e}. Mantendo valor anterior."
                )
                # Não alterar o fields_schema se houver erro de parse

            db.session.commit()
            current_app.logger.info(
                f"✅ [SECTIONS] Seção atualizada com sucesso - ID: {section_id}"
            )

            flash("Seção atualizada com sucesso!", "success")
            return redirect(url_for("admin.petition_sections_list"))
        except Exception as e:
            current_app.logger.error(
                f"❌ [SECTIONS] Erro ao atualizar seção {section_id}: {str(e)}"
            )
            current_app.logger.error(
                f"❌ [SECTIONS] Traceback: {traceback.format_exc()}"
            )
            db.session.rollback()
            flash("Erro ao atualizar seção.", "danger")
            return redirect(
                url_for("admin.petition_section_edit", section_id=section_id)
            )

    current_app.logger.info(
        f"🎨 [SECTIONS] Renderizando template para editar seção {section_id}"
    )
    return render_template(
        "admin/petition_section_form.html",
        title="Editar Seção",
        section=section,
    )


@bp.route("/petitions/sections/<int:section_id>/delete", methods=["POST"])
@login_required
@master_required
@limiter.limit(ADMIN_API_LIMIT)
def petition_section_delete(section_id):
    """Exclui uma seção de petição"""
    current_app.logger.info(
        f"🔍 [SECTIONS] Iniciando petition_section_delete - ID: {section_id}"
    )
    _require_admin()
    current_app.logger.info("✅ [SECTIONS] Usuário admin autenticado")

    try:
        section = PetitionSection.query.get_or_404(section_id)
        current_app.logger.info(
            f"📋 [SECTIONS] Seção encontrada para exclusão: {section.name} (ID: {section.id})"
        )
    except Exception as e:
        current_app.logger.error(
            f"❌ [SECTIONS] Seção não encontrada para exclusão - ID: {section_id}, Erro: {str(e)}"
        )
        raise

    try:
        # Verificar se a seção está sendo usada em modelos
        model_usage_count = len(section.model_sections)
        current_app.logger.info(
            f"🔍 [SECTIONS] Verificando uso da seção - Usada em {model_usage_count} modelos de petição"
        )

        if model_usage_count > 0:
            current_app.logger.warning(
                f"⚠️ [SECTIONS] Tentativa de excluir seção em uso - ID: {section_id}, Usos: {model_usage_count}"
            )
            flash(
                "Não é possível excluir uma seção que está sendo usada em tipos de petição.",
                "danger",
            )
            return redirect(url_for("admin.petition_sections_list"))

        db.session.delete(section)
        db.session.commit()
        current_app.logger.info(
            f"✅ [SECTIONS] Seção excluída com sucesso - ID: {section_id}"
        )

        flash("Seção excluída com sucesso!", "success")
        return redirect(url_for("admin.petition_sections_list"))
    except Exception as e:
        current_app.logger.error(
            f"❌ [SECTIONS] Erro ao excluir seção {section_id}: {str(e)}"
        )
        current_app.logger.error(f"❌ [SECTIONS] Traceback: {traceback.format_exc()}")
        db.session.rollback()
        flash("Erro ao excluir seção.", "danger")
        return redirect(url_for("admin.petition_sections_list"))


# =============================================================================
# EDITOR VISUAL DE SEÇÕES (BETA) - Formulário experimental com drag-and-drop
# =============================================================================


@bp.route("/petitions/sections-editor")
@login_required
@master_required
def petition_sections_editor():
    """
    Editor visual de seções (BETA).
    Interface drag-and-drop para criar/editar campos de seções.
    """
    _require_admin()

    sections = PetitionSection.query.order_by(PetitionSection.order).all()

    return render_template(
        "admin/petition_sections_editor.html",
        title="Editor Visual de Seções (Beta)",
        sections=sections,
    )


@bp.route("/petitions/sections-editor/<int:section_id>")
@login_required
@master_required
def petition_section_editor_edit(section_id):
    """
    Editor visual para uma seção específica (BETA).
    """
    _require_admin()

    section = PetitionSection.query.get_or_404(section_id)

    return render_template(
        "admin/petition_section_editor_form.html",
        title=f"Editor Visual: {section.name}",
        section=section,
    )


@bp.route("/petitions/sections-editor/new")
@login_required
@master_required
def petition_section_editor_new():
    """
    Criar nova seção com editor visual (BETA).
    """
    _require_admin()

    return render_template(
        "admin/petition_section_editor_form.html",
        title="Nova Seção (Editor Visual)",
        section=None,
    )


@bp.route("/petitions/sections-editor/save", methods=["POST"])
@limiter.limit(ADMIN_API_LIMIT)  # Rate limit PRIMEIRO
@login_required
@master_required
def petition_section_editor_save():
    """
    Salva seção criada/editada pelo editor visual (BETA).
    Recebe JSON com dados da seção e campos.
    """
    import re

    _require_admin()

    # Listas de valores permitidos (whitelist)
    ALLOWED_ICONS = [
        "fa-file-alt",
        "fa-user",
        "fa-users",
        "fa-gavel",
        "fa-balance-scale",
        "fa-money-bill",
        "fa-calendar",
        "fa-map-marker",
        "fa-clipboard",
        "fa-pen",
        "fa-home",
        "fa-briefcase",
        "fa-folder",
        "fa-list",
        "fa-check",
    ]
    ALLOWED_COLORS = [
        "primary",
        "secondary",
        "success",
        "danger",
        "warning",
        "info",
        "dark",
        "light",
    ]
    ALLOWED_FIELD_TYPES = [
        "text",
        "textarea",
        "editor",
        "select",
        "radio",
        "checkbox",
        "date",
        "number",
        "currency",
    ]

    try:
        data = request.get_json()

        # Verificar se data existe (OBRIGATÓRIO conforme instruções)
        if not data:
            return jsonify({"success": False, "error": "Dados inválidos"}), 400

        # Sanitizar inputs
        def sanitize_text(text, max_length=255):
            """Remove HTML e limita tamanho"""
            if not text:
                return ""
            text = re.sub(r"<[^>]+>", "", str(text).strip())
            return text[:max_length]

        def sanitize_name(name, max_length=100):
            """Sanitiza nome de campo (apenas alfanumérico e underscore)"""
            if not name:
                return ""
            return re.sub(r"[^a-z0-9_]", "", str(name).lower())[:max_length]

        section_id = data.get("id")
        if section_id is not None:
            section_id = int(section_id) if str(section_id).isdigit() else None

        name = sanitize_text(data.get("name", ""), max_length=200)
        description = sanitize_text(data.get("description", ""), max_length=500)

        # Validar icon contra whitelist
        icon = data.get("icon", "fa-file-alt")
        if icon not in ALLOWED_ICONS:
            icon = "fa-file-alt"

        # Validar color contra whitelist
        color = data.get("color", "primary")
        if color not in ALLOWED_COLORS:
            color = "primary"

        # Validar order como inteiro
        try:
            order = int(data.get("order", 0))
            order = max(0, min(order, 9999))  # Limitar range
        except (ValueError, TypeError):
            order = 0

        is_active = bool(data.get("is_active", True))
        fields = data.get("fields", [])

        if not name:
            return jsonify({"success": False, "error": "Nome é obrigatório"}), 400

        if len(name) < 3:
            return jsonify(
                {"success": False, "error": "Nome deve ter pelo menos 3 caracteres"}
            ), 400

        # Limitar quantidade de campos
        MAX_FIELDS = 50
        if len(fields) > MAX_FIELDS:
            return jsonify(
                {"success": False, "error": f"Máximo de {MAX_FIELDS} campos permitido"}
            ), 400

        # Validar e sanitizar campos
        validated_fields = []
        for idx, field in enumerate(fields):
            if not isinstance(field, dict):
                continue

            field_name = sanitize_name(field.get("name", ""))
            if not field_name:
                field_name = f"campo_{idx + 1}"

            field_type = field.get("type", "text")
            if field_type not in ALLOWED_FIELD_TYPES:
                field_type = "text"

            # Sanitizar options para select/radio
            options = field.get("options", [])
            if isinstance(options, list):
                options = [
                    sanitize_text(str(opt), max_length=100) for opt in options[:20]
                ]  # Max 20 opções
            else:
                options = []

            validated_fields.append(
                {
                    "name": str(field_name),
                    "label": sanitize_text(
                        field.get("label", field_name.replace("_", " ").title()),
                        max_length=100,
                    ),
                    "type": str(field_type),
                    "required": bool(field.get("required", False)),
                    "placeholder": sanitize_text(
                        field.get("placeholder", ""), max_length=200
                    ),
                    "help_text": sanitize_text(
                        field.get("help_text", ""), max_length=300
                    ),
                    "options": list(options),
                    "default_value": sanitize_text(
                        field.get("default_value", ""), max_length=500
                    ),
                }
            )

        if section_id:
            # Editar seção existente
            section = PetitionSection.query.get_or_404(section_id)
            section.name = name
            section.description = description
            section.icon = icon
            section.color = color
            section.order = order
            section.is_active = is_active
            section.fields_schema = validated_fields

            db.session.commit()

            current_app.logger.info(
                f"[EDITOR] Seção atualizada via editor visual - ID: {section.id}"
            )

            return jsonify(
                {
                    "success": True,
                    "message": "Seção atualizada com sucesso!",
                    "section_id": int(section.id),
                }
            )
        else:
            # Criar nova seção
            slug = generate_unique_slug(name, PetitionSection)

            section = PetitionSection(
                name=name,
                slug=slug,
                description=description,
                icon=icon,
                color=color,
                order=order,
                is_active=is_active,
                fields_schema=validated_fields,
            )

            db.session.add(section)
            db.session.commit()

            current_app.logger.info(
                f"[EDITOR] Seção criada via editor visual - ID: {section.id}"
            )

            return jsonify(
                {
                    "success": True,
                    "message": "Seção criada com sucesso!",
                    "section_id": int(section.id),
                }
            )

    except Exception as e:
        current_app.logger.error(f"[EDITOR] Erro ao salvar seção: {str(e)}")
        db.session.rollback()
        return jsonify({"success": False, "error": "Erro ao salvar seção"}), 500


@bp.route("/petitions/sections-editor/<int:section_id>/preview", methods=["POST"])
@limiter.limit(ADMIN_API_LIMIT)  # Rate limit PRIMEIRO
@login_required
@master_required
def petition_section_editor_preview(section_id):
    """
    Gera preview HTML dos campos de uma seção (BETA).
    """
    _require_admin()

    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": "Dados inválidos"}), 400

        fields = data.get("fields", [])

        # Renderizar preview dos campos
        preview_html = render_template(
            "admin/partials/_section_fields_preview.html",
            fields=fields,
        )

        return jsonify({"success": True, "html": str(preview_html)})

    except Exception as e:
        return jsonify({"success": False, "error": "Erro ao gerar preview"}), 500


@bp.route("/petitions/types/<int:type_id>/sections", methods=["GET", "POST"])
@login_required
def petition_type_sections(type_id):
    """Gerencia as seções de um tipo de petição"""
    _require_admin()

    petition_type = PetitionType.query.get_or_404(type_id)

    if request.method == "POST":
        # Salvar configurações das seções
        section_ids = request.form.getlist("section_id[]")
        section_orders = request.form.getlist("section_order[]")
        section_required = request.form.getlist("section_required[]")
        section_expanded = request.form.getlist("section_expanded[]")

        # DEPRECATED: PetitionTypeSection removed - now only using PetitionModelSection
        # This admin route is no longer functional
        flash(
            "Esta funcionalidade foi descontinuada. Use a gestão de modelos de petição.",
            "info",
        )
        return redirect(url_for("admin.petitions_admin"))

    # GET: mostrar página - DEPRECATED
    # PetitionTypeSection removed - functionality moved to PetitionModelSection management
    flash(
        "A gestão de seções por tipo de petição foi descontinuada. Use a gestão de modelos.",
        "info",
    )
    return redirect(url_for("admin.petitions_admin"))


@bp.route("/petitions/types/<int:type_id>/sections/add", methods=["POST"])
@login_required
def petition_type_section_add(type_id):
    """DEPRECATED: PetitionTypeSection no longer used"""
    _require_admin()
    flash("Esta funcionalidade foi descontinuada.", "info")
    return redirect(url_for("admin.petitions_admin"))


@bp.route(
    "/petitions/types/<int:type_id>/sections/<int:section_id>/remove", methods=["POST"]
)
@login_required
def petition_type_section_remove(type_id, section_id):
    """DEPRECATED: PetitionTypeSection no longer used"""
    _require_admin()
    flash("Esta funcionalidade foi descontinuada.", "info")
    return redirect(url_for("admin.petitions_admin"))


@bp.route("/petitions/types")
@login_required
@master_required
@limiter.limit(ADMIN_API_LIMIT)
def petition_types_list():
    """Lista todos os tipos de petição"""
    from app.utils.error_messages import format_error_for_user

    try:
        # Usar type_sections (dynamic relationship, não pode ser eagerly loaded)
        petition_types = PetitionType.query.order_by(PetitionType.name).all()

        return render_template(
            "admin/petition_types_list.html",
            title="Tipos de Petição",
            petition_types=petition_types,
        )
    except Exception as e:
        error_message = format_error_for_user(e, "general")
        current_app.logger.error(
            f"Erro ao carregar lista de tipos de petição: {str(e)}"
        )
        flash(error_message, "danger")
        return redirect(url_for("admin.petitions_admin"))


@bp.route("/petitions/types/new", methods=["GET", "POST"])
@login_required
@master_required
@limiter.limit(ADMIN_API_LIMIT)
@validate_with_schema(PetitionTypeSchema, location="form")
def petition_type_new():
    """Criar novo tipo de petição"""

    if request.method == "POST":
        data = request.validated_data  # Dados já foram validados!

        # Gerar slug único baseado no nome
        slug = generate_unique_slug(data["name"], PetitionType)

        petition_type = PetitionType(
            name=data["name"],
            slug=slug,
            description=data.get("description"),
            category=data.get("category", "civel"),
            icon=data.get("icon", "fa-file-alt"),
            color=data.get("color", "primary"),
            is_billable=data.get("is_billable", False),
            base_price=Decimal(data.get("base_price", "0.00")),
            use_dynamic_form=data.get("use_dynamic_form", False),
        )

        db.session.add(petition_type)
        db.session.commit()

        flash(f"Tipo de petição '{data['name']}' criado com sucesso!", "success")
        return redirect(url_for("admin.petition_types_list"))

    return render_template(
        "admin/petition_type_form.html", title="Novo Tipo de Petição"
    )


@bp.route("/petitions/types/<int:type_id>/edit", methods=["GET", "POST"])
@login_required
@master_required
@limiter.limit(ADMIN_API_LIMIT)
@validate_with_schema(PetitionTypeSchema, location="form")
def petition_type_edit(type_id):
    """Editar tipo de petição"""
    _require_admin()

    petition_type = PetitionType.query.get_or_404(type_id)

    if request.method == "POST":
        # Dados já foram validados!
        data = request.validated_data

        name = data.get("name")
        description = data.get("description")
        category = data.get("category", "civel")
        icon = data.get("icon", "fa-file-alt")
        color = data.get("color", "primary")
        is_billable = data.get("is_billable", False)
        base_price = Decimal(data.get("base_price", "0.00"))
        use_dynamic_form = data.get("use_dynamic_form", False)
        is_active = data.get("is_active", False)

        # Gerar slug único baseado no nome, considerando o slug atual
        new_slug = generate_unique_slug(name, PetitionType, petition_type.slug)

        petition_type.name = name
        petition_type.slug = new_slug
        petition_type.description = description
        petition_type.category = category
        petition_type.icon = icon
        petition_type.color = color
        petition_type.is_billable = is_billable
        petition_type.base_price = base_price
        petition_type.use_dynamic_form = use_dynamic_form
        petition_type.is_active = is_active

        # Validar slug único (exceto para o próprio)
        existing = PetitionType.query.filter_by(slug=petition_type.slug).first()
        if existing and existing.id != petition_type.id:
            flash("Slug já existe. Escolha outro.", "danger")
            return redirect(request.url)

        db.session.commit()
        flash(f"Tipo de petição '{petition_type.name}' atualizado!", "success")
        return redirect(url_for("admin.petition_types_list"))

    return render_template(
        "admin/petition_type_form.html",
        title=f"Editar: {petition_type.name}",
        petition_type=petition_type,
    )


@bp.route("/petitions/types/<int:type_id>/delete", methods=["POST"])
@login_required
@master_required
@limiter.limit(ADMIN_API_LIMIT)
def petition_type_delete(type_id):
    """Excluir tipo de petição"""
    _require_admin()

    petition_type = PetitionType.query.get_or_404(type_id)

    # Verificar se há petições salvas usando este tipo
    saved_count = SavedPetition.query.filter_by(petition_type_id=type_id).count()
    if saved_count > 0:
        flash(
            f"Não é possível excluir. Existem {saved_count} petições salvas usando este tipo.",
            "danger",
        )
        return redirect(url_for("admin.petition_types_list"))

    db.session.delete(petition_type)
    db.session.commit()

    flash(f"Tipo de petição '{petition_type.name}' excluído!", "success")
    return redirect(url_for("admin.petition_types_list"))


def _calculate_trends():
    """Calcula tendências básicas para métricas principais (últimos 3 meses)"""
    now = datetime.now(timezone.utc)
    trends = {}

    # === Tendência de Receita ===
    revenue_trend = []
    for months_back in range(2, -1, -1):
        start_date = now - timedelta(days=30 * months_back)
        end_date = start_date + timedelta(days=30)

        revenue = (
            db.session.query(func.coalesce(func.sum(Payment.amount), 0))
            .filter(
                Payment.paid_at >= start_date,
                Payment.paid_at < end_date,
                Payment.payment_status == "completed",
            )
            .scalar()
            or 0
        )

        revenue_trend.append(float(revenue))

    if len(revenue_trend) >= 2:
        revenue_change = (
            ((revenue_trend[-1] - revenue_trend[-2]) / revenue_trend[-2] * 100)
            if revenue_trend[-2] > 0
            else 0
        )
        trends["revenue"] = {
            "current": revenue_trend[-1],
            "previous": revenue_trend[-2],
            "change_percent": round(revenue_change, 1),
            "direction": "up"
            if revenue_change > 0
            else "down"
            if revenue_change < 0
            else "stable",
            "trend": (
                "Crescendo"
                if revenue_change > 5
                else "Caíndo"
                if revenue_change < -5
                else "Estável"
            ),
        }

    # === Tendência de Novos Usuários ===
    users_trend = []
    for months_back in range(2, -1, -1):
        start_date = now - timedelta(days=30 * months_back)
        end_date = start_date + timedelta(days=30)

        user_count = User.query.filter(
            User.created_at >= start_date,
            User.created_at < end_date,
            User.user_type != "master",
        ).count()

        users_trend.append(user_count)

    if len(users_trend) >= 2:
        users_change = (
            ((users_trend[-1] - users_trend[-2]) / users_trend[-2] * 100)
            if users_trend[-2] > 0
            else 0
        )
        trends["users"] = {
            "current": users_trend[-1],
            "previous": users_trend[-2],
            "change_percent": round(users_change, 1),
            "direction": "up"
            if users_change > 0
            else "down"
            if users_change < 0
            else "stable",
            "trend": (
                "Crescendo"
                if users_change > 10
                else "Caíndo"
                if users_change < -10
                else "Estável"
            ),
        }

    # === Tendência de Petições ===
    petitions_trend = []
    for months_back in range(2, -1, -1):
        start_date = now - timedelta(days=30 * months_back)
        end_date = start_date + timedelta(days=30)

        petition_count = PetitionUsage.query.filter(
            PetitionUsage.generated_at >= start_date,
            PetitionUsage.generated_at < end_date,
        ).count()

        petitions_trend.append(petition_count)

    if len(petitions_trend) >= 2:
        petitions_change = (
            ((petitions_trend[-1] - petitions_trend[-2]) / petitions_trend[-2] * 100)
            if petitions_trend[-2] > 0
            else 0
        )
        trends["petitions"] = {
            "current": petitions_trend[-1],
            "previous": petitions_trend[-2],
            "change_percent": round(petitions_change, 1),
            "direction": (
                "up"
                if petitions_change > 0
                else "down"
                if petitions_change < 0
                else "stable"
            ),
            "trend": (
                "Crescendo"
                if petitions_change > 5
                else "Caíndo"
                if petitions_change < -5
                else "Estável"
            ),
        }

    return trends


# =============================================================================
# ROADMAP MANAGEMENT ROUTES
# =============================================================================


@bp.route("/roadmap")
@login_required
def roadmap():
    """Página principal de gerenciamento do roadmap"""
    _require_admin()

    # Estatísticas rápidas
    total_items = RoadmapItem.query.count()
    completed_items = RoadmapItem.query.filter_by(status="completed").count()
    in_progress_items = RoadmapItem.query.filter_by(status="in_progress").count()
    planned_items = RoadmapItem.query.filter_by(status="planned").count()

    # Itens visíveis aos usuários
    public_items = RoadmapItem.query.filter_by(visible_to_users=True).count()

    # Itens por categoria
    categories = RoadmapCategory.query.filter_by(is_active=True).all()

    # Itens concluídos (últimos 10)
    completed_items_list = (
        RoadmapItem.query.filter_by(status="completed")
        .order_by(RoadmapItem.actual_completion_date.desc().nullslast())
        .limit(10)
        .all()
    )

    # Itens pendentes (últimos 10)
    pending_items_list = (
        RoadmapItem.query.filter(RoadmapItem.status.in_(["planned", "in_progress"]))
        .order_by(
            RoadmapItem.priority.desc(),
            RoadmapItem.planned_start_date.asc().nullslast(),
        )
        .limit(10)
        .all()
    )

    return render_template(
        "admin/roadmap.html",
        title="Gerenciamento do Roadmap",
        total_items=total_items,
        completed_items=completed_items,
        in_progress_items=in_progress_items,
        planned_items=planned_items,
        public_items=public_items,
        categories=categories,
        completed_items_list=completed_items_list,
        pending_items_list=pending_items_list,
    )


@bp.route("/roadmap/matriz")
@login_required
def roadmap_matrix():
    """Visualização de matriz de impacto vs esforço do roadmap"""
    _require_admin()

    # Buscar todos os itens do roadmap
    roadmap_items = RoadmapItem.query.all()

    return render_template(
        "admin/roadmap_matrix.html",
        title="Matriz de Impacto vs Esforço",
        roadmap_items=roadmap_items,
    )


# Expanded palette of distinct colors used for roadmap categories (keeps Bootstrap core names + additional distinct hues)
ROADMAP_COLOR_PALETTE = [
    "primary",
    "indigo",
    "purple",
    "info",
    "cyan",
    "teal",
    "success",
    "lime",
    "warning",
    "orange",
    "danger",
    "pink",
    "secondary",
    "olive",
    "dark",
    "light",
]


@bp.route("/roadmap/categories")
@login_required
def roadmap_categories():
    """Gerenciamento de categorias do roadmap"""
    _require_admin()

    categories = RoadmapCategory.query.order_by(RoadmapCategory.order).all()

    return render_template(
        "admin/roadmap_categories.html",
        title="Categorias do Roadmap",
        categories=categories,
    )


@bp.route("/roadmap/categories/new", methods=["GET", "POST"])
@login_required
@master_required
@limiter.limit(ADMIN_API_LIMIT)
@validate_with_schema(RoadmapCategorySchema, location="form")
def new_roadmap_category():
    """Criar nova categoria do roadmap"""
    _require_admin()

    if request.method == "POST":
        try:
            data = request.validated_data

            name = data.get("name")
            slug = data.get("slug")
            description = data.get("description")
            icon = data.get("icon", "fa-lightbulb")
            color = data.get("color", "auto")  # default to auto-assign
            order = int(data.get("order", 0))

            # Verificar se slug já existe
            if RoadmapCategory.query.filter_by(slug=slug).first():
                flash("Slug já existe. Escolha outro.", "error")
                return redirect(request.url)

            # If color is 'auto' or blank, pick a palette color not currently used (to avoid duplicates)
            if not color or color == "auto":
                used = [c.color for c in RoadmapCategory.query.all()]
                selected = None
                for c in ROADMAP_COLOR_PALETTE:
                    if c not in used:
                        selected = c
                        break
                if not selected:
                    # All colors used, pick one by cycling
                    selected = ROADMAP_COLOR_PALETTE[
                        len(used) % len(ROADMAP_COLOR_PALETTE)
                    ]
                color = selected

            # If user selected a custom color not in palette, accept it but ensure it's a string
            if not isinstance(color, str):
                color = str(color)

            category = RoadmapCategory(
                name=name,
                slug=slug,
                description=description,
                icon=icon,
                color=color,
                order=order,
            )

            db.session.add(category)
            db.session.commit()

            flash("Categoria criada com sucesso!", "success")
            return redirect(url_for("admin.roadmap_categories"))
        except Exception as e:
            current_app.logger.error(f"Error creating roadmap category: {str(e)}")
            error_msg = format_error_for_user(e, "Erro ao criar categoria do roadmap")
            flash(error_msg, "error")
            return redirect(request.url)

    return render_template(
        "admin/roadmap_category_form.html",
        title="Nova Categoria",
        colors=ROADMAP_COLOR_PALETTE,
    )


@bp.route("/roadmap/categories/<int:category_id>/edit", methods=["GET", "POST"])
@login_required
@master_required
@limiter.limit(ADMIN_API_LIMIT)
@validate_with_schema(RoadmapCategorySchema, location="form")
def edit_roadmap_category(category_id):
    """Editar categoria do roadmap"""
    _require_admin()

    category = RoadmapCategory.query.get_or_404(category_id)

    if request.method == "POST":
        try:
            data = request.validated_data

            category.name = data.get("name")
            category.slug = data.get("slug")
            category.description = data.get("description")
            category.icon = data.get("icon", "fa-lightbulb")
            submitted_color = data.get("color", "auto")

            # If 'auto' selected, try to pick a distinct palette color (excluding this category)
            if not submitted_color or submitted_color == "auto":
                used = [
                    c.color
                    for c in RoadmapCategory.query.filter(
                        RoadmapCategory.id != category_id
                    ).all()
                ]
                selected = None
                for c in ROADMAP_COLOR_PALETTE:
                    if c not in used:
                        selected = c
                        break
                if not selected:
                    selected = ROADMAP_COLOR_PALETTE[
                        len(used) % len(ROADMAP_COLOR_PALETTE)
                    ]
                category.color = selected
            else:
                category.color = submitted_color

            category.order = int(data.get("order", 0))

            # Verificar se slug já existe (exceto para este registro)
            existing = RoadmapCategory.query.filter(
                RoadmapCategory.slug == category.slug, RoadmapCategory.id != category_id
            ).first()

            if existing:
                flash("Slug já existe. Escolha outro.", "error")
                return redirect(request.url)

            db.session.commit()
            flash("Categoria atualizada com sucesso!", "success")
            return redirect(url_for("admin.roadmap_categories"))
        except Exception as e:
            current_app.logger.error(f"Error updating roadmap category: {str(e)}")
            error_msg = format_error_for_user(
                e, "Erro ao atualizar categoria do roadmap"
            )
            flash(error_msg, "error")
            return redirect(request.url)

    return render_template(
        "admin/roadmap_category_form.html",
        title="Editar Categoria",
        category=category,
        colors=ROADMAP_COLOR_PALETTE,
    )


@bp.route("/roadmap/categories/<int:category_id>/delete", methods=["POST"])
@login_required
@master_required
@limiter.limit(ADMIN_API_LIMIT)
def delete_roadmap_category(category_id):
    """Excluir categoria do roadmap"""
    _require_admin()

    category = RoadmapCategory.query.get_or_404(category_id)

    # Verificar se há itens nesta categoria
    if category.items.count() > 0:
        flash("Não é possível excluir categoria com itens associados.", "error")
        return redirect(url_for("admin.roadmap_categories"))

    db.session.delete(category)
    db.session.commit()

    flash("Categoria excluída com sucesso!", "success")
    return redirect(url_for("admin.roadmap_categories"))


@bp.route("/roadmap/items")
@login_required
@master_required
@limiter.limit(ADMIN_API_LIMIT)
def roadmap_items():
    """Listar todos os itens do roadmap"""
    from sqlalchemy.orm import joinedload

    # Filtros
    status_filter = request.args.get("status")
    category_filter = request.args.get("category")
    visibility_filter = request.args.get("visibility")  # public, internal, all
    priority_filter = request.args.get("priority")

    # Eager loading para evitar N+1
    query = RoadmapItem.query.options(joinedload(RoadmapItem.category)).join(
        RoadmapCategory
    )

    if status_filter:
        query = query.filter(RoadmapItem.status == status_filter)

    if category_filter:
        query = query.filter(RoadmapItem.category_id == category_filter)

    if visibility_filter == "public":
        query = query.filter(RoadmapItem.visible_to_users.is_(True))
    elif visibility_filter == "internal":
        query = query.filter(RoadmapItem.internal_only.is_(True))

    if priority_filter:
        query = query.filter(RoadmapItem.priority == priority_filter)

    # Ordenação
    sort_by = request.args.get("sort", "updated_at")
    sort_order = request.args.get("order", "desc")

    if sort_by == "title":
        order_col = RoadmapItem.title
    elif sort_by == "priority":
        order_col = RoadmapItem.priority
    elif sort_by == "status":
        order_col = RoadmapItem.status
    elif sort_by == "created_at":
        order_col = RoadmapItem.created_at
    else:
        order_col = RoadmapItem.updated_at

    if sort_order == "asc":
        query = query.order_by(order_col.asc())
    else:
        query = query.order_by(order_col.desc())

    items = query.all()
    categories = RoadmapCategory.query.filter_by(is_active=True).all()

    return render_template(
        "admin/roadmap_items.html",
        title="Itens do Roadmap",
        items=items,
        categories=categories,
        filters={
            "status": status_filter,
            "category": category_filter,
            "visibility": visibility_filter,
            "priority": priority_filter,
            "sort": sort_by,
            "order": sort_order,
        },
    )


@bp.route("/roadmap/items/new", methods=["GET", "POST"])
@login_required
@master_required
@limiter.limit(ADMIN_API_LIMIT)
@validate_with_schema(RoadmapItemSchema, location="form")
def new_roadmap_item():
    """Criar novo item do roadmap"""
    _require_admin()

    categories = RoadmapCategory.query.filter_by(is_active=True).all()
    users = User.query.filter(User.user_type.in_(["master", "admin"])).all()

    if request.method == "POST":
        try:
            data = request.validated_data

            # Extrair dados validados
            category_id = data.get("category_id")
            title = data.get("title")
            slug = data.get("slug")
            description = data.get("description")
            detailed_description = data.get("detailed_description")

            # Status e prioridade
            status = data.get("status", "planned")
            priority = data.get("priority", "medium")
            estimated_effort = data.get("estimated_effort", "medium")

            # Visibilidade
            visible_to_users = data.get("visible_to_users", False)
            internal_only = data.get("internal_only", False)
            show_new_badge = data.get("show_new_badge", False)

            # Datas
            planned_start_date = data.get("planned_start_date")
            planned_completion_date = data.get("planned_completion_date")

            # Detalhes
            business_value = data.get("business_value")
            technical_complexity = data.get("technical_complexity", "medium")
            user_impact = data.get("user_impact", "medium")

            dependencies = data.get("dependencies")
            blockers = data.get("blockers")
            tags = data.get("tags")
            notes = data.get("notes")

            assigned_to = data.get("assigned_to")
            assigned_to = int(assigned_to) if assigned_to else None

            # Verificar se slug já existe
            if RoadmapItem.query.filter_by(slug=slug).first():
                flash("Slug já existe. Escolha outro.", "error")
                return redirect(request.url)

            item = RoadmapItem(
                category_id=category_id,
                title=title,
                slug=slug,
                description=description,
                detailed_description=detailed_description,
                status=status,
                priority=priority,
                estimated_effort=estimated_effort,
                visible_to_users=visible_to_users,
                internal_only=internal_only,
                show_new_badge=show_new_badge,
                planned_start_date=planned_start_date,
                planned_completion_date=planned_completion_date,
                business_value=business_value,
                technical_complexity=technical_complexity,
                user_impact=user_impact,
                dependencies=dependencies,
                blockers=blockers,
                tags=tags,
                notes=notes,
                assigned_to=assigned_to,
                created_by=current_user.id,
            )

            db.session.add(item)
            db.session.commit()

            flash("Item do roadmap criado com sucesso!", "success")
            return redirect(url_for("admin.roadmap_items"))
        except Exception as e:
            current_app.logger.error(f"Error creating roadmap item: {str(e)}")
            error_msg = format_error_for_user(e, "Erro ao criar item do roadmap")
            flash(error_msg, "error")
            return redirect(request.url)

    return render_template(
        "admin/roadmap_item_form.html",
        title="Novo Item do Roadmap",
        categories=categories,
        users=users,
    )


@bp.route("/roadmap/items/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
@master_required
@limiter.limit(ADMIN_API_LIMIT)
@validate_with_schema(RoadmapItemSchema, location="form")
def edit_roadmap_item(item_id):
    """Editar item do roadmap"""
    import logging

    logger = logging.getLogger(__name__)

    _require_admin()
    logger.info(f"📝 Editando roadmap item {item_id}")

    item = RoadmapItem.query.get_or_404(item_id)
    categories = RoadmapCategory.query.filter_by(is_active=True).all()
    users = User.query.filter(User.user_type.in_(["master", "admin"])).all()

    if request.method == "POST":
        try:
            if not hasattr(request, "validated_data"):
                logger.error(f"❌ request.validated_data não existe!")
                return jsonify({"error": "Dados não validados"}), 400

            data = request.validated_data
            logger.info(f"✅ Dados validados recebidos: {list(data.keys())}")

            item.category_id = data.get("category_id")
            item.title = data.get("title")
            item.slug = data.get("slug")
            item.description = data.get("description")
            item.detailed_description = data.get("detailed_description")

            # Status e prioridade
            item.status = data.get("status", "planned")
            item.priority = data.get("priority", "medium")
            item.estimated_effort = data.get("estimated_effort", "medium")

            # Visibilidade
            item.visible_to_users = data.get("visible_to_users", False)
            item.internal_only = data.get("internal_only", False)
            item.show_new_badge = data.get("show_new_badge", False)

            # Datas
            item.planned_start_date = data.get("planned_start_date")
            item.planned_completion_date = data.get("planned_completion_date")

            # Atualizar datas reais se status mudou
            if item.status == "in_progress" and not item.actual_start_date:
                item.actual_start_date = datetime.now(timezone.utc).date()
            elif item.status == "completed" and not item.actual_completion_date:
                item.actual_completion_date = datetime.now(timezone.utc).date()

            # Detalhes
            item.business_value = data.get("business_value")
            item.technical_complexity = data.get("technical_complexity", "medium")
            item.user_impact = data.get("user_impact", "medium")

            item.dependencies = data.get("dependencies")
            item.blockers = data.get("blockers")
            item.tags = data.get("tags")
            item.notes = data.get("notes")

            assigned_to = data.get("assigned_to")
            item.assigned_to = int(assigned_to) if assigned_to else None

            item.last_updated_by = current_user.id
            # Verificar se slug já existe (exceto para este registro)
            existing = RoadmapItem.query.filter(
                RoadmapItem.slug == item.slug, RoadmapItem.id != item_id
            ).first()

            if existing:
                flash("Slug já existe. Escolha outro.", "error")
                return redirect(request.url)

            db.session.commit()
            logger.info(f"✅ Roadmap item {item_id} atualizado com sucesso")
            flash("Item do roadmap atualizado com sucesso!", "success")
            return redirect(url_for("admin.roadmap_items"))
        except Exception as e:
            import traceback

            logger.error(f"❌ Erro ao atualizar roadmap item {item_id}")
            logger.error(f"   Erro: {str(e)}")
            logger.error(f"   Traceback: {traceback.format_exc()}")

            current_app.logger.error(f"Error updating roadmap item: {str(e)}")
            error_msg = format_error_for_user(e, "Erro ao atualizar item do roadmap")
            flash(error_msg, "error")

            if request.accept_mimetypes.best in ["application/json", "text/json"]:
                return jsonify({"error": error_msg, "details": str(e)}), 500

            return redirect(request.url)

    return render_template(
        "admin/roadmap_item_form.html",
        title="Editar Item do Roadmap",
        item=item,
        categories=categories,
        users=users,
    )


@bp.route("/roadmap/items/<int:item_id>/delete", methods=["POST"])
@login_required
@master_required
@limiter.limit(ADMIN_API_LIMIT)
def delete_roadmap_item(item_id):
    """Excluir item do roadmap"""
    _require_admin()

    item = RoadmapItem.query.get_or_404(item_id)

    db.session.delete(item)
    db.session.commit()

    flash("Item do roadmap excluído com sucesso!", "success")
    return redirect(url_for("admin.roadmap_items"))


@bp.route("/roadmap/items/<int:item_id>/toggle-visibility", methods=["POST"])
@login_required
@master_required
@limiter.limit(ADMIN_API_LIMIT)
def toggle_roadmap_item_visibility(item_id):
    """Alternar visibilidade do item para usuários"""
    _require_admin()

    item = RoadmapItem.query.get_or_404(item_id)
    item.visible_to_users = not item.visible_to_users

    db.session.commit()

    status = "visível" if item.visible_to_users else "oculto"
    flash(f"Item agora {status} para usuários.", "success")

    return redirect(request.referrer or url_for("admin.roadmap_items"))


@bp.route("/roadmap/api/items")
@login_required
def roadmap_api_items():
    """API para obter itens do roadmap (para AJAX)"""
    _require_admin()

    items = RoadmapItem.query.join(RoadmapCategory).all()

    return jsonify([item.to_dict() for item in items])


@bp.route("/roadmap/stats")
@login_required
def roadmap_stats():
    """Estatísticas detalhadas do roadmap"""
    _require_admin()

    # Contagens por status
    status_counts = (
        db.session.query(RoadmapItem.status, func.count(RoadmapItem.id))
        .group_by(RoadmapItem.status)
        .all()
    )

    # Contagens por prioridade
    priority_counts = (
        db.session.query(RoadmapItem.priority, func.count(RoadmapItem.id))
        .group_by(RoadmapItem.priority)
        .all()
    )

    # Contagens por categoria
    category_counts = (
        db.session.query(RoadmapCategory.name, func.count(RoadmapItem.id))
        .join(RoadmapItem)
        .group_by(RoadmapCategory.id, RoadmapCategory.name)
        .all()
    )

    # Itens atrasados
    overdue_items = RoadmapItem.query.filter(
        RoadmapItem.status.in_(["planned", "in_progress"]),
        RoadmapItem.planned_completion_date < datetime.now(timezone.utc).date(),
    ).count()

    # Progresso médio
    avg_progress = (
        db.session.query(
            func.avg(
                db.case(
                    (RoadmapItem.status == "planned", 0),
                    (RoadmapItem.status == "in_progress", 50),
                    (RoadmapItem.status == "completed", 100),
                    (RoadmapItem.status == "cancelled", 0),
                    (RoadmapItem.status == "on_hold", 25),
                    else_=0,
                )
            )
        ).scalar()
        or 0
    )

    return render_template(
        "admin/roadmap_stats.html",
        title="Estatísticas do Roadmap",
        status_counts=dict(status_counts),
        priority_counts=dict(priority_counts),
        category_counts=dict(category_counts),
        overdue_items=overdue_items,
        avg_progress=round(avg_progress, 1),
    )


# =============================================================================
# ROADMAP FEEDBACK ROUTES
# =============================================================================


@bp.route("/roadmap/feedback")
@login_required
def roadmap_feedback():
    """Lista todo o feedback dos usuários sobre funcionalidades implementadas"""
    _require_admin()

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    status_filter = request.args.get("status", "all")
    rating_filter = request.args.get("rating", "all")
    category_filter = request.args.get("category", "all")

    # Query base
    query = RoadmapFeedback.query.join(RoadmapItem).join(RoadmapCategory)

    # Aplicar filtros
    if status_filter != "all":
        query = query.filter(RoadmapFeedback.status == status_filter)

    if rating_filter != "all":
        query = query.filter(RoadmapFeedback.rating == int(rating_filter))

    if category_filter != "all":
        query = query.filter(RoadmapCategory.slug == category_filter)

    # Ordenar por data de criação (mais recentes primeiro)
    query = query.order_by(RoadmapFeedback.created_at.desc())

    # Paginação
    feedback = query.paginate(page=page, per_page=per_page, error_out=False)

    # Estatísticas
    total_feedback = RoadmapFeedback.query.count()
    avg_rating = db.session.query(func.avg(RoadmapFeedback.rating)).scalar() or 0
    status_counts = (
        db.session.query(RoadmapFeedback.status, func.count(RoadmapFeedback.id))
        .group_by(RoadmapFeedback.status)
        .all()
    )

    # Categorias para filtro
    categories = RoadmapCategory.query.all()

    return render_template(
        "admin/roadmap_feedback.html",
        title="Feedback do Roadmap",
        feedback=feedback,
        total_feedback=total_feedback,
        avg_rating=round(avg_rating, 1),
        status_counts=dict(status_counts),
        categories=categories,
        filters={
            "status": status_filter,
            "rating": rating_filter,
            "category": category_filter,
        },
    )


@bp.route("/roadmap/feedback/<int:feedback_id>")
@login_required
def roadmap_feedback_detail(feedback_id):
    """Visualiza detalhes de um feedback específico"""
    _require_admin()

    feedback = RoadmapFeedback.query.get_or_404(feedback_id)

    return render_template(
        "admin/roadmap_feedback_detail.html",
        title=f"Feedback - {feedback.title or 'Sem título'}",
        feedback=feedback,
    )


@bp.route("/roadmap/feedback/<int:feedback_id>/respond", methods=["POST"])
@login_required
def roadmap_feedback_respond(feedback_id):
    """Responde a um feedback"""
    _require_admin()

    feedback = RoadmapFeedback.query.get_or_404(feedback_id)
    response_text = request.form.get("response")

    if response_text:
        feedback.add_response(response_text, current_user)
        flash("Resposta enviada com sucesso!", "success")
    else:
        flash("Por favor, digite uma resposta.", "warning")

    return redirect(url_for("admin.roadmap_feedback_detail", feedback_id=feedback_id))


@bp.route("/roadmap/feedback/<int:feedback_id>/status", methods=["POST"])
@login_required
def roadmap_feedback_status(feedback_id):
    """Atualiza status do feedback"""
    _require_admin()

    feedback = RoadmapFeedback.query.get_or_404(feedback_id)
    new_status = request.form.get("status")

    if new_status in ["pending", "reviewed", "addressed", "dismissed"]:
        feedback.status = new_status
        if new_status == "reviewed":
            feedback.mark_as_reviewed(current_user)
        db.session.commit()
        flash(
            f"Status do feedback atualizado para '{feedback.get_status_display()[0]}'.",
            "success",
        )
    else:
        flash("Status inválido.", "danger")

    return redirect(url_for("admin.roadmap_feedback_detail", feedback_id=feedback_id))


@bp.route("/roadmap/feedback/<int:feedback_id>/toggle-featured", methods=["POST"])
@login_required
def roadmap_feedback_toggle_featured(feedback_id):
    """Alterna status de destaque do feedback"""
    _require_admin()

    feedback = RoadmapFeedback.query.get_or_404(feedback_id)
    feedback.is_featured = not feedback.is_featured
    db.session.commit()

    status = "destacado" if feedback.is_featured else "removido dos destaques"
    flash(f"Feedback {status} com sucesso!", "success")

    return redirect(url_for("admin.roadmap_feedback_detail", feedback_id=feedback_id))


@bp.route("/roadmap/feedback/export")
@login_required
def roadmap_feedback_export():
    """Exporta feedback para CSV"""
    _require_admin()

    # Query com joins para incluir informações relacionadas
    feedback_query = (
        RoadmapFeedback.query.join(RoadmapItem).join(RoadmapCategory).join(User).all()
    )

    # Criar CSV
    output = StringIO()
    writer = csv.writer(output)

    # Cabeçalhos
    writer.writerow(
        [
            "ID",
            "Data",
            "Usuário",
            "Item do Roadmap",
            "Categoria",
            "Avaliação",
            "Título",
            "Comentário",
            "Pontos Positivos",
            "Pontos de Melhoria",
            "Sugestões",
            "Frequência de Uso",
            "Facilidade de Uso",
            "Status",
            "Resposta Admin",
            "Anônimo",
            "Destacado",
        ]
    )

    # Dados
    for fb in feedback_query:
        writer.writerow(
            [
                fb.id,
                fb.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                fb.user.name if not fb.is_anonymous and fb.user else "Anônimo",
                fb.roadmap_item.title,
                fb.roadmap_item.category.name,
                fb.rating,
                fb.title or "",
                fb.comment or "",
                fb.pros or "",
                fb.cons or "",
                fb.suggestions or "",
                fb.get_usage_frequency_display(),
                fb.get_ease_of_use_display(),
                fb.get_status_display()[0],
                fb.admin_response or "",
                "Sim" if fb.is_anonymous else "Não",
                "Sim" if fb.is_featured else "Não",
            ]
        )

    # Retornar arquivo CSV
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=roadmap_feedback.csv"},
    )


# ==========================================
@bp.route("/petitions/models", methods=["GET"])
@login_required
@master_required
@limiter.limit(ADMIN_API_LIMIT)
def petition_models_list():
    """Lista todos os modelos de petição"""
    from sqlalchemy.orm import joinedload

    from app.utils.error_messages import format_error_for_user

    try:
        current_app.logger.info("Acessando lista de modelos de petição")
        _require_admin()

        # Eager loading apenas para petition_type (model_sections é dynamic, não pode ser eagerly loaded)
        petition_models = (
            PetitionModel.query.options(joinedload(PetitionModel.petition_type))
            .order_by(PetitionModel.name)
            .all()
        )

        current_app.logger.info(
            f"Encontrados {len(petition_models)} modelos de petição"
        )

        return render_template(
            "admin/petition_models_list.html",
            title="Modelos de Petição",
            petition_models=petition_models,
        )
    except Exception as e:
        error_message = format_error_for_user(e, "general")
        current_app.logger.error(
            f"Erro ao carregar lista de modelos de petição: {str(e)}"
        )
        flash(error_message, "danger")
        return redirect(url_for("admin.petitions_admin"))


@bp.route("/petitions/models/new", methods=["GET", "POST"])
@login_required
@master_required
@limiter.limit(ADMIN_API_LIMIT)
@validate_with_schema(PetitionModelSchema, location="form")
def petition_model_new():
    """Criar novo modelo de petição"""
    current_app.logger.info("Acessando criação de novo modelo de petição")
    _require_admin()

    petition_types = PetitionType.query.order_by(PetitionType.name).all()
    sections = PetitionSection.query.order_by(PetitionSection.name).all()
    current_app.logger.info(f"Encontrados {len(petition_types)} tipos de petição")

    if request.method == "POST":
        current_app.logger.info("Processando POST para criar modelo")

        # Dados já foram validados!
        data = request.validated_data

        name = data.get("name")
        description = data.get("description")
        petition_type_id = data.get("petition_type_id")
        is_active = data.get("is_active", False)
        use_dynamic_form = data.get("use_dynamic_form", False)
        template_content = data.get("template_content")

        # Gerar slug único baseado no nome
        slug = generate_unique_slug(f"Modelo - {name}", PetitionModel)

        petition_model = PetitionModel(
            name=f"Modelo - {name}",
            slug=slug,
            description=description,
            petition_type_id=petition_type_id,
            is_active=is_active,
            use_dynamic_form=use_dynamic_form,
            template_content=template_content,
        )

        db.session.add(petition_model)
        db.session.commit()
        current_app.logger.info(
            f"Modelo criado com sucesso: {petition_model.name} (ID: {petition_model.id})"
        )

        # Adicionar seções se especificadas
        section_order_str = request.form.get("section_order", "")
        if section_order_str:
            # Parse da string de ordem: "order-1,order-2,order-3"
            section_ids = []
            for order_item in section_order_str.split(","):
                if order_item.startswith("order-"):
                    try:
                        section_id = int(order_item.replace("order-", ""))
                        section_ids.append(section_id)
                    except ValueError:
                        continue

            current_app.logger.info(
                f"Adicionando seções ao novo modelo {petition_model.id}: {section_ids}"
            )

            # Adicionar seções na ordem especificada
            for order, section_id in enumerate(section_ids, 1):
                section = PetitionSection.query.get(section_id)
                if section:
                    model_section = PetitionModelSection(
                        petition_model=petition_model, section=section, order=order
                    )
                    db.session.add(model_section)

            db.session.commit()

        flash("Modelo de petição criado com sucesso!", "success")
        return redirect(url_for("admin.petition_models_list"))

    return render_template(
        "admin/petition_model_form.html",
        title="Novo Modelo de Petição",
        petition_types=petition_types,
        sections=sections,
        petition_model=None,
    )


@bp.route("/petitions/models/<int:model_id>/edit", methods=["GET", "POST"])
@login_required
@master_required
@limiter.limit(ADMIN_API_LIMIT)
@validate_with_schema(PetitionModelSchema, location="form")
def petition_model_edit(model_id):
    """Editar modelo de petição"""
    _require_admin()

    petition_model = PetitionModel.query.get_or_404(model_id)
    petition_types = PetitionType.query.order_by(PetitionType.name).all()
    sections = PetitionSection.query.order_by(PetitionSection.name).all()

    current_app.logger.info(
        f"Carregando página de edição do modelo {model_id}: {petition_model.name if petition_model else 'None'}"
    )

    # Log page load with current template info to help trace missing saves
    try:
        from datetime import datetime

        user_repr = (
            getattr(current_user, "username", None)
            or getattr(current_user, "email", None)
            or current_user.get_id()
        )
        with open("debug_capture.log", "a", encoding="utf-8") as f:
            preview = (petition_model.template_content or "")[:200]
            f.write(
                f"{datetime.utcnow().isoformat()} GET model={model_id} user={user_repr} template_len={len(petition_model.template_content or '')} preview={preview}\n"
            )
    except Exception as _e:
        current_app.logger.info(f"Failed writing GET capture: {_e}")

    if request.method == "POST":
        # Temporary capture for failing submissions
        try:
            from datetime import datetime

            user_repr = (
                getattr(current_user, "username", None)
                or getattr(current_user, "email", None)
                or current_user.get_id()
            )
            with open("debug_capture.log", "a", encoding="utf-8") as f:
                try:
                    raw = request.get_data(as_text=True)
                except Exception:
                    raw = ""
                preview = raw[:200]
                f.write(
                    f"{datetime.utcnow().isoformat()} POST model={model_id} user={user_repr} keys={list(request.form.keys())} template_len={len(request.form.get('template_content') or '')} capture_len={len(request.form.get('template_content_capture') or '')} raw_preview={preview}\n"
                )
        except Exception as _ex:
            current_app.logger.info(f"Capture write failed: {_ex}")

        flash("Iniciando salvamento do modelo...", "info")
        try:
            # Dados já foram validados!
            data = request.validated_data

            petition_model.description = data.get("description")
            petition_model.petition_type_id = data.get("petition_type_id")
            petition_model.is_active = data.get("is_active", False)
            petition_model.use_dynamic_form = data.get("use_dynamic_form", False)
            template_content = data.get("template_content")

            current_app.logger.info(
                f"Saving template for model {model_id}, length: {len(template_content or '')}"
            )
            petition_model.template_content = template_content
            current_app.logger.info(f"Template set to model {model_id}")

            # Atualizar seções do modelo
            section_order_str = request.form.get("section_order", "")
            if section_order_str:
                # Parse da string de ordem: "order-1,order-2,order-3"
                section_ids = []
                for order_item in section_order_str.split(","):
                    if order_item.startswith("order-"):
                        try:
                            section_id = int(order_item.replace("order-", ""))
                            section_ids.append(section_id)
                        except ValueError:
                            continue

                current_app.logger.info(
                    f"Atualizando seções do modelo {model_id}: {section_ids}"
                )

                # Remover todas as seções atuais (uso seguro da API)
                try:
                    # Prefer explicit query delete para evitar problemas quando a relação não for dinâmica
                    PetitionModelSection.query.filter_by(
                        petition_model_id=model_id
                    ).delete(synchronize_session=False)
                except Exception as ex_del:
                    current_app.logger.error(
                        f"Erro ao limpar seções antigas do modelo {model_id}: {ex_del}"
                    )

                # Adicionar seções na nova ordem
                for order, section_id in enumerate(section_ids, 1):
                    section = PetitionSection.query.get(section_id)
                    if section:
                        model_section = PetitionModelSection(
                            petition_model=petition_model, section=section, order=order
                        )
                        db.session.add(model_section)

            db.session.add(petition_model)  # Garantir que o modelo esteja na sessão
            current_app.logger.info(f"Committing changes for model {model_id}")
            db.session.commit()
            current_app.logger.info(f"Commit successful for model {model_id}")
            flash("Modelo de petição atualizado com sucesso!", "success")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao salvar modelo {model_id}: {str(e)}")
            flash(f"Erro ao salvar: {str(e)}", "error")
            return redirect(request.url)

        return redirect(url_for("admin.petition_models_list"))

    return render_template(
        "admin/petition_model_form.html",
        title="Editar Modelo de Petição",
        petition_types=petition_types,
        sections=sections,
        petition_model=petition_model,
    )


@bp.route("/petitions/models/<int:model_id>/sections/add", methods=["POST"])
@login_required
def petition_model_add_section(model_id):
    """Adicionar seção ao modelo de petição"""
    _require_admin()

    petition_model = PetitionModel.query.get_or_404(model_id)
    section_id = request.form.get("section_id", type=int)

    current_app.logger.info(f"Adicionando seção {section_id} ao modelo {model_id}")

    if not section_id:
        flash("Seção não especificada.", "danger")
        return redirect(url_for("admin.petition_model_edit", model_id=model_id))

    section = PetitionSection.query.get_or_404(section_id)

    # Verificar se já existe
    existing = PetitionModelSection.query.filter_by(
        petition_model_id=model_id, section_id=section_id
    ).first()

    if existing:
        flash("Esta seção já está associada ao modelo.", "warning")
        return redirect(url_for("admin.petition_model_edit", model_id=model_id))

    # Calcular a próxima ordem
    max_order = (
        db.session.query(func.max(PetitionModelSection.order))
        .filter_by(petition_model_id=model_id)
        .scalar()
        or 0
    )

    model_section = PetitionModelSection(
        petition_model_id=model_id,
        section_id=section_id,
        order=max_order + 1,
        is_required=False,
        is_expanded=True,
    )

    db.session.add(model_section)
    db.session.commit()

    flash(f"Seção '{section.name}' adicionada ao modelo.", "success")
    return redirect(url_for("admin.petition_model_edit", model_id=model_id))


@bp.route(
    "/petitions/models/<int:model_id>/sections/<int:section_id>/remove",
    methods=["POST"],
)
@login_required
def petition_model_remove_section(model_id, section_id):
    """Remover seção do modelo de petição"""
    _require_admin()

    model_section = PetitionModelSection.query.filter_by(
        petition_model_id=model_id, section_id=section_id
    ).first_or_404()

    current_app.logger.info(f"Removendo seção {section_id} do modelo {model_id}")

    section_name = model_section.section.name
    db.session.delete(model_section)
    db.session.commit()

    flash(f"Seção '{section_name}' removida do modelo.", "success")
    return redirect(url_for("admin.petition_model_edit", model_id=model_id))


@bp.route("/petitions/models/<int:model_id>/sections/order", methods=["POST"])
@login_required
def petition_model_update_section_order(model_id):
    """Atualizar ordem das seções do modelo de petição"""
    _require_admin()

    petition_model = PetitionModel.query.get_or_404(model_id)
    section_orders = request.form.getlist("section_order[]")

    current_app.logger.info(
        f"Atualizando ordem das seções do modelo {model_id}: {section_orders}"
    )

    # Atualizar ordem para cada seção
    for i, order in enumerate(section_orders):
        section_id = int(order.split("-")[1])  # formato: order-section_id
        model_section = PetitionModelSection.query.filter_by(
            petition_model_id=model_id, section_id=section_id
        ).first()

        if model_section:
            model_section.order = i + 1

    db.session.commit()
    return jsonify({"success": True})


@bp.route("/petitions/models/<int:model_id>/delete", methods=["POST"])
@login_required
@master_required
@limiter.limit(ADMIN_API_LIMIT)
def petition_model_delete(model_id):
    """Excluir modelo de petição"""
    _require_admin()

    petition_model = PetitionModel.query.get_or_404(model_id)

    # Verificar se há petições usando este modelo
    if petition_model.petitions:
        flash(
            "Não é possível excluir um modelo que possui petições associadas.", "danger"
        )
        return redirect(url_for("admin.petition_models_list"))

    db.session.delete(petition_model)
    db.session.commit()

    flash("Modelo de petição excluído com sucesso!", "success")
    return redirect(url_for("admin.petition_models_list"))


@bp.route("/petitions/models/<int:model_id>/fields", methods=["GET"])
@login_required
def petition_model_fields(model_id):
    """Retornar campos disponíveis para um modelo de petição"""
    _require_admin()

    petition_model = PetitionModel.query.get_or_404(model_id)

    # Obter todas as seções do modelo (PetitionModelSection objects)
    model_sections = petition_model.get_sections_ordered()

    fields = []

    for model_section in model_sections:
        # Acessar a seção real através do relacionamento
        section = model_section.section

        # Adicionar campos do fields_schema da seção
        if section and hasattr(section, "fields_schema") and section.fields_schema:
            if isinstance(section.fields_schema, list):
                for field_def in section.fields_schema:
                    if isinstance(field_def, dict) and "name" in field_def:
                        fields.append(
                            {
                                "name": field_def.get("name"),
                                "display_name": field_def.get(
                                    "label", field_def.get("name", "")
                                ),
                                "category": section.name,
                                "field_type": field_def.get("type", "text"),
                                "required": field_def.get("required", False),
                            }
                        )

    return jsonify({"fields": fields})


# Custo em créditos para geração de template com IA
TEMPLATE_GENERATION_CREDIT_COST = 2


def _check_and_use_ai_credits(amount):
    """Verifica e debita créditos para uso de IA (master não paga)"""
    from app.models import UserCredits

    # Master não paga créditos
    if current_user.user_type == "master":
        return True, None

    user_credits = UserCredits.get_or_create(current_user.id)

    # Verificar se tem créditos suficientes
    if not user_credits.has_credits(amount):
        return False, "Créditos insuficientes para gerar template com IA"

    # Debitar créditos
    user_credits.use_credits(amount)
    return True, None


@bp.route("/petitions/models/<int:model_id>/generate_template", methods=["POST"])
@login_required
def petition_model_generate_template(model_id):
    """Gerar template Jinja2 baseado nas seções do modelo usando IA"""
    _require_admin()

    petition_model = PetitionModel.query.get_or_404(model_id)

    try:
        from app.services.ai_service import AIService

        ai_service = AIService()

        # Obter seções ordenadas com seus campos
        sections = petition_model.get_sections_ordered()

        # Construir informações detalhadas das seções
        sections_info = []
        all_fields = []
        for ms in sections:
            section = ms.section
            if section:
                section_data = {
                    "name": section.name,
                    "description": section.description or "",
                    "fields": [],
                }

                # Extrair campos da seção
                if section.fields_schema:
                    fields = (
                        section.fields_schema
                        if isinstance(section.fields_schema, list)
                        else []
                    )
                    for field in fields:
                        field_info = {
                            "name": field.get("name", ""),
                            "label": field.get("label", ""),
                            "type": field.get("type", "text"),
                            "required": field.get("required", False),
                        }
                        section_data["fields"].append(field_info)
                        all_fields.append(field_info)

                sections_info.append(section_data)

        # Se IA está configurada, usar para gerar template inteligente
        if ai_service.is_configured():
            # Verificar e debitar créditos antes de usar IA
            has_credits, error_msg = _check_and_use_ai_credits(
                TEMPLATE_GENERATION_CREDIT_COST
            )
            if not has_credits:
                return jsonify({"success": False, "error": error_msg}), 402

            # Buscar templates exemplares para few-shot learning
            # IMPORTANTE: Busca apenas exemplos do MESMO tipo de petição
            from app.models import TemplateExample

            examples = TemplateExample.get_best_examples(
                petition_type_id=petition_model.petition_type_id, limit=2
            )

            # Obter informações do tipo
            tipo_peticao = (
                petition_model.petition_type.name
                if petition_model.petition_type
                else "Cível"
            )
            categoria_tipo = (
                petition_model.petition_type.category
                if petition_model.petition_type
                else ""
            )

            # Construir seção de exemplos para o prompt
            examples_section = ""
            if examples:
                examples_section = "\n═══════════════════════════════════════════════════════════════\n"
                examples_section += (
                    f"📚 EXEMPLOS DE TEMPLATES DO TIPO '{tipo_peticao.upper()}'\n"
                )
                examples_section += (
                    "═══════════════════════════════════════════════════════════════\n"
                )
                examples_section += f"Estes são exemplos de templates APROVADOS do mesmo tipo ({tipo_peticao}).\n"
                examples_section += "Use como REFERÊNCIA de estilo, estrutura e linguagem jurídica específica:\n"

                for i, ex in enumerate(examples, 1):
                    # Mostrar apenas os primeiros 1500 caracteres de cada exemplo
                    preview = (
                        ex.template_content[:1500] + "..."
                        if len(ex.template_content) > 1500
                        else ex.template_content
                    )
                    examples_section += f"\n--- EXEMPLO {i}: {ex.name} ---\n{preview}\n"
                    ex.increment_usage()  # Incrementar contador de uso

            # Construir descrição das seções para o prompt
            sections_description = ""
            for i, sec in enumerate(sections_info, 1):
                sections_description += f"\n{i}. **{sec['name']}**"
                if sec["description"]:
                    sections_description += f" - {sec['description']}"
                if sec["fields"]:
                    sections_description += "\n   Campos disponíveis:"
                    for f in sec["fields"]:
                        req = " (obrigatório)" if f["required"] else ""
                        sections_description += (
                            f"\n   - {f['label']} ({f['name']}): tipo {f['type']}{req}"
                        )

            # Construir prompt otimizado
            prompt = f"""Você é um advogado sênior brasileiro especialista em redação de peças processuais.
Crie um template Jinja2 COMPLETO e PROFISSIONAL para a seguinte petição:

═══════════════════════════════════════════════════════════════
📋 INFORMAÇÕES DO MODELO
═══════════════════════════════════════════════════════════════

**Nome:** {petition_model.name}
**Descrição:** {petition_model.description or "Petição jurídica padrão"}
**Tipo de Petição:** {tipo_peticao}
**Categoria:** {categoria_tipo or "Geral"}

⚠️ IMPORTANTE: Este template deve seguir a estrutura e linguagem jurídica específica
   para petições do tipo "{tipo_peticao}". Não misture com outros tipos de petição.
{examples_section}
═══════════════════════════════════════════════════════════════
📑 SEÇÕES E CAMPOS DISPONÍVEIS
═══════════════════════════════════════════════════════════════
{sections_description if sections_description else "Nenhuma seção definida - crie uma estrutura básica"}

═══════════════════════════════════════════════════════════════
📝 REQUISITOS DO TEMPLATE
═══════════════════════════════════════════════════════════════

1. **CABEÇALHO FORMAL:**
   - Endereçamento correto ao juízo (usar {{{{ vara }}}})
   - Qualificação completa do autor (nome, nacionalidade, estado civil, profissão, CPF, RG, endereço)
   - Qualificação completa do réu

2. **CORPO DA PETIÇÃO:**
   - Para CADA seção listada acima, crie uma seção correspondente no template
   - Use os nomes dos campos como variáveis Jinja2: {{{{ nome_do_campo }}}}
   - Inclua títulos em MAIÚSCULAS para cada seção (ex: DOS FATOS, DO DIREITO)
   - Conecte as seções com linguagem jurídica adequada

3. **VARIÁVEIS OBRIGATÓRIAS:**
   - {{{{ vara }}}} - Vara/Juízo
   - {{{{ autor_nome }}}}, {{{{ autor_qualificacao }}}} - Dados do autor
   - {{{{ reu_nome }}}}, {{{{ reu_qualificacao }}}} - Dados do réu
   - {{{{ tipo_acao }}}} - Nome da ação
   - {{{{ valor_causa }}}} - Valor da causa (se aplicável)
   - {{{{ local }}}}, {{{{ data }}}} - Local e data
   - {{{{ advogado_nome }}}}, {{{{ advogado_oab }}}} - Dados do advogado

4. **ESTRUTURA E FORMATAÇÃO:**
   - Use parágrafos bem estruturados
   - Inclua marcadores/numeração onde apropriado
   - Fundamentos jurídicos com citação de artigos
   - Pedidos claros e objetivos
   - Requerimentos finais (citação, provas, etc.)

5. **LINGUAGEM:**
   - Formal e técnica
   - Termos jurídicos adequados
   - Sem erros gramaticais
   - Tom respeitoso ao juízo

═══════════════════════════════════════════════════════════════
⚠️ INSTRUÇÕES IMPORTANTES
═══════════════════════════════════════════════════════════════

- Retorne APENAS o template Jinja2, sem explicações ou comentários
- Use {{{{ variavel }}}} para variáveis (duas chaves)
- NÃO inclua blocos de código markdown (```)
- O template deve estar pronto para uso imediato

GERE O TEMPLATE COMPLETO:"""

            messages = [
                {
                    "role": "system",
                    "content": """Você é um assistente jurídico especializado em criar templates de petições no formato Jinja2.
Suas petições são reconhecidas pela qualidade técnica, clareza e conformidade com as normas processuais brasileiras.
Você domina o CPC, CDC, CC e demais legislações pertinentes.
Sempre cria templates completos, profissionais e prontos para uso.""",
                },
                {"role": "user", "content": prompt},
            ]

            try:
                template_content, metadata = ai_service._call_openai(
                    messages=messages,
                    model="gpt-4o-mini",
                    temperature=0.3,  # Menor temperatura para mais consistência
                    max_tokens=4000,  # Mais tokens para templates completos
                )

                # Limpar possíveis marcadores de código
                template_content = template_content.strip()
                if template_content.startswith("```"):
                    lines = template_content.split("\n")
                    template_content = "\n".join(
                        lines[1:-1] if lines[-1] == "```" else lines[1:]
                    )

                return jsonify(
                    {
                        "success": True,
                        "template": template_content.strip(),
                        "ai_generated": True,
                        "metadata": metadata,
                    }
                )
            except Exception as ai_error:
                current_app.logger.warning(
                    f"Erro na IA, usando fallback: {str(ai_error)}"
                )
                # Fallback para geração básica

        # Fallback: geração básica sem IA
        template_parts = []

        # Cabeçalho da petição
        template_parts.append(
            "EXCELENTÍSSIMO(A) SENHOR(A) DOUTOR(A) JUIZ(ÍZA) DE DIREITO DA {{ vara }}"
        )
        template_parts.append("")
        template_parts.append("{{ autor_nome }}, {{ autor_qualificacao }}, vem propor:")
        template_parts.append("")
        template_parts.append("{{ tipo_acao }}")
        template_parts.append("")
        template_parts.append("em face de {{ reu_nome }}, {{ reu_qualificacao }}")
        template_parts.append("")

        # Adicionar seções dinâmicas
        for sec in sections_info:
            section_title = sec["name"].upper()
            template_parts.append(section_title)
            template_parts.append("")
            for field in sec["fields"]:
                template_parts.append(f"{{{{ {field['name']} }}}}")
            template_parts.append("")

        # Rodapé
        template_parts.append("{{ local }}, {{ data }}")
        template_parts.append("")
        template_parts.append("{{ advogado_nome }}")
        template_parts.append("{{ advogado_oab }}")

        template_content = "\n".join(template_parts)

        return jsonify(
            {"success": True, "template": template_content, "ai_generated": False}
        )

    except Exception as e:
        current_app.logger.error(f"Erro ao gerar template: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/petitions/models/generate_template_preview", methods=["POST"])
@login_required
def petition_model_generate_template_preview():
    """Gerar template Jinja2 para preview (antes de criar o modelo) usando IA"""
    _require_admin()

    try:
        from app.services.ai_service import AIService

        data = request.get_json() or {}
        model_name = data.get("name", "Petição")
        model_description = data.get("description", "")
        section_ids = data.get("section_ids", [])
        petition_type_id = data.get("petition_type_id")  # ID do tipo de petição

        # Obter informações do tipo de petição
        tipo_peticao = "Cível"
        categoria_tipo = "Geral"
        if petition_type_id:
            petition_type = PetitionType.query.get(petition_type_id)
            if petition_type:
                tipo_peticao = petition_type.name
                categoria_tipo = petition_type.category or "Geral"

        # Obter seções com seus campos detalhados
        sections_info = []
        if section_ids:
            sections = PetitionSection.query.filter(
                PetitionSection.id.in_(section_ids)
            ).all()
            # Manter a ordem original e extrair campos
            section_map = {s.id: s for s in sections}
            for sid in section_ids:
                section = section_map.get(sid)
                if section:
                    section_data = {
                        "name": section.name,
                        "description": section.description or "",
                        "fields": [],
                    }
                    if section.fields_schema:
                        fields = (
                            section.fields_schema
                            if isinstance(section.fields_schema, list)
                            else []
                        )
                        for field in fields:
                            section_data["fields"].append(
                                {
                                    "name": field.get("name", ""),
                                    "label": field.get("label", ""),
                                    "type": field.get("type", "text"),
                                    "required": field.get("required", False),
                                }
                            )
                    sections_info.append(section_data)

        ai_service = AIService()

        # Se IA está configurada, usar para gerar template inteligente
        if ai_service.is_configured():
            # Verificar e debitar créditos antes de usar IA
            has_credits, error_msg = _check_and_use_ai_credits(
                TEMPLATE_GENERATION_CREDIT_COST
            )
            if not has_credits:
                return jsonify({"success": False, "error": error_msg}), 402

            # Buscar templates exemplares APENAS do mesmo tipo de petição
            examples_section = ""
            if petition_type_id:
                from app.models import TemplateExample

                examples = TemplateExample.get_best_examples(
                    petition_type_id=petition_type_id, limit=2
                )
                if examples:
                    examples_section = "\n═══════════════════════════════════════════════════════════════\n"
                    examples_section += (
                        f"📚 EXEMPLOS DE TEMPLATES DO TIPO '{tipo_peticao.upper()}'\n"
                    )
                    examples_section += "═══════════════════════════════════════════════════════════════\n"
                    examples_section += f"Estes são exemplos de templates APROVADOS do mesmo tipo ({tipo_peticao}).\n"
                    examples_section += "Use como REFERÊNCIA de estilo, estrutura e linguagem jurídica específica:\n"

                    for i, ex in enumerate(examples, 1):
                        preview = (
                            ex.template_content[:1500] + "..."
                            if len(ex.template_content) > 1500
                            else ex.template_content
                        )
                        examples_section += (
                            f"\n--- EXEMPLO {i}: {ex.name} ---\n{preview}\n"
                        )
                        ex.increment_usage()

            # Construir descrição das seções para o prompt
            sections_description = ""
            for i, sec in enumerate(sections_info, 1):
                sections_description += f"\n{i}. **{sec['name']}**"
                if sec["description"]:
                    sections_description += f" - {sec['description']}"
                if sec["fields"]:
                    sections_description += "\n   Campos disponíveis:"
                    for f in sec["fields"]:
                        req = " (obrigatório)" if f["required"] else ""
                        sections_description += (
                            f"\n   - {f['label']} ({f['name']}): tipo {f['type']}{req}"
                        )

            prompt = f"""Você é um advogado sênior brasileiro especialista em redação de peças processuais.
Crie um template Jinja2 COMPLETO e PROFISSIONAL para a seguinte petição:

═══════════════════════════════════════════════════════════════
📋 INFORMAÇÕES DO MODELO
═══════════════════════════════════════════════════════════════

**Nome:** {model_name}
**Descrição:** {model_description or "Petição jurídica padrão"}
**Tipo de Petição:** {tipo_peticao}
**Categoria:** {categoria_tipo}

⚠️ IMPORTANTE: Este template deve seguir a estrutura e linguagem jurídica específica
   para petições do tipo "{tipo_peticao}". Não misture com outros tipos de petição.
{examples_section}
═══════════════════════════════════════════════════════════════
📑 SEÇÕES E CAMPOS DISPONÍVEIS
═══════════════════════════════════════════════════════════════
{sections_description if sections_description else "Nenhuma seção definida - crie uma estrutura básica"}

═══════════════════════════════════════════════════════════════
📝 REQUISITOS DO TEMPLATE
═══════════════════════════════════════════════════════════════

1. **CABEÇALHO FORMAL:**
   - Endereçamento correto ao juízo (usar {{{{ vara }}}})
   - Qualificação completa do autor (nome, nacionalidade, estado civil, profissão, CPF, RG, endereço)
   - Qualificação completa do réu

2. **CORPO DA PETIÇÃO:**
   - Para CADA seção listada acima, crie uma seção correspondente no template
   - Use os nomes dos campos como variáveis Jinja2: {{{{ nome_do_campo }}}}
   - Inclua títulos em MAIÚSCULAS para cada seção (ex: DOS FATOS, DO DIREITO)
   - Conecte as seções com linguagem jurídica adequada

3. **VARIÁVEIS OBRIGATÓRIAS:**
   - {{{{ vara }}}} - Vara/Juízo
   - {{{{ autor_nome }}}}, {{{{ autor_qualificacao }}}} - Dados do autor
   - {{{{ reu_nome }}}}, {{{{ reu_qualificacao }}}} - Dados do réu
   - {{{{ tipo_acao }}}} - Nome da ação
   - {{{{ valor_causa }}}} - Valor da causa (se aplicável)
   - {{{{ local }}}}, {{{{ data }}}} - Local e data
   - {{{{ advogado_nome }}}}, {{{{ advogado_oab }}}} - Dados do advogado

4. **ESTRUTURA E FORMATAÇÃO:**
   - Use parágrafos bem estruturados
   - Inclua marcadores/numeração onde apropriado
   - Fundamentos jurídicos com citação de artigos
   - Pedidos claros e objetivos
   - Requerimentos finais (citação, provas, etc.)

5. **LINGUAGEM:**
   - Formal e técnica
   - Termos jurídicos adequados
   - Sem erros gramaticais
   - Tom respeitoso ao juízo

═══════════════════════════════════════════════════════════════
⚠️ INSTRUÇÕES IMPORTANTES
═══════════════════════════════════════════════════════════════

- Retorne APENAS o template Jinja2, sem explicações ou comentários
- Use {{{{ variavel }}}} para variáveis (duas chaves)
- NÃO inclua blocos de código markdown (```)
- O template deve estar pronto para uso imediato

GERE O TEMPLATE COMPLETO:"""

            messages = [
                {
                    "role": "system",
                    "content": """Você é um assistente jurídico especializado em criar templates de petições no formato Jinja2.
Suas petições são reconhecidas pela qualidade técnica, clareza e conformidade com as normas processuais brasileiras.
Você domina o CPC, CDC, CC e demais legislações pertinentes.
Sempre cria templates completos, profissionais e prontos para uso.""",
                },
                {"role": "user", "content": prompt},
            ]

            try:
                template_content, metadata = ai_service._call_openai(
                    messages=messages,
                    model="gpt-4o-mini",
                    temperature=0.3,  # Menor temperatura para mais consistência
                    max_tokens=4000,  # Mais tokens para templates completos
                )

                # Limpar possíveis marcadores de código
                template_content = template_content.strip()
                if template_content.startswith("```"):
                    lines = template_content.split("\n")
                    template_content = "\n".join(
                        lines[1:-1] if lines[-1] == "```" else lines[1:]
                    )

                return jsonify(
                    {
                        "success": True,
                        "template": template_content.strip(),
                        "ai_generated": True,
                    }
                )
            except Exception as ai_error:
                current_app.logger.warning(
                    f"Erro na IA, usando fallback: {str(ai_error)}"
                )

        # Fallback: geração básica sem IA
        template_parts = []
        template_parts.append(
            "EXCELENTÍSSIMO(A) SENHOR(A) DOUTOR(A) JUIZ(ÍZA) DE DIREITO DA {{ vara }}"
        )
        template_parts.append("")
        template_parts.append("{{ autor_nome }}, {{ autor_qualificacao }}, vem propor:")
        template_parts.append("")
        template_parts.append("{{ tipo_acao }}")
        template_parts.append("")
        template_parts.append("em face de {{ reu_nome }}, {{ reu_qualificacao }}")
        template_parts.append("")

        for sec in sections_info:
            section_title = sec["name"].upper()
            template_parts.append(section_title)
            template_parts.append("")
            for field in sec["fields"]:
                template_parts.append(f"{{{{ {field['name']} }}}}")
            template_parts.append("")

        template_parts.append("{{ local }}, {{ data }}")
        template_parts.append("")
        template_parts.append("{{ advogado_nome }}")
        template_parts.append("{{ advogado_oab }}")

        template_content = "\n".join(template_parts)

        return jsonify(
            {"success": True, "template": template_content, "ai_generated": False}
        )

    except Exception as e:
        current_app.logger.error(f"Erro ao gerar template preview: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/petitions/sections/fields_by_ids", methods=["POST"])
@login_required
def petition_sections_fields_by_ids():
    """Retornar campos das seções selecionadas (para modo criação)"""
    _require_admin()

    data = request.get_json()
    section_ids = data.get("section_ids", [])

    if not section_ids:
        return jsonify({"fields": []})

    try:
        sections = PetitionSection.query.filter(
            PetitionSection.id.in_(section_ids)
        ).all()
        all_fields = []

        for section in sections:
            if section.fields_schema:
                schema = section.fields_schema
                if isinstance(schema, str):
                    import json

                    schema = json.loads(schema)

                # schema pode ser uma lista de campos diretamente ou um dict com "fields"
                if isinstance(schema, list):
                    fields = schema
                elif isinstance(schema, dict):
                    fields = schema.get("fields", [])
                else:
                    fields = []

                for field in fields:
                    if isinstance(field, dict):
                        field_data = {
                            "name": field.get("name", field.get("field_name", "")),
                            "display_name": field.get(
                                "label", field.get("display_name", "")
                            ),
                            "category": section.name,
                        }
                        all_fields.append(field_data)

        return jsonify({"fields": all_fields})

    except Exception as e:
        current_app.logger.error(f"Erro ao carregar campos: {str(e)}")
        return jsonify({"fields": [], "error": str(e)}), 500


@bp.route("/petitions/models/validate_template_generic", methods=["POST"])
@login_required
def petition_model_validate_template_generic():
    """Validar template Jinja2 (sem modelo específico)"""
    _require_admin()

    data = request.get_json()
    template = data.get("template", "")

    if not template.strip():
        return jsonify({"valid": False, "errors": ["Template vazio"]})

    try:
        from jinja2 import Template, TemplateSyntaxError

        Template(template)
        return jsonify({"valid": True})

    except TemplateSyntaxError as e:
        return jsonify(
            {
                "valid": False,
                "errors": [f"Erro de sintaxe na linha {e.lineno}: {e.message}"],
            }
        )
    except Exception as e:
        return jsonify({"valid": False, "errors": [f"Erro desconhecido: {str(e)}"]})


@bp.route("/petitions/models/preview_template_generic", methods=["POST"])
@login_required
def petition_model_preview_template_generic():
    """Gerar preview do template Jinja2 (sem modelo específico)"""
    _require_admin()

    data = request.get_json()
    template_content = data.get("template", "")

    if not template_content.strip():
        return jsonify({"success": False, "error": "Template vazio"})

    try:
        from jinja2 import Template

        # Criar dados de exemplo genéricos para preview
        sample_data = {
            "vara": "1ª Vara Cível da Comarca de São Paulo",
            "autor_nome": "João Silva Santos",
            "autor_qualificacao": "brasileiro, casado, empresário, portador do CPF 123.456.789-00",
            "tipo_acao": "AÇÃO CÍVEL",
            "reu_nome": "Empresa XYZ Ltda",
            "reu_qualificacao": "pessoa jurídica de direito privado, inscrita no CNPJ 12.345.678/0001-90",
            "local": "São Paulo",
            "data": "15 de janeiro de 2024",
            "advogado_nome": "Dr. Maria Aparecida",
            "advogado_oab": "OAB/SP 123.456",
            "fatos": "[DESCRIÇÃO DOS FATOS]",
            "fundamentos": "[FUNDAMENTOS JURÍDICOS]",
            "pedidos": "[PEDIDOS]",
            "valor_causa": "10.000,00",
        }

        template = Template(template_content)
        rendered = template.render(**sample_data)

        return jsonify({"success": True, "preview": rendered})

    except Exception as e:
        current_app.logger.error(f"Erro ao gerar preview: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/petitions/models/<int:model_id>/validate_template", methods=["POST"])
@login_required
def petition_model_validate_template(model_id):
    """Validar template Jinja2"""
    _require_admin()

    petition_model = PetitionModel.query.get_or_404(model_id)
    data = request.get_json()

    template = data.get("template", "")

    if not template.strip():
        return jsonify({"valid": False, "errors": ["Template vazio"]})

    try:
        # Tentar compilar o template Jinja2
        from jinja2 import Template, TemplateSyntaxError

        Template(template)
        return jsonify({"valid": True})

    except TemplateSyntaxError as e:
        return jsonify(
            {
                "valid": False,
                "errors": [f"Erro de sintaxe na linha {e.lineno}: {e.message}"],
            }
        )
    except Exception as e:
        return jsonify({"valid": False, "errors": [f"Erro desconhecido: {str(e)}"]})


@bp.route("/petitions/models/<int:model_id>/preview_template", methods=["POST"])
@login_required
def petition_model_preview_template(model_id):
    """Gerar preview do template Jinja2"""
    _require_admin()

    petition_model = PetitionModel.query.get_or_404(model_id)
    data = request.get_json()

    template_content = data.get("template", "")

    if not template_content.strip():
        return jsonify({"success": False, "error": "Template vazio"})

    try:
        from jinja2 import Template

        # Criar dados de exemplo para preview
        sample_data = {
            "vara": "1ª Vara Cível da Comarca de São Paulo",
            "autor_nome": "João Silva Santos",
            "autor_qualificacao": "brasileiro, casado, empresário, portador do CPF 123.456.789-00, residente e domiciliado na Rua das Flores, 123, São Paulo/SP",
            "tipo_acao": "AÇÃO DE COBRANÇA",
            "reu_nome": "Empresa XYZ Ltda",
            "reu_qualificacao": "pessoa jurídica de direito privado, inscrita no CNPJ 12.345.678/0001-90, com sede na Avenida Paulista, 1000, São Paulo/SP",
            "local": "São Paulo",
            "data": "15 de janeiro de 2024",
            "advogado_nome": "Dr. Maria Aparecida",
            "advogado_oab": "OAB/SP 123.456",
        }

        # Adicionar campos das seções como dados de exemplo
        sections = petition_model.get_sections_ordered()
        for model_section in sections:
            section = model_section.section
            if section:
                section_name = section.name.upper().replace(" ", "_")
                sample_data[section_name] = f"[CONTEÚDO DA SEÇÃO: {section.name}]"

        # Renderizar template
        template = Template(template_content)
        rendered = template.render(**sample_data)

        return jsonify({"success": True, "preview": rendered})

    except Exception as e:
        current_app.logger.error(f"Erro ao gerar preview: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/petitions/models/<int:model_id>/generate_with_ai", methods=["POST"])
@login_required
def petition_model_generate_with_ai(model_id):
    """Gerar conteúdo usando IA"""
    _require_admin()

    petition_model = PetitionModel.query.get_or_404(model_id)
    data = request.get_json()

    prompt = data.get("prompt", "").strip()

    if not prompt:
        return jsonify({"success": False, "error": "Prompt vazio"})

    try:
        # Importar serviço de IA
        from app.ai.services import AIService

        ai_service = AIService()

        # Verificar créditos do usuário
        user_credits = UserCredits.get_or_create(current_user.id)
        if not user_credits.has_credits(1):
            return jsonify(
                {"success": False, "error": "Créditos insuficientes para usar a IA"}
            )

        # Contexto adicional sobre o modelo
        context = f"""
        Modelo de Petição: {petition_model.name}
        Tipo: {petition_model.petition_type.name if petition_model.petition_type else "N/A"}
        Descrição: {petition_model.description or "N/A"}
        """

        # Gerar conteúdo
        generated_content = ai_service.generate_petition_content(
            prompt=prompt, context=context
        )

        # Deduzir créditos
        user_credits.use_credits(1)

        return jsonify(
            {
                "success": True,
                "content": generated_content,
                "credits_remaining": user_credits.balance,
            }
        )

    except Exception as e:
        current_app.logger.error(f"Erro ao gerar com IA: {str(e)}")
        return jsonify({"success": False, "error": "Erro interno do servidor"}), 500


# ============================================================================
# ROTAS DE FEEDBACK E EXEMPLOS DE TEMPLATES
# ============================================================================


@bp.route("/petitions/templates/feedback", methods=["POST"])
@login_required
def petition_template_feedback():
    """Registrar feedback do usuário sobre template gerado pela IA"""
    _require_admin()

    from app.models import AIGenerationFeedback

    data = request.get_json() or {}

    try:
        feedback = AIGenerationFeedback(
            petition_model_id=data.get("model_id"),
            generated_template=data.get("template", ""),
            rating=data.get("rating", 3),
            feedback_type=data.get("feedback_type", "neutral"),
            feedback_text=data.get("feedback_text"),
            action_taken=data.get("action_taken"),
            edited_template=data.get("edited_template"),
            prompt_used=data.get("prompt_used"),
            sections_used=data.get("sections_used"),
            user_id=current_user.id,
        )

        db.session.add(feedback)
        db.session.commit()

        return jsonify({"success": True, "feedback_id": feedback.id})

    except Exception as e:
        current_app.logger.error(f"Erro ao salvar feedback: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/petitions/templates/examples", methods=["GET"])
@login_required
def petition_template_examples_list():
    """Listar templates exemplares"""
    _require_admin()

    from app.models import TemplateExample

    examples = TemplateExample.query.order_by(
        TemplateExample.quality_score.desc(), TemplateExample.usage_count.desc()
    ).all()

    return render_template(
        "admin/template_examples_list.html",
        examples=examples,
        petition_types=PetitionType.query.order_by(PetitionType.name).all(),
    )


@bp.route("/petitions/templates/examples/new", methods=["GET", "POST"])
@login_required
def petition_template_example_new():
    """Criar novo template exemplar"""
    _require_admin()

    from app.models import TemplateExample

    if request.method == "POST":
        try:
            example = TemplateExample(
                name=request.form.get("name"),
                description=request.form.get("description"),
                template_content=request.form.get("template_content"),
                petition_type_id=request.form.get("petition_type_id") or None,
                tags=request.form.get("tags"),
                quality_score=int(request.form.get("quality_score", 5)),
                source="manual",
                created_by=current_user.id,
            )

            db.session.add(example)
            db.session.commit()

            flash("Template exemplar criado com sucesso!", "success")
            return redirect(url_for("admin.petition_template_examples_list"))

        except Exception as e:
            flash(f"Erro ao criar template: {str(e)}", "error")

    return render_template(
        "admin/template_example_form.html",
        example=None,
        petition_types=PetitionType.query.order_by(PetitionType.name).all(),
    )


@bp.route(
    "/petitions/templates/examples/<int:example_id>/edit", methods=["GET", "POST"]
)
@login_required
def petition_template_example_edit(example_id):
    """Editar template exemplar"""
    _require_admin()

    from app.models import TemplateExample

    example = TemplateExample.query.get_or_404(example_id)

    if request.method == "POST":
        try:
            example.name = request.form.get("name")
            example.description = request.form.get("description")
            example.template_content = request.form.get("template_content")
            example.petition_type_id = request.form.get("petition_type_id") or None
            example.tags = request.form.get("tags")
            example.quality_score = int(request.form.get("quality_score", 5))

            db.session.commit()

            flash("Template exemplar atualizado com sucesso!", "success")
            return redirect(url_for("admin.petition_template_examples_list"))

        except Exception as e:
            flash(f"Erro ao atualizar template: {str(e)}", "error")

    return render_template(
        "admin/template_example_form.html",
        example=example,
        petition_types=PetitionType.query.order_by(PetitionType.name).all(),
    )


@bp.route("/petitions/templates/examples/<int:example_id>/delete", methods=["POST"])
@login_required
def petition_template_example_delete(example_id):
    """Excluir template exemplar"""
    _require_admin()

    from app.models import TemplateExample

    example = TemplateExample.query.get_or_404(example_id)

    try:
        db.session.delete(example)
        db.session.commit()

        # Se for AJAX, retornar JSON
        if request.is_json or request.headers.get("Content-Type") == "application/json":
            return jsonify({"success": True})

        flash("Template exemplar excluído com sucesso!", "success")

    except Exception as e:
        if request.is_json or request.headers.get("Content-Type") == "application/json":
            return jsonify({"success": False, "error": str(e)}), 500
        flash(f"Erro ao excluir template: {str(e)}", "error")

    return redirect(url_for("admin.petition_template_examples_list"))


@bp.route("/petitions/models/<int:model_id>/save_as_example", methods=["POST"])
@login_required
def petition_model_save_as_example(model_id):
    """Salvar template de um modelo como exemplo de alta qualidade"""
    _require_admin()

    from app.models import TemplateExample

    petition_model = PetitionModel.query.get_or_404(model_id)

    if not petition_model.template_content:
        return jsonify({"success": False, "error": "Modelo não possui template"}), 400

    try:
        # Verificar se já existe um exemplo deste modelo
        existing = TemplateExample.query.filter_by(original_model_id=model_id).first()

        if existing:
            # Atualizar existente
            existing.template_content = petition_model.template_content
            existing.quality_score = min(
                existing.quality_score + 1, 10
            )  # Aumentar score
            flash("Template exemplar atualizado!", "success")
        else:
            # Criar novo
            example = TemplateExample(
                name=petition_model.name,
                description=petition_model.description,
                template_content=petition_model.template_content,
                petition_type_id=petition_model.petition_type_id,
                source="ai_approved",
                original_model_id=model_id,
                created_by=current_user.id,
                quality_score=7,  # Score inicial bom para templates aprovados
            )
            db.session.add(example)
            flash("Template salvo como exemplo de alta qualidade!", "success")

        db.session.commit()

        return jsonify({"success": True})

    except Exception as e:
        current_app.logger.error(f"Erro ao salvar exemplo: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/audit-logs")
@login_required
def audit_logs():
    """Visualizar logs de auditoria do sistema"""
    _require_admin()

    # Parâmetros de filtro
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    entity_type = request.args.get("entity_type")
    entity_id = request.args.get("entity_id", type=int)
    user_id = request.args.get("user_id", type=int)
    action = request.args.get("action")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    # Construir query
    query = AuditLog.query

    if entity_type:
        query = query.filter_by(entity_type=entity_type)
    if entity_id:
        query = query.filter_by(entity_id=entity_id)
    if user_id:
        query = query.filter_by(user_id=user_id)
    if action:
        query = query.filter_by(action=action)

    # Filtro de data
    if date_from:
        from datetime import datetime

        query = query.filter(AuditLog.timestamp >= datetime.fromisoformat(date_from))
    if date_to:
        from datetime import datetime

        query = query.filter(AuditLog.timestamp <= datetime.fromisoformat(date_to))

    # Paginação
    logs = query.order_by(AuditLog.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Estatísticas
    total_logs = AuditLog.query.count()
    today_logs = AuditLog.query.filter(
        func.date(AuditLog.timestamp) == func.date(func.now())
    ).count()

    # Opções para filtros
    entity_types = db.session.query(AuditLog.entity_type).distinct().all()
    entity_types = [et[0] for et in entity_types]

    actions = db.session.query(AuditLog.action).distinct().all()
    actions = [a[0] for a in actions]

    # IDs recentes por tipo de entidade (últimos 5 IDs ÚNICOS apenas)
    recent_entity_ids = {}
    for et in entity_types:
        recent_ids = (
            db.session.query(AuditLog.entity_id, AuditLog.timestamp)
            .filter(AuditLog.entity_type == et)
            .order_by(AuditLog.timestamp.desc())
            .limit(100)
            .all()
        )
        # Remove duplicatas mantendo ordem
        seen = set()
        unique_ids = []
        for item in recent_ids:
            eid = int(item[0])
            if eid not in seen:
                seen.add(eid)
                unique_ids.append(eid)
                if len(unique_ids) >= 5:  # Apenas 5 IDs únicos
                    break
        recent_entity_ids[et] = unique_ids

    # IDs de usuários recentes (5 IDs ÚNICOS apenas)
    recent_user_ids_query = (
        db.session.query(AuditLog.user_id, AuditLog.timestamp)
        .filter(AuditLog.user_id.isnot(None))
        .order_by(AuditLog.timestamp.desc())
        .limit(100)
        .all()
    )
    # Remove duplicatas
    seen = set()
    recent_user_ids = []
    for item in recent_user_ids_query:
        uid = int(item[0])
        if uid not in seen:
            seen.add(uid)
            recent_user_ids.append(uid)
            if len(recent_user_ids) >= 5:  # Apenas 5 IDs únicos
                break

    return render_template(
        "admin/audit_logs.html",
        title="Logs de Auditoria",
        logs=logs,
        total_logs=total_logs,
        today_logs=today_logs,
        entity_types=entity_types,
        actions=actions,
        recent_entity_ids=recent_entity_ids,
        recent_user_ids=recent_user_ids,
        filters={
            "entity_type": entity_type,
            "entity_id": entity_id,
            "user_id": user_id,
            "action": action,
            "date_from": date_from,
            "date_to": date_to,
        },
    )


@bp.route("/audit-logs/<int:log_id>")
@login_required
def audit_log_detail(log_id):
    """Visualizar detalhes de um log de auditoria específico"""
    _require_admin()

    log = AuditLog.query.get_or_404(log_id)

    return render_template(
        "admin/audit_log_detail.html", title=f"Log de Auditoria #{log.id}", log=log
    )


# ==============================================================================
# Template Examples - Few-Shot Learning
# ==============================================================================


@bp.route("/petitions/models/<int:model_id>/save_as_example", methods=["POST"])
@login_required
def save_template_as_example(model_id):
    """Salvar um modelo de petição como template exemplar para few-shot learning"""
    _require_admin()

    try:
        from app.models import TemplateExample

        petition_model = PetitionModel.query.get_or_404(model_id)

        # Verificar se já existe um exemplo baseado neste modelo
        existing = TemplateExample.query.filter_by(original_model_id=model_id).first()

        if existing:
            return jsonify(
                {
                    "success": False,
                    "error": "Este modelo já foi salvo como exemplo de referência.",
                }
            ), 400

        # Verificar se tem conteúdo de template
        if not petition_model.template_content:
            return jsonify(
                {
                    "success": False,
                    "error": "O modelo não possui conteúdo de template para salvar.",
                }
            ), 400

        # Verificar se tem tipo de petição (importante para few-shot)
        if not petition_model.petition_type_id:
            return jsonify(
                {
                    "success": False,
                    "error": "O modelo precisa ter um tipo de petição definido para ser salvo como exemplo.",
                }
            ), 400

        data = request.get_json() or {}
        quality_score = data.get("quality_score", 5.0)
        tags = data.get("tags", "")

        # Criar o exemplo
        example = TemplateExample(
            name=petition_model.name,
            description=petition_model.description
            or f"Template exemplar: {petition_model.name}",
            template_content=petition_model.template_content,
            petition_type_id=petition_model.petition_type_id,
            tags=str(tags)[:500] if tags else "",  # Limitar tamanho das tags
            quality_score=min(max(float(quality_score), 1.0), 5.0),  # Entre 1 e 5
            source="approved_model",
            original_model_id=model_id,
            created_by=current_user.id,
            is_active=True,
        )

        db.session.add(example)
        db.session.commit()

        flash(
            f"Template '{petition_model.name}' salvo como exemplo de referência!",
            "success",
        )

        return jsonify(
            {
                "success": True,
                "message": "Template salvo como exemplo de referência para melhorar gerações futuras da IA.",
                "example_id": example.id,
            }
        )
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao salvar exemplo: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/petitions/models/<int:model_id>/ai_feedback", methods=["POST"])
@login_required
def save_ai_generation_feedback(model_id):
    """Salvar feedback sobre geração de template por IA"""
    _require_admin()

    try:
        from app.models import AIGenerationFeedback

        petition_model = PetitionModel.query.get_or_404(model_id)
        data = request.get_json() or {}

        # Validar dados
        rating = data.get("rating")
        if not rating:
            return jsonify({"success": False, "error": "Rating é obrigatório."}), 400

        try:
            rating_int = int(rating)
            if not (1 <= rating_int <= 5):
                raise ValueError("Rating fora do intervalo")
        except (ValueError, TypeError):
            return jsonify(
                {"success": False, "error": "Rating deve ser um número entre 1 e 5."}
            ), 400

        feedback = AIGenerationFeedback(
            petition_model_id=model_id,
            generated_template=data.get("generated_template", "")[
                :50000
            ],  # Limitar tamanho
            rating=rating_int,
            feedback_type=data.get(
                "feedback_type", "general"
            ),  # positive, negative, suggestion, general
            feedback_text=data.get("feedback_text", "")[:1000],  # Limitar tamanho
            action_taken=data.get(
                "action_taken", "none"
            ),  # used, edited, discarded, none
            edited_template=data.get("edited_template"),
            prompt_used=data.get("prompt_used"),
            sections_used=data.get("sections_used"),
            user_id=current_user.id,
        )

        db.session.add(feedback)
        db.session.commit()

        # Se feedback muito positivo (4-5 estrelas) e foi usado/editado, sugerir salvar como exemplo
        suggest_save = rating_int >= 4 and data.get("action_taken") in [
            "used",
            "edited",
        ]

        return jsonify(
            {
                "success": True,
                "message": "Obrigado pelo feedback! Isso nos ajuda a melhorar a IA.",
                "feedback_id": feedback.id,
                "suggest_save_as_example": suggest_save,
            }
        )
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao salvar feedback: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/template-examples")
@login_required
def template_examples_list():
    """Lista todos os templates exemplares"""
    _require_admin()

    from app.models import TemplateExample

    examples = TemplateExample.query.order_by(
        TemplateExample.quality_score.desc(), TemplateExample.usage_count.desc()
    ).all()

    return render_template(
        "admin/template_examples.html", title="Templates Exemplares", examples=examples
    )


@bp.route("/template-examples/<int:example_id>/toggle", methods=["POST"])
@login_required
def toggle_template_example(example_id):
    """Ativar/desativar um template exemplar"""
    _require_admin()

    try:
        from app.models import TemplateExample

        example = TemplateExample.query.get_or_404(example_id)
        example.is_active = not example.is_active
        db.session.commit()

        status = "ativado" if example.is_active else "desativado"
        flash(f"Template exemplar '{example.name}' {status}!", "success")

        return jsonify({"success": True, "is_active": example.is_active})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao toggle exemplo: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/template-examples/<int:example_id>", methods=["DELETE"])
@login_required
def delete_template_example(example_id):
    """Excluir um template exemplar"""
    _require_admin()

    try:
        from app.models import TemplateExample

        example = TemplateExample.query.get_or_404(example_id)
        name = example.name

        db.session.delete(example)
        db.session.commit()

        flash(f"Template exemplar '{name}' excluído!", "success")

        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao excluir exemplo: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/template-examples/<int:example_id>/update", methods=["POST"])
@login_required
def update_template_example(example_id):
    """Atualizar dados de um template exemplar"""
    _require_admin()

    try:
        from app.models import TemplateExample

        example = TemplateExample.query.get_or_404(example_id)
        data = request.get_json() or {}

        if "quality_score" in data:
            score = float(data["quality_score"])
            example.quality_score = min(max(score, 1.0), 5.0)
        if "tags" in data:
            example.tags = str(data["tags"])[:500]  # Limitar tamanho
        if "description" in data:
            example.description = data["description"]
        if "is_active" in data:
            example.is_active = bool(data["is_active"])

        db.session.commit()

        return jsonify({"success": True, "message": "Template exemplar atualizado!"})
    except ValueError as e:
        return jsonify({"success": False, "error": "Valor inválido fornecido"}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao atualizar exemplo: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/audit-logs/entity/<entity_type>/<int:entity_id>")
@login_required
def audit_logs_entity(entity_type, entity_id):
    """Visualizar histórico completo de uma entidade específica"""
    _require_admin()

    logs = AuditManager.get_entity_history(entity_type, entity_id)

    # Buscar nome da entidade para exibição
    entity_name = f"{entity_type} #{entity_id}"
    if entity_type == "user":
        user = User.query.get(entity_id)
        if user:
            entity_name = f"Usuário: {user.email}"
    elif entity_type == "client":
        client = Client.query.get(entity_id)
        if client:
            entity_name = f"Cliente: {client.full_name}"

    return render_template(
        "admin/audit_logs_entity.html",
        title=f"Histórico: {entity_name}",
        logs=logs,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
    )


@bp.route("/system-diagnostics")
@login_required
@master_required
def system_diagnostics():
    """Diagnóstico do sistema - verifica dependências disponíveis"""
    import subprocess
    import sys

    diagnostics = {
        "python_version": sys.version,
        "platform": sys.platform,
        "conversions": {},
    }

    # Verificar Pillow (imagens)
    try:
        from PIL import Image

        diagnostics["conversions"]["images"] = {"available": True, "lib": "Pillow"}
    except ImportError:
        diagnostics["conversions"]["images"] = {"available": False}

    # Verificar ReportLab (PDF)
    try:
        from reportlab.pdfgen import canvas

        diagnostics["conversions"]["txt_to_pdf"] = {
            "available": True,
            "lib": "ReportLab",
        }
    except ImportError:
        diagnostics["conversions"]["txt_to_pdf"] = {"available": False}

    # Verificar python-docx
    try:
        from docx import Document

        diagnostics["conversions"]["docx"] = {"available": True, "lib": "python-docx"}
    except ImportError:
        diagnostics["conversions"]["docx"] = {"available": False}

    # Verificar LibreOffice
    libreoffice_paths = [
        "libreoffice",
        "soffice",
        "/usr/bin/libreoffice",
        "/usr/bin/soffice",
    ]
    libreoffice_found = False
    libreoffice_version = None

    for path in libreoffice_paths:
        try:
            result = subprocess.run(
                [path, "--version"], capture_output=True, timeout=5, text=True
            )
            if result.returncode == 0:
                libreoffice_found = True
                libreoffice_version = result.stdout.strip()
                break
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            continue

    diagnostics["conversions"]["office_files"] = {
        "available": libreoffice_found,
        "lib": "LibreOffice",
        "version": libreoffice_version,
        "note": "DOC, XLS, XLSX, PPT"
        if libreoffice_found
        else "Não disponível - DOC/XLS mantidos como original",
    }

    # Verificar PyPDF2
    try:
        import PyPDF2

        diagnostics["conversions"]["pdf_read"] = {"available": True, "lib": "PyPDF2"}
    except ImportError:
        diagnostics["conversions"]["pdf_read"] = {"available": False}

    return jsonify(diagnostics)


# =============================================================================
# GERENCIAMENTO DE CUPONS PROMOCIONAIS (Master Only)
# =============================================================================


@bp.route("/coupons")
@login_required
@master_required
def coupons_list():
    """Lista todos os cupons promocionais"""
    # Filtros
    status = request.args.get("status", "all")  # all, available, used, expired

    query = PromoCoupon.query

    if status == "available":
        query = query.filter_by(is_used=False).filter(
            (PromoCoupon.expires_at.is_(None))
            | (PromoCoupon.expires_at > datetime.now(timezone.utc))
        )
    elif status == "used":
        query = query.filter_by(is_used=True)
    elif status == "expired":
        query = query.filter_by(is_used=False).filter(
            PromoCoupon.expires_at <= datetime.now(timezone.utc)
        )

    coupons = query.order_by(PromoCoupon.created_at.desc()).all()

    # Estatísticas
    stats = {
        "total": PromoCoupon.query.count(),
        "available": PromoCoupon.query.filter_by(is_used=False)
        .filter(
            (PromoCoupon.expires_at.is_(None))
            | (PromoCoupon.expires_at > datetime.now(timezone.utc))
        )
        .count(),
        "used": PromoCoupon.query.filter_by(is_used=True).count(),
        "expired": PromoCoupon.query.filter_by(is_used=False)
        .filter(PromoCoupon.expires_at <= datetime.now(timezone.utc))
        .count(),
    }

    return render_template(
        "admin/coupons_list.html",
        coupons=coupons,
        stats=stats,
        current_status=status,
        now=datetime.now(timezone.utc),
    )


@bp.route("/coupons/create", methods=["GET", "POST"])
@login_required
@master_required
def coupons_create():
    """Cria um novo cupom promocional"""
    if request.method == "POST":
        try:
            # Sanitizar e validar inputs
            try:
                benefit_days = max(0, int(request.form.get("benefit_days", 0)))
                benefit_credits = max(0, int(request.form.get("benefit_credits", 0)))
            except (ValueError, TypeError):
                flash("Valores de dias ou créditos inválidos.", "danger")
                return redirect(url_for("admin.coupons_create"))

            # Sanitizar descrição (limitar tamanho e remover HTML)
            description = request.form.get("description", "").strip()[:255]
            # Remove tags HTML básicas
            import re

            description = re.sub(r"<[^>]+>", "", description)

            # Sanitizar código do cupom
            raw_code = request.form.get("custom_code", "").strip().upper()
            custom_code = sanitize_coupon_code(raw_code) if raw_code else None

            expires_at_str = request.form.get("expires_at", "")

            # Validar
            if benefit_days <= 0 and benefit_credits <= 0:
                flash(
                    "O cupom deve ter pelo menos dias de acesso ou créditos de IA.",
                    "warning",
                )
                return redirect(url_for("admin.coupons_create"))

            # Limitar valores máximos razoáveis
            if benefit_days > 365:
                flash("Dias de acesso não pode exceder 365.", "warning")
                return redirect(url_for("admin.coupons_create"))

            if benefit_credits > 1000:
                flash("Créditos de IA não pode exceder 1000.", "warning")
                return redirect(url_for("admin.coupons_create"))

            # Processar data de expiração
            expires_at = None
            if expires_at_str:
                try:
                    expires_at = datetime.strptime(expires_at_str, "%Y-%m-%d")
                    expires_at = expires_at.replace(
                        hour=23, minute=59, second=59, tzinfo=timezone.utc
                    )
                except ValueError:
                    flash("Data de expiração inválida.", "danger")
                    return redirect(url_for("admin.coupons_create"))

            # Criar cupom
            coupon = PromoCoupon.create_coupon(
                created_by_id=current_user.id,
                benefit_days=benefit_days,
                benefit_credits=benefit_credits,
                description=description,
                expires_at=expires_at,
                custom_code=custom_code,
            )

            flash(f"Cupom {coupon.code} criado com sucesso!", "success")
            return redirect(url_for("admin.coupons_list"))

        except Exception as e:
            flash(f"Erro ao criar cupom: {str(e)}", "danger")
            return redirect(url_for("admin.coupons_create"))

    return render_template("admin/coupons_create.html")


@bp.route("/coupons/<int:coupon_id>")
@login_required
@master_required
def coupons_detail(coupon_id):
    """Detalhes de um cupom"""
    coupon = PromoCoupon.query.get_or_404(coupon_id)
    return render_template(
        "admin/coupons_detail.html", coupon=coupon, now=datetime.now(timezone.utc)
    )


@bp.route("/coupons/<int:coupon_id>/delete", methods=["POST"])
@login_required
@master_required
def coupons_delete(coupon_id):
    """Deleta um cupom (apenas se não foi usado)"""
    coupon = PromoCoupon.query.get_or_404(coupon_id)

    if coupon.is_used:
        flash("Não é possível deletar um cupom já utilizado.", "warning")
        return redirect(url_for("admin.coupons_list"))

    code = coupon.code
    db.session.delete(coupon)
    db.session.commit()

    flash(f"Cupom {code} deletado com sucesso!", "success")
    return redirect(url_for("admin.coupons_list"))


def sanitize_coupon_code(code):
    """Sanitiza código de cupom - apenas letras maiúsculas, números e hífen"""
    import re

    if not code:
        return ""
    # Remove caracteres não permitidos e limita tamanho
    sanitized = re.sub(r"[^A-Z0-9\-]", "", code.upper())
    return sanitized[:20]


@bp.route("/api/coupons/validate", methods=["POST"])
@limiter.limit(COUPON_LIMIT)
@login_required
def api_validate_coupon():
    """API para validar um cupom (usado no checkout)"""
    data = request.get_json()

    if not data:
        return jsonify({"valid": False, "message": "Dados inválidos"}), 400

    raw_code = data.get("code", "")
    code = sanitize_coupon_code(raw_code)

    if not code:
        return jsonify(
            {"valid": False, "message": "Código não informado ou inválido"}
        ), 400

    if len(code) < 3:
        return jsonify({"valid": False, "message": "Código muito curto"}), 400

    coupon = PromoCoupon.query.filter_by(code=code).first()

    if not coupon:
        return jsonify({"valid": False, "message": "Cupom não encontrado"}), 404

    valid, message = coupon.is_valid()

    if valid:
        return jsonify(
            {
                "valid": True,
                "message": message,
                "benefit_days": int(coupon.benefit_days or 0),
                "benefit_credits": int(coupon.benefit_credits or 0),
            }
        )
    else:
        return jsonify({"valid": False, "message": message}), 400


@bp.route("/api/coupons/apply", methods=["POST"])
@limiter.limit(COUPON_LIMIT)
@login_required
def api_apply_coupon():
    """API para aplicar um cupom ao usuário atual"""
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "message": "Dados inválidos"}), 400

    raw_code = data.get("code", "")
    code = sanitize_coupon_code(raw_code)

    if not code:
        return jsonify(
            {"success": False, "message": "Código não informado ou inválido"}
        ), 400

    if len(code) < 3:
        return jsonify({"success": False, "message": "Código muito curto"}), 400

    coupon = PromoCoupon.query.filter_by(code=code).first()

    if not coupon:
        return jsonify({"success": False, "message": "Cupom não encontrado"}), 404

    success, message, details = coupon.apply_to_user(current_user)

    if success:
        return jsonify(
            {
                "success": True,
                "message": message,
                "benefit_days": int(details.get("days_added", 0)),
                "benefit_credits": int(details.get("credits_added", 0)),
                "new_trial_end": details.get("new_trial_end").isoformat()
                if details.get("new_trial_end")
                else None,
                "new_credit_balance": int(details.get("new_credit_balance", 0)),
            }
        )
    else:
        return jsonify({"success": False, "message": message}), 400


# =============================================================================
# CONFIGURAÇÃO DE CRÉDITOS DE IA
# =============================================================================


@bp.route("/ai-config")
@login_required
@master_required
def ai_config():
    """Tela de configuração de custos de créditos de IA"""
    # Garantir que as configs padrão existam
    AICreditConfig.seed_defaults()
    
    configs = AICreditConfig.query.order_by(AICreditConfig.sort_order).all()
    
    # Estatísticas de uso
    total_generations = AIGeneration.query.count()
    total_credits_used = db.session.query(func.sum(AIGeneration.credits_used)).scalar() or 0
    
    # Uso por operação
    usage_by_type = db.session.query(
        AIGeneration.generation_type,
        func.count(AIGeneration.id).label('count'),
        func.sum(AIGeneration.credits_used).label('credits')
    ).group_by(AIGeneration.generation_type).all()
    
    usage_stats = {row.generation_type: {'count': row.count, 'credits': row.credits or 0} for row in usage_by_type}
    
    return render_template(
        "admin/ai_config.html",
        configs=configs,
        total_generations=total_generations,
        total_credits_used=int(total_credits_used),
        usage_stats=usage_stats,
    )


@bp.route("/ai-config/<int:config_id>/update", methods=["POST"])
@login_required
@master_required
def ai_config_update(config_id):
    """Atualiza uma configuração de custo de IA"""
    config = AICreditConfig.query.get_or_404(config_id)
    
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Dados inválidos"}), 400
    
    # Atualizar campos
    if "credit_cost" in data:
        credit_cost = int(data["credit_cost"])
        if credit_cost < 0 or credit_cost > 100:
            return jsonify({"success": False, "message": "Custo deve ser entre 0 e 100"}), 400
        config.credit_cost = credit_cost
    
    if "is_premium" in data:
        config.is_premium = bool(data["is_premium"])
    
    if "is_active" in data:
        config.is_active = bool(data["is_active"])
    
    if "name" in data:
        config.name = str(data["name"])[:100]
    
    if "description" in data:
        config.description = str(data["description"])[:500]
    
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Configuração atualizada!",
        "config": {
            "id": config.id,
            "operation_key": config.operation_key,
            "name": config.name,
            "credit_cost": config.credit_cost,
            "is_premium": config.is_premium,
            "is_active": config.is_active,
        }
    })


@bp.route("/ai-config/reset", methods=["POST"])
@login_required
@master_required
def ai_config_reset():
    """Reseta todas as configurações para os valores padrão"""
    for default in AICreditConfig.DEFAULT_CONFIGS:
        config = AICreditConfig.query.filter_by(operation_key=default["operation_key"]).first()
        if config:
            config.credit_cost = default["credit_cost"]
            config.is_premium = default["is_premium"]
            config.is_active = True
            config.name = default["name"]
            config.description = default["description"]
    
    db.session.commit()
    flash("Configurações resetadas para os valores padrão!", "success")
    return redirect(url_for("admin.ai_config"))

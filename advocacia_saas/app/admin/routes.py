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

from app import db
from app.admin import bp
from app.models import (
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
    PetitionTypeSection,
    PetitionUsage,
    RoadmapCategory,
    RoadmapFeedback,
    RoadmapItem,
    SavedPetition,
    User,
    UserCredits,
    UserPlan,
)
from app.utils.audit import AuditManager

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
def users_list():
    """Lista todos os usuários com métricas detalhadas"""
    try:
        admin_logger.info(f"Admin {current_user.email} acessando lista de usuários")

        _require_admin()

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

        # Query base
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
        flash("Erro ao carregar lista de usuários. Tente novamente.", "danger")
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

    # === DADOS PARA GRÁFICOS - Últimos 12 meses ===
    chart_labels = []
    chart_revenue = []  # Faturamento geral
    chart_revenue_by_plan = {}  # Faturamento por plano
    chart_ai_usage = []  # Uso de IA (gerações)
    chart_ai_cost = []  # Custo de IA
    chart_ai_credits_sold = []  # Créditos vendidos

    # Buscar planos existentes
    all_plans = BillingPlan.query.filter(BillingPlan.active.is_(True)).all()
    for plan in all_plans:
        chart_revenue_by_plan[plan.name] = []
    chart_revenue_by_plan["Avulso"] = []  # Para pagamentos avulsos/créditos

    # Iterar últimos 12 meses
    for i in range(11, -1, -1):
        # Calcular início e fim do mês
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

        # Label do mês
        chart_labels.append(month_start.strftime("%b/%y"))

        # Faturamento geral do mês
        month_revenue = (
            db.session.query(func.coalesce(func.sum(Payment.amount), 0))
            .filter(
                Payment.paid_at >= month_start,
                Payment.paid_at < month_end,
                Payment.payment_status == "completed",
            )
            .scalar()
            or 0
        )
        chart_revenue.append(float(month_revenue))

        # Faturamento por plano (via user -> current plan)
        for plan in all_plans:
            plan_revenue = (
                db.session.query(func.coalesce(func.sum(Payment.amount), 0))
                .join(User, Payment.user_id == User.id)
                .join(
                    UserPlan,
                    and_(UserPlan.user_id == User.id, UserPlan.is_current.is_(True)),
                )
                .filter(
                    Payment.paid_at >= month_start,
                    Payment.paid_at < month_end,
                    Payment.payment_status == "completed",
                    UserPlan.plan_id == plan.id,
                )
                .scalar()
                or 0
            )
            chart_revenue_by_plan[plan.name].append(float(plan_revenue))

        # Faturamento avulso (créditos IA) - via CreditPackage.price
        credits_revenue = (
            db.session.query(func.coalesce(func.sum(CreditPackage.price), 0))
            .join(CreditTransaction, CreditTransaction.package_id == CreditPackage.id)
            .filter(
                CreditTransaction.created_at >= month_start,
                CreditTransaction.created_at < month_end,
                CreditTransaction.transaction_type == "purchase",
            )
            .scalar()
            or 0
        )
        chart_revenue_by_plan["Avulso"].append(float(credits_revenue))

        # Uso de IA no mês
        ai_gens = AIGeneration.query.filter(
            AIGeneration.created_at >= month_start, AIGeneration.created_at < month_end
        ).count()
        chart_ai_usage.append(ai_gens)

        # Custo de IA no mês
        ai_cost = (
            db.session.query(func.coalesce(func.sum(AIGeneration.cost_usd), 0))
            .filter(
                AIGeneration.created_at >= month_start,
                AIGeneration.created_at < month_end,
            )
            .scalar()
            or 0
        )
        chart_ai_cost.append(float(ai_cost))

        # Créditos vendidos no mês
        credits = (
            db.session.query(func.coalesce(func.sum(CreditTransaction.amount), 0))
            .filter(
                CreditTransaction.created_at >= month_start,
                CreditTransaction.created_at < month_end,
                CreditTransaction.transaction_type == "purchase",
            )
            .scalar()
            or 0
        )
        chart_ai_credits_sold.append(int(credits))

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
        .filter(User.created_at >= func.date_trunc("month", func.now()))
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
        .filter(PetitionUsage.billable == True)
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

        metrics = {
            "days_on_platform": (
                now
                - (
                    user.created_at.replace(tzinfo=timezone.utc)
                    if user.created_at and user.created_at.tzinfo is None
                    else user.created_at
                )
            ).days
            if user.created_at
            else 0,
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
def petition_sections_list():
    """Lista todas as seções de petição"""
    current_app.logger.info("🔍 [SECTIONS] Iniciando petition_sections_list")
    _require_admin()
    current_app.logger.info("✅ [SECTIONS] Usuário admin autenticado")

    try:
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
        raise


@bp.route("/petitions/sections/new", methods=["GET", "POST"])
@login_required
def petition_section_new():
    """Cria uma nova seção de petição"""
    current_app.logger.info("🔍 [SECTIONS] Iniciando petition_section_new")
    _require_admin()
    current_app.logger.info("✅ [SECTIONS] Usuário admin autenticado")

    if request.method == "POST":
        current_app.logger.info("📝 [SECTIONS] Processando POST para nova seção")

        name = request.form.get("name")
        slug = request.form.get(
            "slug"
        )  # Slug será gerado automaticamente, mas mantemos para compatibilidade
        description = request.form.get("description")
        icon = request.form.get("icon", "fa-file-alt")
        color = request.form.get("color", "primary")
        order = int(request.form.get("order", 0))
        is_active = "is_active" in request.form
        fields_schema_raw = request.form.get("fields_schema", "[]")

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
            name = request.form.get("name")
            description = request.form.get("description")
            icon = request.form.get("icon", "fa-file-alt")
            color = request.form.get("color", "primary")
            order = int(request.form.get("order", 0))
            is_active = "is_active" in request.form

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
            fields_schema_raw = request.form.get("fields_schema", "[]")
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
        # Verificar se a seção está sendo usada
        usage_count = section.type_sections.count()
        current_app.logger.info(
            f"🔍 [SECTIONS] Verificando uso da seção - Usada em {usage_count} tipos de petição"
        )

        if usage_count > 0:
            current_app.logger.warning(
                f"⚠️ [SECTIONS] Tentativa de excluir seção em uso - ID: {section_id}, Usos: {usage_count}"
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

        # Atualizar configurações para cada seção
        for i, section_id in enumerate(section_ids):
            type_section = PetitionTypeSection.query.filter_by(
                petition_type_id=type_id, section_id=int(section_id)
            ).first()

            if type_section:
                type_section.order = (
                    int(section_orders[i])
                    if i < len(section_orders)
                    else type_section.order
                )
                type_section.is_required = str(section_id) in section_required
                type_section.is_expanded = str(section_id) in section_expanded

        db.session.commit()
        flash("Configurações das seções salvas com sucesso!", "success")
        return redirect(url_for("admin.petition_type_sections", type_id=type_id))

    # GET: mostrar página
    all_sections = (
        PetitionSection.query.filter_by(is_active=True)
        .order_by(PetitionSection.order)
        .all()
    )

    # Buscar seções já configuradas para este tipo
    configured_sections = []
    type_sections = (
        PetitionTypeSection.query.filter_by(petition_type_id=type_id)
        .order_by(PetitionTypeSection.order)
        .all()
    )

    for type_section in type_sections:
        configured_sections.append((type_section, type_section.section))

    # Seções disponíveis (não configuradas ainda)
    configured_ids = [ts.section_id for ts in type_sections]
    available_sections = [s for s in all_sections if s.id not in configured_ids]

    return render_template(
        "admin/petition_type_sections.html",
        title=f"Seções - {petition_type.name}",
        petition_type=petition_type,
        configured_sections=configured_sections,
        available_sections=available_sections,
    )


@bp.route("/petitions/types/<int:type_id>/sections/add", methods=["POST"])
@login_required
def petition_type_section_add(type_id):
    """Adiciona uma seção a um tipo de petição"""
    _require_admin()

    petition_type = PetitionType.query.get_or_404(type_id)
    section_id = request.form.get("section_id", type=int)

    if section_id:
        section = PetitionSection.query.get_or_404(section_id)

        # Verificar se já existe
        existing = PetitionTypeSection.query.filter_by(
            petition_type_id=type_id, section_id=section_id
        ).first()

        if not existing:
            # Pegar a maior ordem atual
            max_order = (
                db.session.query(db.func.max(PetitionTypeSection.order))
                .filter_by(petition_type_id=type_id)
                .scalar()
                or 0
            )

            type_section = PetitionTypeSection(
                petition_type_id=type_id,
                section_id=section_id,
                order=max_order + 1,
            )

            db.session.add(type_section)
            db.session.commit()

            flash(f"Seção '{section.name}' adicionada com sucesso!", "success")

    return redirect(url_for("admin.petition_type_sections", type_id=type_id))


@bp.route(
    "/petitions/types/<int:type_id>/sections/<int:section_id>/remove", methods=["POST"]
)
@login_required
def petition_type_section_remove(type_id, section_id):
    """Remove uma seção de um tipo de petição"""
    _require_admin()

    type_section = PetitionTypeSection.query.filter_by(
        petition_type_id=type_id, section_id=section_id
    ).first_or_404()

    db.session.delete(type_section)
    db.session.commit()

    flash("Seção removida com sucesso!", "success")
    return redirect(url_for("admin.petition_type_sections", type_id=type_id))


@bp.route("/petitions/types")
@login_required
def petition_types_list():
    """Lista todos os tipos de petição"""
    _require_admin()

    petition_types = PetitionType.query.order_by(PetitionType.name).all()

    return render_template(
        "admin/petition_types_list.html",
        title="Tipos de Petição",
        petition_types=petition_types,
    )


@bp.route("/petitions/types/new", methods=["GET", "POST"])
@login_required
def petition_type_new():
    """Criar novo tipo de petição"""
    _require_admin()

    if request.method == "POST":
        name = request.form.get("name")
        slug = request.form.get(
            "slug"
        )  # Slug será gerado automaticamente, mas mantemos para compatibilidade
        description = request.form.get("description")
        category = request.form.get("category", "civel")
        icon = request.form.get("icon", "fa-file-alt")
        color = request.form.get("color", "primary")
        is_billable = request.form.get("is_billable") == "on"
        base_price = request.form.get("base_price", "0.00")
        use_dynamic_form = request.form.get("use_dynamic_form") == "on"

        # Gerar slug único baseado no nome
        slug = generate_unique_slug(name, PetitionType)

        petition_type = PetitionType(
            name=name,
            slug=slug,
            description=description,
            category=category,
            icon=icon,
            color=color,
            is_billable=is_billable,
            base_price=Decimal(base_price),
            use_dynamic_form=use_dynamic_form,
        )

        db.session.add(petition_type)
        db.session.commit()

        flash(f"Tipo de petição '{name}' criado com sucesso!", "success")
        return redirect(url_for("admin.petition_types_list"))

    return render_template(
        "admin/petition_type_form.html", title="Novo Tipo de Petição"
    )


@bp.route("/petitions/types/<int:type_id>/edit", methods=["GET", "POST"])
@login_required
def petition_type_edit(type_id):
    """Editar tipo de petição"""
    _require_admin()

    petition_type = PetitionType.query.get_or_404(type_id)

    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        category = request.form.get("category", "civel")
        icon = request.form.get("icon", "fa-file-alt")
        color = request.form.get("color", "primary")
        is_billable = request.form.get("is_billable") == "on"
        base_price = Decimal(request.form.get("base_price", "0.00"))
        use_dynamic_form = request.form.get("use_dynamic_form") == "on"
        is_active = request.form.get("is_active") == "on"

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
            "trend": "Crescendo"
            if revenue_change > 5
            else "Caíndo"
            if revenue_change < -5
            else "Estável",
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
            "trend": "Crescendo"
            if users_change > 10
            else "Caíndo"
            if users_change < -10
            else "Estável",
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
            "direction": "up"
            if petitions_change > 0
            else "down"
            if petitions_change < 0
            else "stable",
            "trend": "Crescendo"
            if petitions_change > 5
            else "Caíndo"
            if petitions_change < -5
            else "Estável",
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
def new_roadmap_category():
    """Criar nova categoria do roadmap"""
    _require_admin()

    if request.method == "POST":
        name = request.form.get("name")
        slug = request.form.get("slug")
        description = request.form.get("description")
        icon = request.form.get("icon", "fa-lightbulb")
        color = request.form.get("color", "primary")
        order = int(request.form.get("order", 0))

        # Verificar se slug já existe
        if RoadmapCategory.query.filter_by(slug=slug).first():
            flash("Slug já existe. Escolha outro.", "error")
            return redirect(request.url)

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

    return render_template("admin/roadmap_category_form.html", title="Nova Categoria")


@bp.route("/roadmap/categories/<int:category_id>/edit", methods=["GET", "POST"])
@login_required
def edit_roadmap_category(category_id):
    """Editar categoria do roadmap"""
    _require_admin()

    category = RoadmapCategory.query.get_or_404(category_id)

    if request.method == "POST":
        category.name = request.form.get("name")
        category.slug = request.form.get("slug")
        category.description = request.form.get("description")
        category.icon = request.form.get("icon", "fa-lightbulb")
        category.color = request.form.get("color", "primary")
        category.order = int(request.form.get("order", 0))

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

    return render_template(
        "admin/roadmap_category_form.html",
        title="Editar Categoria",
        category=category,
    )


@bp.route("/roadmap/categories/<int:category_id>/delete", methods=["POST"])
@login_required
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
def roadmap_items():
    """Listar todos os itens do roadmap"""
    _require_admin()

    # Filtros
    status_filter = request.args.get("status")
    category_filter = request.args.get("category")
    visibility_filter = request.args.get("visibility")  # public, internal, all
    priority_filter = request.args.get("priority")

    query = RoadmapItem.query.join(RoadmapCategory)

    if status_filter:
        query = query.filter(RoadmapItem.status == status_filter)

    if category_filter:
        query = query.filter(RoadmapItem.category_id == category_filter)

    if visibility_filter == "public":
        query = query.filter(RoadmapItem.visible_to_users == True)
    elif visibility_filter == "internal":
        query = query.filter(RoadmapItem.internal_only == True)

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
def new_roadmap_item():
    """Criar novo item do roadmap"""
    _require_admin()

    categories = RoadmapCategory.query.filter_by(is_active=True).all()
    users = User.query.filter(User.user_type.in_(["master", "admin"])).all()

    if request.method == "POST":
        category_id = request.form.get("category_id")
        title = request.form.get("title")
        slug = request.form.get("slug")
        description = request.form.get("description")
        detailed_description = request.form.get("detailed_description")

        # Status e prioridade
        status = request.form.get("status", "planned")
        priority = request.form.get("priority", "medium")
        estimated_effort = request.form.get("estimated_effort", "medium")

        # Visibilidade
        visible_to_users = "visible_to_users" in request.form
        internal_only = "internal_only" in request.form
        show_new_badge = "show_new_badge" in request.form

        # Datas
        planned_start_date = (
            datetime.strptime(request.form.get("planned_start_date"), "%Y-%m-%d").date()
            if request.form.get("planned_start_date")
            else None
        )
        planned_completion_date = (
            datetime.strptime(
                request.form.get("planned_completion_date"), "%Y-%m-%d"
            ).date()
            if request.form.get("planned_completion_date")
            else None
        )

        # Detalhes
        business_value = request.form.get("business_value")
        technical_complexity = request.form.get("technical_complexity", "medium")
        user_impact = request.form.get("user_impact", "medium")

        dependencies = request.form.get("dependencies")
        blockers = request.form.get("blockers")
        tags = request.form.get("tags")
        notes = request.form.get("notes")

        assigned_to = request.form.get("assigned_to")
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

    return render_template(
        "admin/roadmap_item_form.html",
        title="Novo Item do Roadmap",
        categories=categories,
        users=users,
    )


@bp.route("/roadmap/items/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def edit_roadmap_item(item_id):
    """Editar item do roadmap"""
    _require_admin()

    item = RoadmapItem.query.get_or_404(item_id)
    categories = RoadmapCategory.query.filter_by(is_active=True).all()
    users = User.query.filter(User.user_type.in_(["master", "admin"])).all()

    if request.method == "POST":
        item.category_id = request.form.get("category_id")
        item.title = request.form.get("title")
        item.slug = request.form.get("slug")
        item.description = request.form.get("description")
        item.detailed_description = request.form.get("detailed_description")

        # Status e prioridade
        item.status = request.form.get("status", "planned")
        item.priority = request.form.get("priority", "medium")
        item.estimated_effort = request.form.get("estimated_effort", "medium")

        # Visibilidade
        item.visible_to_users = "visible_to_users" in request.form
        item.internal_only = "internal_only" in request.form
        item.show_new_badge = "show_new_badge" in request.form

        # Datas
        item.planned_start_date = (
            datetime.strptime(request.form.get("planned_start_date"), "%Y-%m-%d").date()
            if request.form.get("planned_start_date")
            else None
        )
        item.planned_completion_date = (
            datetime.strptime(
                request.form.get("planned_completion_date"), "%Y-%m-%d"
            ).date()
            if request.form.get("planned_completion_date")
            else None
        )

        # Atualizar datas reais se status mudou
        if item.status == "in_progress" and not item.actual_start_date:
            item.actual_start_date = datetime.now(timezone.utc).date()
        elif item.status == "completed" and not item.actual_completion_date:
            item.actual_completion_date = datetime.now(timezone.utc).date()

        # Detalhes
        item.business_value = request.form.get("business_value")
        item.technical_complexity = request.form.get("technical_complexity", "medium")
        item.user_impact = request.form.get("user_impact", "medium")

        item.dependencies = request.form.get("dependencies")
        item.blockers = request.form.get("blockers")
        item.tags = request.form.get("tags")
        item.notes = request.form.get("notes")

        assigned_to = request.form.get("assigned_to")
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
        flash("Item do roadmap atualizado com sucesso!", "success")
        return redirect(url_for("admin.roadmap_items"))

    return render_template(
        "admin/roadmap_item_form.html",
        title="Editar Item do Roadmap",
        item=item,
        categories=categories,
        users=users,
    )


@bp.route("/roadmap/items/<int:item_id>/delete", methods=["POST"])
@login_required
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
# PETITION MODELS MANAGEMENT
# ==========================================


@bp.route("/petitions/models")
@login_required
def petition_models_list():
    """Lista todos os modelos de petição"""
    current_app.logger.info("Acessando lista de modelos de petição")
    _require_admin()

    petition_models = PetitionModel.query.order_by(PetitionModel.name).all()
    current_app.logger.info(f"Encontrados {len(petition_models)} modelos de petição")

    return render_template(
        "admin/petition_models_list.html",
        title="Modelos de Petição",
        petition_models=petition_models,
    )


@bp.route("/petitions/models/new", methods=["GET", "POST"])
@login_required
def petition_model_new():
    """Criar novo modelo de petição"""
    current_app.logger.info("Acessando criação de novo modelo de petição")
    _require_admin()

    petition_types = PetitionType.query.order_by(PetitionType.name).all()
    sections = PetitionSection.query.order_by(PetitionSection.name).all()
    current_app.logger.info(f"Encontrados {len(petition_types)} tipos de petição")

    if request.method == "POST":
        current_app.logger.info("Processando POST para criar modelo")
        name = request.form.get("name")
        description = request.form.get("description")
        petition_type_id = request.form.get("petition_type_id")
        is_active = request.form.get("is_active") == "on"
        use_dynamic_form = request.form.get("use_dynamic_form") == "on"
        template_content = request.form.get("template_content")

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
def petition_model_edit(model_id):
    """Editar modelo de petição"""
    _require_admin()

    petition_model = PetitionModel.query.get_or_404(model_id)
    petition_types = PetitionType.query.order_by(PetitionType.name).all()
    sections = PetitionSection.query.order_by(PetitionSection.name).all()

    current_app.logger.info(
        f"Carregando página de edição do modelo {model_id}: {petition_model.name if petition_model else 'None'}"
    )

    if request.method == "POST":
        petition_model.description = request.form.get("description")
        petition_model.petition_type_id = request.form.get("petition_type_id")
        petition_model.is_active = request.form.get("is_active") == "on"
        petition_model.use_dynamic_form = request.form.get("use_dynamic_form") == "on"
        petition_model.template_content = request.form.get("template_content")

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

            # Remover todas as seções atuais
            petition_model.model_sections.delete()

            # Adicionar seções na nova ordem
            for order, section_id in enumerate(section_ids, 1):
                section = PetitionSection.query.get(section_id)
                if section:
                    model_section = PetitionModelSection(
                        petition_model=petition_model, section=section, order=order
                    )
                    db.session.add(model_section)

        db.session.commit()

        flash("Modelo de petição atualizado com sucesso!", "success")
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


@bp.route("/petitions/models/<int:model_id>/generate_template", methods=["POST"])
@login_required
def petition_model_generate_template(model_id):
    """Gerar template Jinja2 baseado nas seções do modelo"""
    _require_admin()

    petition_model = PetitionModel.query.get_or_404(model_id)

    try:
        # Obter seções ordenadas
        sections = petition_model.get_sections_ordered()

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
        for model_section in sections:
            section = model_section.section
            if section:
                section_name = section.name.upper()
                template_parts.append(f"{{{{ {section_name} }}}}")
                template_parts.append("")

        # Rodapé
        template_parts.append("{{ local }}, {{ data }}")
        template_parts.append("")
        template_parts.append("{{ advogado_nome }}")
        template_parts.append("{{ advogado_oab }}")

        template_content = "\n".join(template_parts)

        return jsonify({"success": True, "template": template_content})

    except Exception as e:
        current_app.logger.error(f"Erro ao gerar template: {str(e)}")
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

    return render_template(
        "admin/audit_logs.html",
        title="Logs de Auditoria",
        logs=logs,
        total_logs=total_logs,
        today_logs=today_logs,
        entity_types=entity_types,
        actions=actions,
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

"""
Rotas de Administração de Usuários
Dashboard completo para gerenciar usuários e métricas da plataforma.
"""

from datetime import datetime, timedelta
from decimal import Decimal

from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import and_, case, func
from sqlalchemy.orm import joinedload

from app import db
from app.admin import bp
from app.models import (
    AIGeneration,
    BillingPlan,
    Client,
    CreditPackage,
    CreditTransaction,
    Invoice,
    Payment,
    PetitionUsage,
    User,
    UserCredits,
    UserPlan,
)


def _require_admin():
    """Verifica se o usuário é admin (master)"""
    if not current_user.is_authenticated or current_user.user_type != "master":
        abort(403)


@bp.route("/usuarios")
@login_required
def users_list():
    """Lista todos os usuários com métricas detalhadas"""
    _require_admin()

    # Parâmetros de filtro e ordenação
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "all")
    user_type_filter = request.args.get("user_type", "all")
    sort_by = request.args.get("sort", "created_at")
    sort_order = request.args.get("order", "desc")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

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
        query = query.filter(User.is_active == True)
    elif status_filter == "inactive":
        query = query.filter(User.is_active == False)
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

    return render_template(
        "admin/users_list.html",
        title="Gerenciar Usuários",
        users_data=users_with_metrics,
        pagination=pagination,
        search=search,
        status_filter=status_filter,
        user_type_filter=user_type_filter,
        sort_by=sort_by,
        sort_order=sort_order,
    )


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

    if user.user_type == "master":
        flash("Não é possível desativar um usuário master.", "danger")
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


@bp.route("/dashboard")
@login_required
def dashboard():
    """Dashboard administrativo com visão geral da plataforma"""
    _require_admin()

    # Período atual
    now = datetime.utcnow()
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
    all_plans = BillingPlan.query.filter(BillingPlan.active == True).all()
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
                    and_(UserPlan.user_id == User.id, UserPlan.is_current == True),
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
        User.is_active == True, User.user_type != "master"
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
        .filter(UserPlan.status == "active", UserPlan.is_current == True)
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
    now = datetime.utcnow()
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # 1. Contagem de clientes (usa lawyer_id)
    clients_count = dict(
        db.session.query(
            Client.lawyer_id,
            func.count(Client.id)
        )
        .filter(Client.lawyer_id.in_(user_ids))
        .group_by(Client.lawyer_id)
        .all()
    )
    
    # 2. Petições totais e mensais
    petitions_total = dict(
        db.session.query(
            PetitionUsage.user_id,
            func.count(PetitionUsage.id)
        )
        .filter(PetitionUsage.user_id.in_(user_ids))
        .group_by(PetitionUsage.user_id)
        .all()
    )
    
    petitions_month = dict(
        db.session.query(
            PetitionUsage.user_id,
            func.count(PetitionUsage.id)
        )
        .filter(
            PetitionUsage.user_id.in_(user_ids),
            PetitionUsage.generated_at >= current_month_start
        )
        .group_by(PetitionUsage.user_id)
        .all()
    )
    
    # 3. Valor total de petições
    petitions_value = dict(
        db.session.query(
            PetitionUsage.user_id,
            func.coalesce(func.sum(PetitionUsage.amount), 0)
        )
        .filter(PetitionUsage.user_id.in_(user_ids))
        .group_by(PetitionUsage.user_id)
        .all()
    )
    
    # 4. Créditos de IA
    credits_data = dict(
        db.session.query(
            UserCredits.user_id,
            UserCredits.balance,
            UserCredits.total_used
        )
        .filter(UserCredits.user_id.in_(user_ids))
        .all()
    )
    
    # 5. Gerações de IA totais e mensais
    ai_total = dict(
        db.session.query(
            AIGeneration.user_id,
            func.count(AIGeneration.id)
        )
        .filter(AIGeneration.user_id.in_(user_ids))
        .group_by(AIGeneration.user_id)
        .all()
    )
    
    ai_month = dict(
        db.session.query(
            AIGeneration.user_id,
            func.count(AIGeneration.id)
        )
        .filter(
            AIGeneration.user_id.in_(user_ids),
            AIGeneration.created_at >= current_month_start
        )
        .group_by(AIGeneration.user_id)
        .all()
    )
    
    # 6. Tokens e custo de IA
    ai_stats = dict(
        db.session.query(
            AIGeneration.user_id,
            func.coalesce(func.sum(AIGeneration.tokens_total), 0),
            func.coalesce(func.sum(AIGeneration.cost_usd), 0)
        )
        .filter(AIGeneration.user_id.in_(user_ids))
        .group_by(AIGeneration.user_id)
        .all()
    )
    
    # 7. Plano atual
    current_plans = {}
    plans_query = (
        db.session.query(UserPlan, BillingPlan)
        .join(BillingPlan)
        .filter(
            UserPlan.user_id.in_(user_ids),
            UserPlan.is_current == True
        )
        .all()
    )
    for user_plan, billing_plan in plans_query:
        current_plans[user_plan.user_id] = billing_plan.name
    
    # 8. Total pago
    total_paid = dict(
        db.session.query(
            Payment.user_id,
            func.coalesce(func.sum(Payment.amount), 0)
        )
        .filter(
            Payment.user_id.in_(user_ids),
            Payment.payment_status == 'completed'
        )
        .group_by(Payment.user_id)
        .all()
    )
    
    # 9. Primeiro pagamento (para calcular days_paying)
    first_payments = {}
    payments_query = (
        db.session.query(
            Payment.user_id,
            func.min(Payment.paid_at)
        )
        .filter(
            Payment.user_id.in_(user_ids),
            Payment.payment_status == 'completed',
            Payment.paid_at.isnot(None)
        )
        .group_by(Payment.user_id)
        .all()
    )
    for user_id, first_paid_at in payments_query:
        if first_paid_at:
            first_payments[user_id] = (now - first_paid_at).days
    
    # Montar resultado
    results = []
    for user in users:
        uid = user.id
        credits = credits_data.get(uid, (0, 0))
        ai_stat = ai_stats.get(uid, (0, Decimal('0.00')))
        
        metrics = {
            'days_on_platform': (now - user.created_at).days if user.created_at else 0,
            'days_paying': first_payments.get(uid, 0),
            'plan_name': current_plans.get(uid, 'Sem plano'),
            'clients_count': clients_count.get(uid, 0),
            'petitions_total': petitions_total.get(uid, 0),
            'petitions_month': petitions_month.get(uid, 0),
            'petitions_value': float(petitions_value.get(uid, Decimal('0.00'))),
            'ai_credits_balance': credits[0] if isinstance(credits, tuple) else 0,
            'ai_credits_used': credits[1] if isinstance(credits, tuple) else 0,
            'ai_generations_total': ai_total.get(uid, 0),
            'ai_generations_month': ai_month.get(uid, 0),
            'ai_tokens_total': ai_stat[0] if len(ai_stat) > 0 else 0,
            'ai_cost_total': float(ai_stat[1]) if len(ai_stat) > 1 else 0.0,
            'total_paid': float(total_paid.get(uid, Decimal('0.00')))
        }
        
        results.append({'user': user, 'metrics': metrics})
    
    return results


def _get_user_metrics(user, detailed=False):
    """Calcula métricas de um usuário"""
    now = datetime.utcnow()
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Dias na plataforma
    days_on_platform = (now - user.created_at).days if user.created_at else 0

    # Clientes (Client usa lawyer_id, não user_id)
    clients_count = Client.query.filter_by(lawyer_id=user.id).count()

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

    ai_tokens_total = ai_stats.tokens if ai_stats else 0
    ai_cost_total = ai_stats.cost if ai_stats else Decimal("0.00")

    # Plano atual
    current_plan = UserPlan.query.filter_by(user_id=user.id, is_current=True).first()
    plan_name = (
        current_plan.plan.name if current_plan and current_plan.plan else "Sem plano"
    )

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
        days_paying = (now - first_payment.paid_at).days

    # Total pago
    total_paid = db.session.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
        Payment.user_id == user.id, Payment.payment_status == "completed"
    ).scalar() or Decimal("0.00")

    metrics = {
        "days_on_platform": days_on_platform,
        "days_paying": days_paying,
        "plan_name": plan_name,
        "clients_count": clients_count,
        "petitions_total": petitions_total,
        "petitions_month": petitions_month,
        "petitions_value": float(petitions_value),
        "ai_credits_balance": ai_credits_balance,
        "ai_credits_used": ai_credits_used,
        "ai_generations_total": ai_generations_total,
        "ai_generations_month": ai_generations_month,
        "ai_tokens_total": ai_tokens_total,
        "ai_cost_total": float(ai_cost_total),
        "total_paid": float(total_paid),
    }

    return metrics

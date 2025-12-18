"""
Rotas de Administração de Usuários
Dashboard completo para gerenciar usuários e métricas da plataforma.
"""

from datetime import datetime, timedelta
from decimal import Decimal

from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, case, and_
from sqlalchemy.orm import joinedload

from app import db
from app.admin import bp
from app.models import (
    User,
    Client,
    PetitionUsage,
    UserPlan,
    BillingPlan,
    Payment,
    Invoice,
    UserCredits,
    AIGeneration,
    CreditTransaction,
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
    if sort_by == "created_at":
        order_col = User.created_at
    elif sort_by == "username":
        order_col = User.username
    elif sort_by == "email":
        order_col = User.email
    elif sort_by == "full_name":
        order_col = User.full_name
    else:
        order_col = User.created_at
    
    if sort_order == "asc":
        query = query.order_by(order_col.asc())
    else:
        query = query.order_by(order_col.desc())
    
    # Paginação
    users_paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Calcular métricas para cada usuário
    users_data = []
    for user in users_paginated.items:
        user_data = _get_user_metrics(user)
        users_data.append(user_data)
    
    # Métricas gerais da plataforma
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    paying_users = User.query.join(UserPlan).filter(UserPlan.status == "active").distinct().count()
    
    # Métricas do mês atual
    current_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_users_month = User.query.filter(User.created_at >= current_month_start).count()
    
    return render_template(
        "admin/users_list.html",
        title="Administração de Usuários",
        users=users_data,
        pagination=users_paginated,
        search=search,
        status_filter=status_filter,
        user_type_filter=user_type_filter,
        sort_by=sort_by,
        sort_order=sort_order,
        total_users=total_users,
        active_users=active_users,
        paying_users=paying_users,
        new_users_month=new_users_month,
    )


@bp.route("/usuarios/<int:user_id>")
@login_required
def user_detail(user_id):
    """Detalhes completos de um usuário específico"""
    _require_admin()
    
    user = User.query.get_or_404(user_id)
    metrics = _get_user_metrics(user, detailed=True)
    
    # Histórico de petições (últimas 20)
    petitions = (
        PetitionUsage.query
        .filter_by(user_id=user.id)
        .order_by(PetitionUsage.generated_at.desc())
        .limit(20)
        .all()
    )
    
    # Histórico de pagamentos (últimos 10)
    payments = (
        Payment.query
        .filter_by(user_id=user.id)
        .order_by(Payment.paid_at.desc())
        .limit(10)
        .all()
    )
    
    # Histórico de uso de IA (últimos 20)
    ai_generations = (
        AIGeneration.query
        .filter_by(user_id=user.id)
        .order_by(AIGeneration.created_at.desc())
        .limit(20)
        .all()
    )
    
    # Transações de créditos (últimas 20)
    credit_transactions = (
        CreditTransaction.query
        .filter_by(user_id=user.id)
        .order_by(CreditTransaction.created_at.desc())
        .limit(20)
        .all()
    )
    
    return render_template(
        "admin/user_detail.html",
        title=f"Usuário: {user.full_name or user.username}",
        user=user,
        metrics=metrics,
        petitions=petitions,
        payments=payments,
        ai_generations=ai_generations,
        credit_transactions=credit_transactions,
    )


@bp.route("/usuarios/<int:user_id>/toggle-status", methods=["POST"])
@login_required
def toggle_user_status(user_id):
    """Ativa/Desativa um usuário"""
    _require_admin()
    
    user = User.query.get_or_404(user_id)
    
    # Não pode desativar a si mesmo
    if user.id == current_user.id:
        flash("Você não pode desativar sua própria conta.", "danger")
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
    
    flash(f"{amount} créditos adicionados para {user.username}. Novo saldo: {new_balance}", "success")
    
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
    
    # === Métricas de Usuários ===
    total_users = User.query.filter(User.user_type != "master").count()
    active_users = User.query.filter(User.is_active == True, User.user_type != "master").count()
    new_users_month = User.query.filter(
        User.created_at >= current_month_start,
        User.user_type != "master"
    ).count()
    new_users_last_month = User.query.filter(
        User.created_at >= last_month_start,
        User.created_at < current_month_start,
        User.user_type != "master"
    ).count()
    
    # === Métricas de Clientes ===
    total_clients = Client.query.count()
    new_clients_month = Client.query.filter(Client.created_at >= current_month_start).count()
    
    # === Métricas de Petições ===
    total_petitions = PetitionUsage.query.count()
    petitions_month = PetitionUsage.query.filter(
        PetitionUsage.generated_at >= current_month_start
    ).count()
    petitions_last_month = PetitionUsage.query.filter(
        PetitionUsage.generated_at >= last_month_start,
        PetitionUsage.generated_at < current_month_start
    ).count()
    
    # Valor total de petições no mês
    petitions_value_month = db.session.query(
        func.coalesce(func.sum(PetitionUsage.amount), 0)
    ).filter(PetitionUsage.generated_at >= current_month_start).scalar() or Decimal("0.00")
    
    # === Métricas de IA ===
    ai_generations_month = AIGeneration.query.filter(
        AIGeneration.created_at >= current_month_start
    ).count()
    
    # Tokens usados no mês
    tokens_month = db.session.query(
        func.coalesce(func.sum(AIGeneration.tokens_total), 0)
    ).filter(AIGeneration.created_at >= current_month_start).scalar() or 0
    
    # Custo de IA no mês (em USD)
    ai_cost_month = db.session.query(
        func.coalesce(func.sum(AIGeneration.cost_usd), 0)
    ).filter(AIGeneration.created_at >= current_month_start).scalar() or Decimal("0.00")
    
    # Créditos vendidos no mês
    credits_sold_month = db.session.query(
        func.coalesce(func.sum(CreditTransaction.amount), 0)
    ).filter(
        CreditTransaction.created_at >= current_month_start,
        CreditTransaction.transaction_type == "purchase"
    ).scalar() or 0
    
    # === Métricas Financeiras ===
    # Pagamentos do mês
    payments_month = db.session.query(
        func.coalesce(func.sum(Payment.amount), 0)
    ).filter(
        Payment.paid_at >= current_month_start,
        Payment.payment_status == "completed"
    ).scalar() or Decimal("0.00")
    
    # Usuários pagantes (com plano ativo)
    paying_users = User.query.join(UserPlan).filter(
        UserPlan.status == "active",
        UserPlan.is_current == True
    ).distinct().count()
    
    # === Top Usuários (mais petições no mês) ===
    top_users_petitions = db.session.query(
        User.id,
        User.username,
        User.full_name,
        User.email,
        func.count(PetitionUsage.id).label("petition_count"),
        func.coalesce(func.sum(PetitionUsage.amount), 0).label("total_value")
    ).join(
        PetitionUsage, User.id == PetitionUsage.user_id
    ).filter(
        PetitionUsage.generated_at >= current_month_start
    ).group_by(
        User.id, User.username, User.full_name, User.email
    ).order_by(
        func.count(PetitionUsage.id).desc()
    ).limit(10).all()
    
    # === Top Usuários (mais uso de IA no mês) ===
    top_users_ai = db.session.query(
        User.id,
        User.username,
        User.full_name,
        func.count(AIGeneration.id).label("generation_count"),
        func.coalesce(func.sum(AIGeneration.tokens_total), 0).label("total_tokens"),
        func.coalesce(func.sum(AIGeneration.cost_usd), 0).label("total_cost")
    ).join(
        AIGeneration, User.id == AIGeneration.user_id
    ).filter(
        AIGeneration.created_at >= current_month_start
    ).group_by(
        User.id, User.username, User.full_name
    ).order_by(
        func.sum(AIGeneration.tokens_total).desc()
    ).limit(10).all()
    
    # === Usuários recentes ===
    recent_users = User.query.filter(
        User.user_type != "master"
    ).order_by(
        User.created_at.desc()
    ).limit(10).all()
    
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
        data.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "oab_number": user.oab_number,
            "user_type": user.user_type,
            "is_active": user.is_active,
            "billing_status": user.billing_status,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "days_on_platform": metrics["days_on_platform"],
            "total_petitions": metrics["total_petitions"],
            "total_clients": metrics["total_clients"],
            "petitions_value_total": float(metrics["petitions_value_total"]),
            "ai_credits_balance": metrics["ai_credits_balance"],
            "ai_tokens_month": metrics["ai_tokens_month"],
            "ai_cost_month": float(metrics["ai_cost_month"]),
        })
    
    return jsonify(data)


def _get_user_metrics(user, detailed=False):
    """Calcula métricas para um usuário"""
    now = datetime.utcnow()
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Tempo na plataforma
    days_on_platform = (now - user.created_at).days if user.created_at else 0
    
    # Total de clientes
    total_clients = Client.query.filter_by(lawyer_id=user.id).count()
    
    # Total de petições
    total_petitions = PetitionUsage.query.filter_by(user_id=user.id).count()
    petitions_month = PetitionUsage.query.filter(
        PetitionUsage.user_id == user.id,
        PetitionUsage.generated_at >= current_month_start
    ).count()
    
    # Valor total de petições
    petitions_value_total = db.session.query(
        func.coalesce(func.sum(PetitionUsage.amount), 0)
    ).filter(PetitionUsage.user_id == user.id).scalar() or Decimal("0.00")
    
    petitions_value_month = db.session.query(
        func.coalesce(func.sum(PetitionUsage.amount), 0)
    ).filter(
        PetitionUsage.user_id == user.id,
        PetitionUsage.generated_at >= current_month_start
    ).scalar() or Decimal("0.00")
    
    # Plano atual
    active_plan = user.get_active_plan()
    plan_name = active_plan.plan.name if active_plan else "Nenhum"
    plan_started_at = active_plan.started_at if active_plan else None
    
    # Tempo como pagante
    days_paying = 0
    if plan_started_at:
        days_paying = (now - plan_started_at).days
    
    # Créditos de IA
    user_credits = UserCredits.query.filter_by(user_id=user.id).first()
    ai_credits_balance = user_credits.balance if user_credits else 0
    ai_credits_total_used = user_credits.total_used if user_credits else 0
    
    # Uso de IA no mês
    ai_generations_month = AIGeneration.query.filter(
        AIGeneration.user_id == user.id,
        AIGeneration.created_at >= current_month_start
    ).count()
    
    ai_tokens_month = db.session.query(
        func.coalesce(func.sum(AIGeneration.tokens_total), 0)
    ).filter(
        AIGeneration.user_id == user.id,
        AIGeneration.created_at >= current_month_start
    ).scalar() or 0
    
    ai_cost_month = db.session.query(
        func.coalesce(func.sum(AIGeneration.cost_usd), 0)
    ).filter(
        AIGeneration.user_id == user.id,
        AIGeneration.created_at >= current_month_start
    ).scalar() or Decimal("0.00")
    
    # Total gasto com IA (todos os tempos)
    ai_cost_total = db.session.query(
        func.coalesce(func.sum(AIGeneration.cost_usd), 0)
    ).filter(AIGeneration.user_id == user.id).scalar() or Decimal("0.00")
    
    metrics = {
        "user": user,
        "days_on_platform": days_on_platform,
        "total_clients": total_clients,
        "total_petitions": total_petitions,
        "petitions_month": petitions_month,
        "petitions_value_total": petitions_value_total,
        "petitions_value_month": petitions_value_month,
        "plan_name": plan_name,
        "plan_started_at": plan_started_at,
        "days_paying": days_paying,
        "ai_credits_balance": ai_credits_balance,
        "ai_credits_total_used": ai_credits_total_used,
        "ai_generations_month": ai_generations_month,
        "ai_tokens_month": ai_tokens_month,
        "ai_cost_month": ai_cost_month,
        "ai_cost_total": ai_cost_total,
    }
    
    if detailed:
        # Métricas adicionais para visão detalhada
        
        # Total de pagamentos
        total_payments = db.session.query(
            func.coalesce(func.sum(Payment.amount), 0)
        ).filter(
            Payment.user_id == user.id,
            Payment.payment_status == "completed"
        ).scalar() or Decimal("0.00")
        
        # Último login (se tiver campo)
        # last_login = user.last_login_at  # Se existir
        
        # Clientes criados no mês
        clients_month = Client.query.filter(
            Client.lawyer_id == user.id,
            Client.created_at >= current_month_start
        ).count()
        
        metrics.update({
            "total_payments": total_payments,
            "clients_month": clients_month,
        })
    
    return metrics

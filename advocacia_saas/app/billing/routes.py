"""
Billing Routes - Refatorado para usar Services
"""

from flask import abort, flash, redirect, render_template, request, url_for, jsonify
from flask_login import current_user, login_required

from app import limiter
from app.billing import bp
from app.billing.forms import BillingPlanForm, PetitionTypeForm
from app.billing.services import (
    BillingPlanService,
    BillingPortalService,
    FeatureService,
    PetitionTypeService,
    UserPlanService,
)
from app.decorators import master_required
from app.models import User
from app.rate_limits import ADMIN_API_LIMIT


def _require_admin():
    if current_user.user_type != "master":
        abort(403)


# ===========================================================================
# PORTAL DO USUÁRIO
# ===========================================================================


@bp.route("/portal")
@login_required
def portal():
    """Portal de billing do usuário"""
    billing_info = BillingPortalService.get_user_billing_info(current_user)

    return render_template(
        "billing/portal.html",
        title="Minha assinatura",
        plan=billing_info["plan"],
        cycle=billing_info["cycle"],
        usages=billing_info["usages"],
        totals=billing_info["totals"],
    )


@bp.route("/upgrade")
@login_required
def upgrade():
    """Página para upgrade de plano"""
    upgrade_info = BillingPortalService.get_upgrade_options(current_user)

    return render_template(
        "billing/upgrade.html",
        title="Fazer Upgrade de Plano",
        current_plan=upgrade_info["current_plan"],
        available_plans=upgrade_info["available_plans"],
    )


# ===========================================================================
# GESTÃO DE TIPOS DE PETIÇÃO (ADMIN)
# ===========================================================================


@bp.route("/petition-types", methods=["GET", "POST"])
@login_required
def petition_types():
    """Lista e cria tipos de petição"""
    _require_admin()

    form = PetitionTypeForm()
    if form.validate_on_submit():
        petition_type, error = PetitionTypeService.create({
            "name": form.name.data,
            "description": form.description.data,
            "category": form.category.data,
            "is_billable": form.is_billable.data,
            "base_price": form.base_price.data,
            "active": form.active.data,
        })

        if error:
            flash(error, "warning")
        else:
            flash("Tipo de petição criado com sucesso!", "success")
            return redirect(url_for("billing.petition_types"))

    return render_template(
        "billing/petition_types.html",
        title="Tipos de Petições",
        form=form,
        petition_types=PetitionTypeService.list_all(),
    )


@bp.route("/petition-types/<int:type_id>/edit", methods=["GET", "POST"])
@login_required
def edit_petition_type(type_id):
    """Edita um tipo de petição"""
    _require_admin()

    from app.billing.repository import PetitionTypeRepository
    petition_type = PetitionTypeRepository.get_by_id(type_id)
    if not petition_type:
        abort(404)

    form = PetitionTypeForm(obj=petition_type)

    if form.validate_on_submit():
        _, error = PetitionTypeService.update(type_id, {
            "name": form.name.data,
            "description": form.description.data,
            "category": form.category.data,
            "is_billable": form.is_billable.data,
            "base_price": form.base_price.data,
            "active": form.active.data,
        })

        if error:
            flash(error, "warning")
        else:
            flash("Tipo atualizado com sucesso!", "success")
            return redirect(url_for("billing.petition_types"))

    return render_template(
        "billing/edit_petition_type.html",
        title="Editar tipo de petição",
        form=form,
        petition_type=petition_type,
    )


@bp.route("/petition-types/<int:type_id>/toggle", methods=["POST"])
@login_required
def toggle_petition_type(type_id):
    """Alterna campo de um tipo de petição"""
    _require_admin()

    action = request.form.get("action")
    PetitionTypeService.toggle(type_id, action)
    flash("Tipo atualizado!", "success")
    return redirect(url_for("billing.petition_types"))


# ===========================================================================
# GESTÃO DE PLANOS (ADMIN)
# ===========================================================================


@bp.route("/plans", methods=["GET", "POST"])
@login_required
@master_required
@limiter.limit(ADMIN_API_LIMIT)
def plans():
    """Lista e cria planos de cobrança"""
    form = BillingPlanForm()

    if form.validate_on_submit():
        _, error = BillingPlanService.create({
            "name": form.name.data,
            "description": form.description.data,
            "plan_type": form.plan_type.data,
            "monthly_fee": form.monthly_fee.data,
            "monthly_petition_limit": form.monthly_petition_limit.data,
            "supported_periods": form.supported_periods.data,
            "discount_percentage": form.discount_percentage.data,
            "active": form.active.data,
        })

        if error:
            flash(error, "warning")
        else:
            flash("Plano criado com sucesso!", "success")
            return redirect(url_for("billing.plans"))

    return render_template(
        "billing/plans.html",
        title="Planos de cobrança",
        form=form,
        plans=BillingPlanService.list_all(),
    )


@bp.route("/plans/<int:plan_id>/toggle", methods=["POST"])
@login_required
@master_required
@limiter.limit(ADMIN_API_LIMIT)
def toggle_plan(plan_id):
    """Alterna status ativo de um plano"""
    _require_admin()
    BillingPlanService.toggle_active(plan_id)
    flash("Plano atualizado!", "success")
    return redirect(url_for("billing.plans"))


@bp.route("/plans/<int:plan_id>/edit", methods=["GET", "POST"])
@login_required
def edit_plan(plan_id):
    """Edita um plano de cobrança"""
    _require_admin()

    plan = BillingPlanService.get_by_id(plan_id)
    form = BillingPlanForm()

    if form.validate_on_submit():
        _, error = BillingPlanService.update(plan_id, {
            "name": form.name.data,
            "description": form.description.data,
            "plan_type": form.plan_type.data,
            "monthly_fee": form.monthly_fee.data,
            "monthly_petition_limit": form.monthly_petition_limit.data,
            "supported_periods": form.supported_periods.data,
            "discount_percentage": form.discount_percentage.data,
            "active": form.active.data,
        })

        if error:
            flash(error, "warning")
        else:
            flash("Plano atualizado com sucesso!", "success")
            return redirect(url_for("billing.plans"))

    elif request.method == "GET":
        form.name.data = plan.name
        form.description.data = plan.description
        form.plan_type.data = plan.plan_type
        form.monthly_fee.data = plan.monthly_fee
        form.monthly_petition_limit.data = (
            str(plan.monthly_petition_limit) if plan.monthly_petition_limit else ""
        )
        form.supported_periods.data = plan.supported_periods
        form.discount_percentage.data = plan.discount_percentage
        form.active.data = plan.active

    return render_template(
        "billing/edit_plan.html",
        title=f"Editar Plano - {plan.name}",
        form=form,
        plan=plan,
    )


# ===========================================================================
# GESTÃO DE USUÁRIOS (REDIRECIONAMENTO)
# ===========================================================================


@bp.route("/users", methods=["GET", "POST"])
@login_required
def users():
    """Redirecionamento: Gerenciamento de usuários movido para admin/users"""
    _require_admin()
    flash(
        "Gerenciamento de usuários e planos agora disponível em Admin > Usuários",
        "info",
    )
    return redirect(url_for("admin.users_list"))


@bp.route("/users/<int:user_id>/billing-status", methods=["POST"])
@login_required
def change_billing_status(user_id):
    """Altera status de billing de um usuário"""
    _require_admin()

    user = User.query.get_or_404(user_id)
    status = request.form.get("status")

    if not UserPlanService.change_billing_status(user, status):
        flash("Status inválido.", "warning")
    else:
        flash("Status de cobrança atualizado!", "success")

    return redirect(url_for("billing.users"))


@bp.route("/users/<int:user_id>/plan-status", methods=["POST"])
@login_required
def change_plan_status(user_id):
    """Altera status do plano de um usuário"""
    _require_admin()

    user = User.query.get_or_404(user_id)
    status = request.form.get("status")

    success, error = UserPlanService.change_plan_status(user, status)
    if not success:
        flash(error or "Erro ao atualizar status.", "warning")
    else:
        flash("Status do plano atualizado!", "success")

    return redirect(url_for("billing.users"))


@bp.route("/users/<int:user_id>/assign-plan", methods=["POST"])
@login_required
def assign_plan(user_id):
    """Atribui plano a um usuário"""
    _require_admin()

    user = User.query.get_or_404(user_id)
    plan_id = request.form.get("plan_id")
    status = request.form.get("status", "active")

    if not plan_id:
        flash("Plano não especificado.", "warning")
        return redirect(url_for("admin.users_list"))

    success, error = UserPlanService.assign_plan(user, int(plan_id), status)
    if not success:
        flash(error or "Erro ao atribuir plano.", "warning")
    else:
        from app.billing.repository import BillingPlanRepository
        plan = BillingPlanRepository.get_by_id(int(plan_id))
        flash(f"Plano '{plan.name}' atribuído a {user.full_name or user.email}.", "success")

    return redirect(url_for("admin.users_list"))


# ===========================================================================
# API DE PLANOS
# ===========================================================================


@bp.route("/api/plans", methods=["GET"])
@login_required
def api_plans():
    """API para obter lista de planos ativos"""
    _require_admin()

    plans = BillingPlanService.list_active()
    return jsonify([
        {
            "id": plan.id,
            "name": plan.name,
            "plan_type": plan.plan_type,
            "monthly_fee": float(plan.monthly_fee) if plan.monthly_fee else 0,
            "yearly_fee": float(plan.yearly_fee) if plan.yearly_fee else 0,
        }
        for plan in plans
    ])


# ===========================================================================
# GESTÃO DE FEATURES MODULARES
# ===========================================================================


@bp.route("/features")
@login_required
@master_required
def features_list():
    """Lista todas as features disponíveis"""
    modules = FeatureService.list_all_grouped()
    features = FeatureService.list_active()

    return render_template(
        "billing/features_list.html",
        title="Features Modulares",
        modules=modules,
        features=features,
    )


@bp.route("/plans/<int:plan_id>/features", methods=["GET", "POST"])
@login_required
@master_required
def plan_features(plan_id):
    """Gerenciar features de um plano específico"""
    plan = BillingPlanService.get_by_id(plan_id)

    if request.method == "POST":
        selected_features = request.form.getlist("features")
        limits = {k: v for k, v in request.form.items() if k.startswith("limit_")}

        FeatureService.update_plan_features(plan_id, selected_features, limits)
        flash(f"Features do plano '{plan.name}' atualizadas com sucesso!", "success")
        return redirect(url_for("billing.plan_features", plan_id=plan_id))

    modules = FeatureService.get_plan_features_grouped(plan_id)
    from app.billing.repository import FeatureRepository
    current_features = FeatureRepository.get_plan_features(plan_id)

    return render_template(
        "billing/plan_features.html",
        title=f"Features - {plan.name}",
        plan=plan,
        modules=modules,
        current_features=current_features,
    )


@bp.route("/api/features")
@login_required
@master_required
def api_features_list():
    """API: Lista todas as features"""
    features = FeatureService.list_active()
    return jsonify([f.to_dict() for f in features])


@bp.route("/api/plans/<int:plan_id>/features")
@login_required
@master_required
def api_plan_features(plan_id):
    """API: Lista features de um plano"""
    plan = BillingPlanService.get_by_id(plan_id)
    features_data = plan.get_all_features_with_limits()

    return jsonify([
        {
            "feature": fd["feature"].to_dict(),
            "limit": fd["limit"],
            "config": fd["config"],
        }
        for fd in features_data
    ])

from datetime import datetime, timedelta
from decimal import Decimal
import json

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.billing import bp
from app.billing.forms import AssignPlanForm, BillingPlanForm, PetitionTypeForm
from app.billing.utils import (
    current_billing_cycle,
    ensure_default_petition_types,
    ensure_default_plan,
    slugify,
)
from app.models import BillingPlan, PetitionType, PetitionUsage, User, UserPlan


def _require_admin():
    if current_user.user_type != "master":
        abort(403)


@bp.route("/portal")
@login_required
def portal():
    plan = current_user.get_active_plan()
    cycle = current_billing_cycle()
    usages = (
        PetitionUsage.query.filter_by(user_id=current_user.id, billing_cycle=cycle)
        .order_by(PetitionUsage.generated_at.desc())
        .all()
    )
    totals = {
        "count": len(usages),
        "billable": sum(1 for u in usages if u.billable),
        "billable_amount": sum((u.amount or 0) for u in usages if u.billable),
    }
    return render_template(
        "billing/portal.html",
        title="Minha assinatura",
        plan=plan,
        cycle=cycle,
        usages=usages,
        totals=totals,
    )


@bp.route("/petition-types", methods=["GET", "POST"])
@login_required
def petition_types():
    _require_admin()

    form = PetitionTypeForm()
    if form.validate_on_submit():
        slug = slugify(form.name.data)
        existing = PetitionType.query.filter_by(slug=slug).first()
        if existing:
            flash("Já existe um tipo com este nome/slug.", "warning")
        else:
            petition_type = PetitionType(
                slug=slug,
                name=form.name.data,
                description=form.description.data,
                category=form.category.data,
                is_billable=form.is_billable.data,
                base_price=form.base_price.data,
                active=form.active.data,
            )
            db.session.add(petition_type)
            db.session.commit()
            flash("Tipo de petição criado com sucesso!", "success")
            return redirect(url_for("billing.petition_types"))

    query = PetitionType.query.order_by(PetitionType.category, PetitionType.name).all()
    return render_template(
        "billing/petition_types.html",
        title="Tipos de Petições",
        form=form,
        petition_types=query,
    )


@bp.route("/petition-types/<int:type_id>/edit", methods=["GET", "POST"])
@login_required
def edit_petition_type(type_id):
    _require_admin()

    petition_type = PetitionType.query.get_or_404(type_id)
    form = PetitionTypeForm(obj=petition_type)

    if form.validate_on_submit():
        slug = slugify(form.name.data)
        duplicate = PetitionType.query.filter(
            PetitionType.slug == slug, PetitionType.id != petition_type.id
        ).first()
        if duplicate:
            flash("Outro tipo já usa este nome/slug.", "warning")
        else:
            petition_type.slug = slug
            petition_type.name = form.name.data
            petition_type.description = form.description.data
            petition_type.category = form.category.data
            petition_type.is_billable = form.is_billable.data
            petition_type.base_price = form.base_price.data
            petition_type.active = form.active.data
            db.session.commit()
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
    _require_admin()

    petition_type = PetitionType.query.get_or_404(type_id)
    action = request.form.get("action")
    if action == "toggle_billable":
        petition_type.is_billable = not petition_type.is_billable
    elif action == "toggle_active":
        petition_type.active = not petition_type.active
    db.session.commit()
    flash("Tipo atualizado!", "success")
    return redirect(url_for("billing.petition_types"))


@bp.route("/plans", methods=["GET", "POST"])
@login_required
def plans():
    _require_admin()

    form = BillingPlanForm()
    if form.validate_on_submit():
        slug = slugify(form.name.data)
        if BillingPlan.query.filter_by(slug=slug).first():
            flash("Já existe um plano com este nome.", "warning")
        else:
            plan = BillingPlan(
                slug=slug,
                name=form.name.data,
                description=form.description.data,
                plan_type=form.plan_type.data,
                monthly_fee=form.monthly_fee.data or Decimal("0.00"),
                usage_rate=form.usage_rate.data or Decimal("0.00"),
                supported_periods=form.supported_periods.data
                or ["1m", "3m", "6m", "1y", "2y", "3y"],
                discount_percentage=form.discount_percentage.data or Decimal("0.00"),
                period_discounts=json.loads(form.period_discounts.data) if form.period_discounts.data else {"1m": 0.0, "3m": 5.0, "6m": 7.0, "1y": 9.0, "2y": 13.0, "3y": 20.0},
                active=form.active.data,
            )
            db.session.add(plan)
            db.session.commit()
            flash("Plano criado com sucesso!", "success")
            return redirect(url_for("billing.plans"))

    plans = BillingPlan.query.order_by(BillingPlan.created_at.desc()).all()
    return render_template(
        "billing/plans.html", title="Planos de cobrança", form=form, plans=plans
    )


@bp.route("/plans/<int:plan_id>/toggle", methods=["POST"])
@login_required
def toggle_plan(plan_id):
    _require_admin()
    plan = BillingPlan.query.get_or_404(plan_id)
    plan.active = not plan.active
    db.session.commit()
    flash("Plano atualizado!", "success")
    return redirect(url_for("billing.plans"))


@bp.route("/users", methods=["GET", "POST"])
@login_required
def users():
    _require_admin()

    form = AssignPlanForm()
    users_qs = User.query.order_by(User.created_at.desc()).all()
    plans = BillingPlan.query.order_by(BillingPlan.name).all()
    form.user_id.choices = [
        (u.id, f"{u.full_name or u.email} ({u.email})") for u in users_qs
    ]
    form.plan_id.choices = [(p.id, f"{p.name} ({p.plan_type})") for p in plans]

    usage_map = {
        u.id: u.petition_usages.order_by(PetitionUsage.generated_at.desc()).first()
        for u in users_qs
    }

    if form.validate_on_submit():
        user = User.query.get_or_404(form.user_id.data)
        plan = BillingPlan.query.get_or_404(form.plan_id.data)
        # Mark existing plans as old
        for user_plan in user.plans.filter_by(is_current=True).all():
            user_plan.is_current = False

        new_plan = UserPlan(
            user_id=user.id,
            plan_id=plan.id,
            status=form.status.data,
            started_at=datetime.utcnow(),
            renewal_date=datetime.utcnow() + timedelta(days=30),
            is_current=True,
        )
        db.session.add(new_plan)

        user.billing_status = (
            "delinquent" if form.status.data == "delinquent" else "active"
        )
        db.session.commit()
        flash(
            f"Plano '{plan.name}' atribuído a {user.full_name or user.email}.",
            "success",
        )
        return redirect(url_for("billing.users"))

    return render_template(
        "billing/users.html",
        title="Usuários e planos",
        form=form,
        users=users_qs,
        plans=plans,
        usage_map=usage_map,
    )


@bp.route("/users/<int:user_id>/billing-status", methods=["POST"])
@login_required
def change_billing_status(user_id):
    _require_admin()
    user = User.query.get_or_404(user_id)
    status = request.form.get("status")
    if status not in {"active", "trial", "delinquent"}:
        flash("Status inválido.", "warning")
        return redirect(url_for("billing.users"))

    user.billing_status = status
    plan = user.get_active_plan()
    if plan:
        plan.status = status
    db.session.commit()
    flash("Status de cobrança atualizado!", "success")
    return redirect(url_for("billing.users"))


@bp.route("/users/<int:user_id>/plan-status", methods=["POST"])
@login_required
def change_plan_status(user_id):
    _require_admin()
    user = User.query.get_or_404(user_id)
    status = request.form.get("status")
    if status not in {"active", "trial", "delinquent"}:
        flash("Status inválido.", "warning")
        return redirect(url_for("billing.users"))

    plan = user.get_active_plan()
    if not plan:
        flash("Usuário não possui plano atual.", "warning")
        return redirect(url_for("billing.users"))

    plan.status = status
    if status == "delinquent":
        user.billing_status = "delinquent"
    elif user.billing_status != "delinquent":
        user.billing_status = status
    db.session.commit()
    flash("Status do plano atualizado!", "success")
    return redirect(url_for("billing.users"))

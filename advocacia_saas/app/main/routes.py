from datetime import datetime, timezone

from flask import (
    flash,
    make_response,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func

from app import db
from app.billing.analytics import (
    get_monthly_usage_history,
    get_usage_insights,
    predict_limit_date,
)
from app.billing.decorators import subscription_required
from app.billing.utils import (
    current_billing_cycle,
    get_unread_notifications,
    get_user_petition_usage,
)
from app.decorators import lawyer_required
from app.main import bp
from app.main.forms import TestimonialForm
from app.models import (
    BillingPlan,
    Client,
    PetitionType,
    PetitionUsage,
    RoadmapCategory,
    RoadmapFeedback,
    RoadmapItem,
    Testimonial,
)
from app.quick_actions import build_dashboard_actions

# Ícones para categorias de petições
CATEGORY_ICONS = {
    "civel": "fa-balance-scale",
    "trabalhista": "fa-briefcase",
    "criminal": "fa-gavel",
    "previdenciario": "fa-user-shield",
    "tributario": "fa-file-invoice-dollar",
    "consumidor": "fa-shopping-cart",
    "familia": "fa-users",
    "administrativo": "fa-building",
}

CATEGORY_LABELS = {
    "civel": "Cível",
    "trabalhista": "Trabalhista",
    "criminal": "Criminal",
    "previdenciario": "Previdenciário",
    "tributario": "Tributário",
    "consumidor": "Consumidor",
    "familia": "Família",
    "administrativo": "Administrativo",
}


@bp.route("/favicon.ico")
def favicon():
    """Serve favicon usando o logo do Petitio"""
    return send_from_directory(
        "static/img", "petitio-logo.svg", mimetype="image/svg+xml"
    )


@bp.route("/")
def index():
    plans = _get_public_plans()
    petition_types = _get_implemented_petition_types()

    # Busca depoimentos aprovados (prioriza destacados)
    testimonials = (
        Testimonial.query.filter_by(status="approved")
        .order_by(Testimonial.is_featured.desc(), Testimonial.created_at.desc())
        .limit(6)
        .all()
    )

    return render_template(
        "index.html",
        pricing_plans=plans,
        petition_types=petition_types,
        testimonials=testimonials,
    )


@bp.route("/recursos")
def recursos():
    """Página detalhada de recursos e funcionalidades"""
    return render_template("recursos.html")


@bp.route("/dashboard")
@login_required
@lawyer_required
def dashboard():
    # Get client statistics
    total_clients = Client.query.filter_by(lawyer_id=current_user.id).count()
    recent_clients = (
        Client.query.filter_by(lawyer_id=current_user.id)
        .order_by(Client.created_at.desc())
        .limit(5)
        .all()
    )

    stats = {"total_clients": total_clients, "recent_clients": recent_clients}
    quick_actions = _build_quick_actions_for(current_user)
    plan_summary = _build_plan_summary(current_user)

    # Get petition usage statistics
    petition_usage = get_user_petition_usage(current_user)

    # Get analytics data
    usage_history = get_monthly_usage_history(current_user, months=6)
    prediction = predict_limit_date(current_user)
    insights = get_usage_insights(current_user)

    # Get unread notifications
    notifications = get_unread_notifications(current_user)

    return render_template(
        "dashboard.html",
        title="Dashboard",
        stats=stats,
        quick_actions=quick_actions,
        plan_summary=plan_summary,
        petition_usage=petition_usage,
        usage_history=usage_history,
        prediction=prediction,
        insights=insights,
        notifications=notifications,
    )


@bp.route("/peticionador")
@login_required
@subscription_required
def peticionador():
    # Buscar tipos de petição com formulário dinâmico ativo
    dynamic_petition_types = (
        PetitionType.query.filter_by(use_dynamic_form=True, is_active=True)
        .order_by(PetitionType.name)
        .all()
    )

    return render_template(
        "peticionador.html",
        title="Peticionador",
        dynamic_petition_types=dynamic_petition_types,
    )


@bp.route("/termos")
def terms_of_service():
    """Página de Termos de Uso"""
    return render_template("terms_of_service.html", title="Termos de Uso")


@bp.route("/privacidade")
def privacy_policy():
    """Política de Privacidade em conformidade com LGPD"""
    return render_template("privacy_policy.html", title="Política de Privacidade")


@bp.route("/lgpd")
def lgpd_info():
    """Informações sobre conformidade com LGPD"""
    return render_template("lgpd_info.html", title="Conformidade LGPD")


def _build_quick_actions_for(user):
    return build_dashboard_actions(user.get_quick_actions())


STATUS_BADGES = {
    "active": ("Plano ativo", "success"),
    "trial": ("Período de testes", "info"),
    "delinquent": ("Pagamento pendente", "danger"),
}

PLAN_TYPE_LABELS = {
    "per_usage": "Pague por uso",
    "monthly": "Mensalidade fixa",
}

MONTH_LABELS = {
    "01": "Jan",
    "02": "Fev",
    "03": "Mar",
    "04": "Abr",
    "05": "Mai",
    "06": "Jun",
    "07": "Jul",
    "08": "Ago",
    "09": "Set",
    "10": "Out",
    "11": "Nov",
    "12": "Dez",
}


def _build_plan_summary(user):
    plan_rel = user.get_active_plan()
    has_plan = plan_rel is not None
    status_label, badge_variant = STATUS_BADGES.get(
        user.billing_status, ("Status indefinido", "secondary")
    )

    summary = {
        "has_plan": has_plan,
        "status_label": status_label,
        "status_badge": badge_variant,
        "manage_url": url_for("billing.portal"),
        "warning": None,
    }

    if user.billing_status == "delinquent":
        summary["warning"] = (
            "Pagamento pendente detectado. Regularize para continuar gerando petições."
        )

    # Adicionar informações sobre trial se o usuário estiver em período de teste
    if user.trial_active:
        if user.is_trial_expired:
            summary["warning"] = (
                "Seu período de teste expirou. Assine um plano para continuar usando o sistema."
            )
        else:
            summary["trial_info"] = {
                "days_remaining": user.trial_days_remaining,
                "message": f"Você está em período de teste com {user.trial_days_remaining} dias restantes.",
            }

    if not has_plan:
        summary.update(
            {
                "plan_name": None,
                "plan_type_label": None,
                "monthly_fee_display": "—",
                "usage_rate_display": "—",
                "cycle_usage_total": 0,
                "cycle_usage_amount_display": "R$ 0,00",
                "cycle_label": _current_cycle_label(),
                "started_at_label": None,
                "renewal_label": None,
            }
        )
        summary["empty_message"] = (
            "Você ainda não definiu um plano. Configure pagamentos para liberar todas as funcionalidades."
        )
        return summary

    plan = plan_rel.plan
    plan_type_label = PLAN_TYPE_LABELS.get(plan.plan_type, plan.plan_type.title())
    monthly_fee_display = _format_currency(plan.monthly_fee)
    # usage_rate_display removido - sistema simplificado

    cycle = current_billing_cycle()
    cycle_label = _current_cycle_label(cycle)
    usage_total = PetitionUsage.query.filter_by(
        user_id=user.id, billing_cycle=cycle
    ).count()
    billable_amount = (
        db.session.query(func.coalesce(func.sum(PetitionUsage.amount), 0))
        .filter(
            PetitionUsage.user_id == user.id,
            PetitionUsage.billing_cycle == cycle,
            PetitionUsage.billable.is_(True),
        )
        .scalar()
    )

    summary.update(
        {
            "plan_name": plan.name,
            "plan_type_label": plan_type_label,
            "monthly_fee_display": monthly_fee_display,
            "cycle_usage_total": usage_total,
            "cycle_usage_amount_display": _format_currency(billable_amount),
            "cycle_label": cycle_label,
            "started_at_label": _format_date(plan_rel.started_at),
            "renewal_label": _format_date(plan_rel.renewal_date),
        }
    )
    return summary


def _get_public_plans():
    plans = (
        BillingPlan.query.filter_by(active=True)
        .order_by(BillingPlan.plan_type, BillingPlan.name)
        .all()
    )
    public = []
    for plan in plans:
        public.append(
            {
                "name": plan.name,
                "description": plan.description,
                "plan_type_label": PLAN_TYPE_LABELS.get(
                    plan.plan_type, plan.plan_type.title()
                ),
                "monthly_fee": _format_currency(plan.monthly_fee),
                # usage_rate removido - sistema simplificado
                "is_per_usage": plan.plan_type == "per_usage",
            }
        )
    return public


def _format_currency(value):
    if not value:
        return "R$ 0,00"
    formatted = f"{value:,.2f}" if value else "0,00"
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def _format_date(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    return str(value)


def _current_cycle_label(cycle=None):
    cycle = cycle or current_billing_cycle()
    year, month = cycle.split("-")
    month_label = MONTH_LABELS.get(month, month)
    return f"{month_label}/{year}"


def _get_implemented_petition_types():
    """Retorna os tipos de petição implementados para exibição pública."""
    types = (
        PetitionType.query.filter_by(is_implemented=True, is_active=True)
        .order_by(PetitionType.category, PetitionType.name)
        .all()
    )
    result = []
    for pt in types:
        result.append(
            {
                "id": pt.id,
                "name": pt.name,
                "description": pt.description or "Petição disponível para uso.",
                "category": pt.category,
                "category_label": CATEGORY_LABELS.get(pt.category, pt.category.title()),
                "icon": CATEGORY_ICONS.get(pt.category, "fa-file-alt"),
                "price": _format_currency(pt.base_price)
                if pt.is_billable
                else "Gratuito",
            }
        )
    return result


# ===== Testimonials Routes =====


@bp.route("/depoimentos")
@login_required
def testimonials():
    """Lista os depoimentos do usuário atual."""
    user_testimonials = (
        Testimonial.query.filter_by(user_id=current_user.id)
        .order_by(Testimonial.created_at.desc())
        .all()
    )
    return render_template(
        "testimonials/index.html",
        title="Meus Depoimentos",
        testimonials=user_testimonials,
    )


@bp.route("/depoimentos/novo", methods=["GET", "POST"])
@login_required
def new_testimonial():
    """Formulário para enviar um novo depoimento."""
    form = TestimonialForm()

    # Pré-preenche o nome se disponível
    if request.method == "GET" and current_user.full_name:
        form.display_name.data = current_user.full_name

    if form.validate_on_submit():
        testimonial = Testimonial(
            user_id=current_user.id,
            content=form.content.data.strip(),
            rating=int(form.rating.data),
            display_name=form.display_name.data.strip(),
            display_role=form.display_role.data.strip()
            if form.display_role.data
            else None,
            display_location=form.display_location.data.strip()
            if form.display_location.data
            else None,
            status="pending",
        )
        db.session.add(testimonial)
        db.session.commit()
        flash(
            "Seu depoimento foi enviado e está aguardando aprovação. Obrigado!",
            "success",
        )
        return redirect(url_for("main.testimonials"))

    return render_template(
        "testimonials/form.html",
        title="Enviar Depoimento",
        form=form,
    )


@bp.route("/depoimentos/<int:testimonial_id>/editar", methods=["GET", "POST"])
@login_required
def edit_testimonial(testimonial_id):
    """Edita um depoimento existente (apenas se pendente)."""
    testimonial = Testimonial.query.get_or_404(testimonial_id)

    if testimonial.user_id != current_user.id:
        flash("Você não tem permissão para editar este depoimento.", "danger")
        return redirect(url_for("main.testimonials"))

    if testimonial.status != "pending":
        flash("Apenas depoimentos pendentes podem ser editados.", "warning")
        return redirect(url_for("main.testimonials"))

    form = TestimonialForm(obj=testimonial)

    if form.validate_on_submit():
        testimonial.content = form.content.data.strip()
        testimonial.rating = int(form.rating.data)
        testimonial.display_name = form.display_name.data.strip()
        testimonial.display_role = (
            form.display_role.data.strip() if form.display_role.data else None
        )
        testimonial.display_location = (
            form.display_location.data.strip() if form.display_location.data else None
        )
        testimonial.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        flash("Depoimento atualizado com sucesso!", "success")
        return redirect(url_for("main.testimonials"))

    return render_template(
        "testimonials/form.html",
        title="Editar Depoimento",
        form=form,
        testimonial=testimonial,
    )


@bp.route("/depoimentos/<int:testimonial_id>/excluir", methods=["POST"])
@login_required
def delete_testimonial(testimonial_id):
    """Exclui um depoimento do usuário."""
    testimonial = Testimonial.query.get_or_404(testimonial_id)

    if testimonial.user_id != current_user.id:
        flash("Você não tem permissão para excluir este depoimento.", "danger")
        return redirect(url_for("main.testimonials"))

    db.session.delete(testimonial)
    db.session.commit()
    flash("Depoimento excluído com sucesso.", "success")
    return redirect(url_for("main.testimonials"))


# ===== Admin Testimonials Routes =====


@bp.route("/admin/depoimentos")
@login_required
def admin_testimonials():
    """Lista todos os depoimentos para moderação (apenas admin)."""
    if current_user.user_type != "master":
        flash("Acesso negado.", "danger")
        return redirect(url_for("main.dashboard"))

    status_filter = request.args.get("status", "pending")
    query = Testimonial.query

    if status_filter and status_filter != "all":
        query = query.filter_by(status=status_filter)

    testimonials = query.order_by(Testimonial.created_at.desc()).all()

    # Contadores
    counts = {
        "pending": Testimonial.query.filter_by(status="pending").count(),
        "approved": Testimonial.query.filter_by(status="approved").count(),
        "rejected": Testimonial.query.filter_by(status="rejected").count(),
    }

    return render_template(
        "testimonials/admin.html",
        title="Moderar Depoimentos",
        testimonials=testimonials,
        counts=counts,
        current_filter=status_filter,
    )


@bp.route("/admin/depoimentos/<int:testimonial_id>/moderar", methods=["POST"])
@login_required
def moderate_testimonial(testimonial_id):
    """Aprova ou rejeita um depoimento."""
    if current_user.user_type != "master":
        flash("Acesso negado.", "danger")
        return redirect(url_for("main.dashboard"))

    testimonial = Testimonial.query.get_or_404(testimonial_id)
    action = request.form.get("action")

    if action == "approve":
        testimonial.status = "approved"
        testimonial.moderated_by = current_user.id
        testimonial.moderated_at = datetime.now(timezone.utc)
        testimonial.rejection_reason = None
        flash(f"Depoimento de {testimonial.display_name} aprovado!", "success")
    elif action == "reject":
        testimonial.status = "rejected"
        testimonial.moderated_by = current_user.id
        testimonial.moderated_at = datetime.now(timezone.utc)
        testimonial.rejection_reason = request.form.get("rejection_reason", "")
        flash(f"Depoimento de {testimonial.display_name} rejeitado.", "warning")
    elif action == "feature":
        testimonial.is_featured = not testimonial.is_featured
        status = "destacado" if testimonial.is_featured else "removido do destaque"
        flash(f"Depoimento {status}.", "success")

    db.session.commit()
    return redirect(url_for("main.admin_testimonials"))


def get_approved_testimonials(limit=6, featured_only=False):
    """Retorna depoimentos aprovados para exibição na página inicial."""
    query = Testimonial.query.filter_by(status="approved")
    if featured_only:
        query = query.filter_by(is_featured=True)
    return query.order_by(Testimonial.created_at.desc()).limit(limit).all()


@bp.route("/notifications")
@login_required
@lawyer_required
def notifications():
    """Página de histórico de notificações."""
    from app.models import Notification

    all_notifications = (
        Notification.query.filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )

    unread_count = sum(1 for n in all_notifications if not n.read)

    return render_template(
        "notifications.html",
        title="Notificações",
        notifications=all_notifications,
        unread_count=unread_count,
    )


@bp.route("/notifications/mark-read/<int:notification_id>", methods=["POST"])
@login_required
def mark_notification_read(notification_id):
    """Marca uma notificação como lida via AJAX."""
    from flask import jsonify

    from app.billing.utils import mark_notification_as_read

    success = mark_notification_as_read(notification_id, current_user)

    if success:
        return jsonify(
            {"status": "success", "message": "Notificação marcada como lida"}
        ), 200
    else:
        return jsonify(
            {"status": "error", "message": "Notificação não encontrada"}
        ), 404


@bp.route("/notifications/mark-all-read", methods=["POST"])
@login_required
def mark_all_notifications_read():
    """Marca todas as notificações como lidas."""
    from flask import jsonify

    from app.models import Notification

    notifications = Notification.query.filter_by(
        user_id=current_user.id, read=False
    ).all()

    for notification in notifications:
        notification.read = True
        notification.read_at = datetime.now(timezone.utc)

    db.session.commit()

    return jsonify(
        {
            "status": "success",
            "message": f"{len(notifications)} notificações marcadas como lidas",
        }
    ), 200


@bp.route("/sitemap.xml")
def sitemap():
    """Sitemap XML dinâmico para SEO"""
    from datetime import datetime, timedelta

    # URLs principais
    urls = [
        {
            "loc": url_for("main.index", _external=True),
            "lastmod": datetime.now().strftime("%Y-%m-%d"),
            "changefreq": "weekly",
            "priority": "1.0",
        },
        {
            "loc": url_for("main.recursos", _external=True),
            "lastmod": datetime.now().strftime("%Y-%m-%d"),
            "changefreq": "monthly",
            "priority": "0.8",
        },
        {
            "loc": url_for("auth.register", _external=True),
            "lastmod": datetime.now().strftime("%Y-%m-%d"),
            "changefreq": "monthly",
            "priority": "0.9",
        },
        {
            "loc": url_for("portal.login", _external=True),
            "lastmod": datetime.now().strftime("%Y-%m-%d"),
            "changefreq": "monthly",
            "priority": "0.7",
        },
    ]

    # URLs de planos (se existirem)
    try:
        plans = BillingPlan.query.filter_by(active=True).all()
        for plan in plans:
            urls.append(
                {
                    "loc": url_for("payments.plans", _external=True),
                    "lastmod": datetime.now().strftime("%Y-%m-%d"),
                    "changefreq": "weekly",
                    "priority": "0.8",
                }
            )
            break  # Só uma URL de planos
    except:
        pass

    # URLs de tipos de petição
    try:
        petition_types = PetitionType.query.filter_by(active=True).limit(10).all()
        for pt in petition_types:
            urls.append(
                {
                    "loc": url_for(
                        "petitions.create", petition_type_slug=pt.slug, _external=True
                    ),
                    "lastmod": datetime.now().strftime("%Y-%m-%d"),
                    "changefreq": "weekly",
                    "priority": "0.8",
                }
            )
    except:
        pass

    # Renderizar template XML
    xml_content = render_template("sitemap.xml", urls=urls)
    response = make_response(xml_content)
    response.headers["Content-Type"] = "application/xml"
    return response


@bp.route("/robots.txt")
def robots():
    """Arquivo robots.txt para SEO"""
    from flask import make_response

    robots_content = f"""User-agent: *
Allow: /

# Páginas importantes para geração de petições
Allow: /
Allow: /recursos
Allow: /auth/register

# Bloquear áreas administrativas
Disallow: /admin/
Disallow: /auth/login
Disallow: /portal/
Disallow: /dashboard
Disallow: /api/

# Sitemap
Sitemap: {url_for("main.sitemap", _external=True)}
"""

    response = make_response(robots_content)
    response.headers["Content-Type"] = "text/plain"
    return response


# =============================================================================
# ROADMAP PUBLIC ROUTES
# =============================================================================


@bp.route("/roadmap")
def roadmap():
    """Página pública do roadmap de desenvolvimento"""

    # Buscar apenas itens visíveis aos usuários
    public_items = (
        RoadmapItem.query.filter_by(visible_to_users=True).join(RoadmapCategory).all()
    )

    # Agrupar por categoria
    categories = {}
    for item in public_items:
        cat_slug = item.category.slug
        if cat_slug not in categories:
            categories[cat_slug] = {"category": item.category, "items": []}
        categories[cat_slug]["items"].append(item)

    # Ordenar categorias por ordem definida
    sorted_categories = sorted(categories.values(), key=lambda x: x["category"].order)

    # Estatísticas públicas
    total_features = len(public_items)
    completed_features = len(
        [item for item in public_items if item.status == "completed"]
    )
    in_progress_features = len(
        [item for item in public_items if item.status == "in_progress"]
    )

    # Calcular progresso geral
    if total_features > 0:
        overall_progress = (completed_features / total_features) * 100
    else:
        overall_progress = 0

    return render_template(
        "main/roadmap.html",
        title="Roadmap de Desenvolvimento",
        categories=sorted_categories,
        total_features=total_features,
        completed_features=completed_features,
        in_progress_features=in_progress_features,
        overall_progress=round(overall_progress, 1),
    )


@bp.route("/roadmap/<slug>")
def roadmap_item(slug):
    """Página detalhada de um item do roadmap"""

    item = RoadmapItem.query.filter_by(slug=slug, visible_to_users=True).first_or_404()

    # Buscar itens relacionados (mesma categoria)
    related_items = (
        RoadmapItem.query.filter(
            RoadmapItem.category_id == item.category_id,
            RoadmapItem.id != item.id,
            RoadmapItem.visible_to_users == True,
        )
        .limit(5)
        .all()
    )

    return render_template(
        "main/roadmap_item.html",
        title=item.title,
        item=item,
        related_items=related_items,
    )


# =============================================================================
# ROADMAP FEEDBACK ROUTES
# =============================================================================


@bp.route("/roadmap/<slug>/feedback", methods=["GET", "POST"])
@login_required
def roadmap_item_feedback(slug):
    """Página para usuários darem feedback sobre uma funcionalidade implementada"""

    item = RoadmapItem.query.filter_by(slug=slug, visible_to_users=True).first_or_404()

    # Verificar se o item está implementado (completed)
    if item.status != "completed":
        flash("Esta funcionalidade ainda não foi implementada.", "warning")
        return redirect(url_for("main.roadmap_item", slug=slug))

    # Verificar se o usuário já deu feedback
    existing_feedback = RoadmapFeedback.query.filter_by(
        roadmap_item_id=item.id, user_id=current_user.id
    ).first()

    if request.method == "POST":
        # Processar o feedback
        rating = int(request.form.get("rating", 5))
        rating_category = request.form.get("rating_category")
        title = request.form.get("title", "").strip()
        comment = request.form.get("comment", "").strip()
        pros = request.form.get("pros", "").strip()
        cons = request.form.get("cons", "").strip()
        suggestions = request.form.get("suggestions", "").strip()
        usage_frequency = request.form.get("usage_frequency")
        ease_of_use = request.form.get("ease_of_use")
        is_anonymous = request.form.get("is_anonymous") == "on"

        # Validar rating
        if not 1 <= rating <= 5:
            flash("Avaliação deve ser entre 1 e 5 estrelas.", "danger")
            return redirect(request.url)

        if existing_feedback:
            # Atualizar feedback existente
            existing_feedback.rating = rating
            existing_feedback.rating_category = rating_category
            existing_feedback.title = title
            existing_feedback.comment = comment
            existing_feedback.pros = pros
            existing_feedback.cons = cons
            existing_feedback.suggestions = suggestions
            existing_feedback.usage_frequency = usage_frequency
            existing_feedback.ease_of_use = ease_of_use
            existing_feedback.is_anonymous = is_anonymous
            existing_feedback.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            flash("Seu feedback foi atualizado com sucesso!", "success")
        else:
            # Criar novo feedback
            feedback = RoadmapFeedback(
                roadmap_item_id=item.id,
                user_id=current_user.id,
                rating=rating,
                rating_category=rating_category,
                title=title,
                comment=comment,
                pros=pros,
                cons=cons,
                suggestions=suggestions,
                usage_frequency=usage_frequency,
                ease_of_use=ease_of_use,
                is_anonymous=is_anonymous,
                user_agent=request.headers.get("User-Agent"),
                ip_address=request.remote_addr,
                session_id=request.cookies.get("session", ""),
            )
            db.session.add(feedback)
            db.session.commit()
            flash(
                "Obrigado pelo seu feedback! Ele nos ajuda a melhorar continuamente.",
                "success",
            )

        return redirect(url_for("main.roadmap_item", slug=slug))

    return render_template(
        "main/roadmap_feedback.html",
        title=f"Feedback - {item.title}",
        item=item,
        existing_feedback=existing_feedback,
    )


@bp.route("/roadmap/<slug>/feedback/thanks")
@login_required
def roadmap_feedback_thanks(slug):
    """Página de agradecimento após enviar feedback"""

    item = RoadmapItem.query.filter_by(slug=slug, visible_to_users=True).first_or_404()

    return render_template(
        "main/roadmap_feedback_thanks.html",
        title="Obrigado pelo Feedback",
        item=item,
    )

"""Rotas para gerenciamento de Escritório"""

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.billing.decorators import feature_required
from app.decorators import lawyer_required
from app.office import bp
from app.office.forms import (
    ChangeMemberRoleForm,
    CreateOfficeForm,
    InviteMemberForm,
    OfficeSettingsForm,
    TransferOwnershipForm,
)
from app.office.services import (
    OfficeInviteService,
    OfficeMemberService,
    OfficeService,
)

# =============================================================================
# Decorators específicos do módulo Office
# =============================================================================


def office_required(f):
    """
    Decorator que requer que o usuário pertença a um escritório.
    """
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.office_id:
            flash(
                "Você precisa criar ou participar de um escritório para acessar esta funcionalidade.",
                "warning",
            )
            return redirect(url_for("office.create"))
        return f(*args, **kwargs)

    return decorated_function


def office_admin_required(f):
    """
    Decorator que requer que o usuário seja admin ou owner do escritório.
    """
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.office_id:
            flash("Você não pertence a nenhum escritório.", "warning")
            return redirect(url_for("office.create"))

        if not current_user.can_manage_office():
            flash("Você não tem permissão para gerenciar o escritório.", "danger")
            return redirect(url_for("office.dashboard"))
        return f(*args, **kwargs)

    return decorated_function


def office_owner_required(f):
    """
    Decorator que requer que o usuário seja o dono do escritório.
    """
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.office_id:
            flash("Você não pertence a nenhum escritório.", "warning")
            return redirect(url_for("office.create"))

        if not current_user.is_office_owner():
            flash(
                "Apenas o proprietário do escritório pode realizar esta ação.", "danger"
            )
            return redirect(url_for("office.dashboard"))
        return f(*args, **kwargs)

    return decorated_function


# =============================================================================
# Rotas principais
# =============================================================================


@bp.route("/")
@login_required
@lawyer_required
def index():
    """Página inicial do módulo de escritório"""
    if current_user.office_id:
        return redirect(url_for("office.dashboard"))
    return redirect(url_for("office.create"))


@bp.route("/create", methods=["GET", "POST"])
@login_required
@lawyer_required
@feature_required("multi_users")
def create():
    """Criar um novo escritório"""
    if current_user.office_id:
        flash("Você já pertence a um escritório.", "info")
        return redirect(url_for("office.dashboard"))

    form = CreateOfficeForm()

    if form.validate_on_submit():
        success, message = OfficeService.create_office(
            current_user,
            {
                "name": form.name.data,
                "cnpj": form.cnpj.data,
                "oab_number": form.oab_number.data,
                "phone": form.phone.data,
                "email": form.email.data,
                "website": form.website.data,
            },
        )
        flash(message, "success" if success else "danger")
        if success:
            return redirect(url_for("office.dashboard"))

    return render_template(
        "office/create.html",
        title="Criar Escritório",
        form=form,
    )


@bp.route("/dashboard")
@login_required
@lawyer_required
@office_required
def dashboard():
    """Dashboard do escritório"""
    data = OfficeService.get_dashboard_data(current_user)

    if not data:
        flash("Escritório não encontrado.", "danger")
        return redirect(url_for("office.create"))

    return render_template(
        "office/dashboard.html",
        title=f"Escritório - {data['office'].name}",
        **data,
    )


@bp.route("/settings", methods=["GET", "POST"])
@login_required
@lawyer_required
@office_admin_required
def settings():
    """Configurações do escritório"""
    office = current_user.get_office()

    if not office:
        flash("Escritório não encontrado.", "danger")
        return redirect(url_for("office.create"))

    form = OfficeSettingsForm(obj=office)

    if form.validate_on_submit():
        success, message = OfficeService.update_settings(
            current_user,
            {
                "name": form.name.data,
                "cnpj": form.cnpj.data,
                "oab_number": form.oab_number.data,
                "phone": form.phone.data,
                "email": form.email.data,
                "website": form.website.data,
                "address": form.address.data if hasattr(form, "address") else None,
            },
        )
        flash(message, "success" if success else "danger")
        if success:
            return redirect(url_for("office.settings"))

    return render_template(
        "office/settings.html",
        title="Configurações do Escritório",
        office=office,
        form=form,
    )


# =============================================================================
# Gerenciamento de Membros
# =============================================================================


@bp.route("/members")
@login_required
@lawyer_required
@office_required
def members():
    """Lista de membros do escritório"""
    data = OfficeMemberService.get_members_page_data(current_user)

    if not data:
        flash("Escritório não encontrado.", "danger")
        return redirect(url_for("office.create"))

    # Forms
    invite_form = InviteMemberForm()
    role_form = ChangeMemberRoleForm()

    return render_template(
        "office/members.html",
        title="Membros do Escritório",
        invite_form=invite_form,
        role_form=role_form,
        **data,
    )


@bp.route("/members/invite", methods=["POST"])
@login_required
@lawyer_required
@office_admin_required
def invite_member():
    """Enviar convite para novo membro"""
    form = InviteMemberForm()

    if form.validate_on_submit():
        success, message, invite_url = OfficeInviteService.send_invite(
            current_user,
            form.email.data,
            form.role.data,
        )

        if success:
            if invite_url:
                flash(f"{message} Link: {invite_url}", "warning")
            else:
                flash(message, "success")
        else:
            flash(message, "warning" if "já existe" in message.lower() else "danger")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{error}", "danger")

    return redirect(url_for("office.members"))


@bp.route("/members/<int:member_id>/change-role", methods=["POST"])
@login_required
@lawyer_required
@office_admin_required
def change_member_role(member_id):
    """Alterar função de um membro"""
    new_role = request.form.get("role")
    success, message = OfficeMemberService.change_member_role(
        current_user, member_id, new_role
    )
    flash(message, "success" if success else "danger")
    return redirect(url_for("office.members"))


@bp.route("/members/<int:member_id>/remove", methods=["POST"])
@login_required
@lawyer_required
@office_admin_required
def remove_member(member_id):
    """Remover membro do escritório"""
    success, message = OfficeMemberService.remove_member(current_user, member_id)
    flash(
        message,
        "success" if success else "danger" if "não" in message.lower() else "warning",
    )
    return redirect(url_for("office.members"))


@bp.route("/invites/<int:invite_id>/cancel", methods=["POST"])
@login_required
@lawyer_required
@office_admin_required
def cancel_invite(invite_id):
    """Cancelar um convite pendente"""
    success, message = OfficeInviteService.cancel_invite(current_user, invite_id)
    flash(message, "success" if success else "danger")
    return redirect(url_for("office.members"))


@bp.route("/invites/<int:invite_id>/resend", methods=["POST"])
@login_required
@lawyer_required
@office_admin_required
def resend_invite(invite_id):
    """Reenviar um convite"""
    success, message, invite_url = OfficeInviteService.resend_invite(
        current_user, invite_id
    )

    if success:
        if invite_url:
            flash(f"{message} Link: {invite_url}", "warning")
        else:
            flash(message, "success")
    else:
        flash(message, "danger")

    return redirect(url_for("office.members"))


# =============================================================================
# Aceitar Convite
# =============================================================================


@bp.route("/invite/<token>")
@login_required
@lawyer_required
def accept_invite_page(token):
    """Página para aceitar convite"""
    success, message, data = OfficeInviteService.validate_invite(token, current_user)

    if not success:
        flash(message, "danger" if "não encontrado" in message.lower() else "warning")
        if "já pertence" in message.lower():
            return redirect(url_for("office.dashboard"))
        return redirect(url_for("main.index"))

    return render_template(
        "office/accept_invite.html",
        title="Aceitar Convite",
        invite=data["invite"],
        office=data["office"],
        inviter=data["inviter"],
        role_info=data["role_info"],
    )


@bp.route("/invite/<token>/accept", methods=["POST"])
@login_required
@lawyer_required
def accept_invite(token):
    """Aceitar convite para escritório"""
    success, message = OfficeInviteService.accept_invite(token, current_user)

    if success:
        flash(message, "success")
        return redirect(url_for("office.dashboard"))
    else:
        flash(message, "danger" if "inválido" in message.lower() else "warning")
        return redirect(url_for("main.index"))


@bp.route("/invite/<token>/decline", methods=["POST"])
@login_required
def decline_invite(token):
    """Recusar convite"""
    success, message = OfficeInviteService.decline_invite(token, current_user)
    flash(message, "info" if success else "danger")
    return redirect(url_for("main.index"))


# =============================================================================
# Transferir Propriedade / Sair do Escritório
# =============================================================================


@bp.route("/transfer-ownership", methods=["GET", "POST"])
@login_required
@lawyer_required
@office_owner_required
def transfer_ownership():
    """Transferir propriedade do escritório"""
    office = current_user.get_office()

    if not office:
        flash("Escritório não encontrado.", "danger")
        return redirect(url_for("office.create"))

    form = TransferOwnershipForm()

    # Obter membros elegíveis
    candidates = OfficeMemberService.get_transfer_candidates(current_user)
    form.new_owner_id.choices = candidates

    if not candidates:
        flash(
            "Não há outros membros elegíveis para transferir a propriedade.", "warning"
        )
        return redirect(url_for("office.dashboard"))

    if form.validate_on_submit():
        success, message = OfficeMemberService.transfer_ownership(
            current_user, form.new_owner_id.data
        )
        flash(message, "success" if success else "danger")
        if success:
            return redirect(url_for("office.dashboard"))

    return render_template(
        "office/transfer_ownership.html",
        title="Transferir Propriedade",
        office=office,
        form=form,
    )


@bp.route("/leave", methods=["POST"])
@login_required
@lawyer_required
@office_required
def leave_office():
    """Sair do escritório"""
    success, message = OfficeMemberService.leave_office(current_user)

    if success:
        flash(message, "info")
        return redirect(url_for("main.index"))
    else:
        flash(message, "danger")
        return redirect(url_for("office.dashboard"))


@bp.route("/delete", methods=["POST"])
@login_required
@lawyer_required
@office_owner_required
def delete_office():
    """Excluir escritório"""
    success, message = OfficeService.delete_office(current_user)
    flash(message, "info" if success else "danger")

    if success:
        return redirect(url_for("main.index"))
    else:
        return redirect(url_for("office.members"))

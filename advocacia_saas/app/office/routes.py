"""Rotas para gerenciamento de Escritório"""

from datetime import datetime, timezone

from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from app import db
from app.billing.decorators import feature_required
from app.decorators import lawyer_required
from app.models import OFFICE_ROLES, Office, OfficeInvite, User
from app.office import bp
from app.office.forms import (
    ChangeMemberRoleForm,
    CreateOfficeForm,
    InviteMemberForm,
    OfficeSettingsForm,
    TransferOwnershipForm,
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
    # Se já tem escritório, redireciona
    if current_user.office_id:
        flash("Você já pertence a um escritório.", "info")
        return redirect(url_for("office.dashboard"))

    form = CreateOfficeForm()

    if form.validate_on_submit():
        # Criar o escritório
        office = Office(
            name=form.name.data,
            slug=Office.generate_slug(form.name.data),
            owner_id=current_user.id,
            cnpj=form.cnpj.data or None,
            oab_number=form.oab_number.data or None,
            phone=form.phone.data or None,
            email=form.email.data or None,
            website=form.website.data or None,
        )
        db.session.add(office)
        db.session.flush()  # Obter o ID do escritório

        # Vincular o usuário atual ao escritório como owner
        current_user.office_id = office.id
        current_user.office_role = "owner"

        db.session.commit()

        flash(f"Escritório '{office.name}' criado com sucesso!", "success")
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
    office = current_user.get_office()

    if not office:
        flash("Escritório não encontrado.", "danger")
        return redirect(url_for("office.create"))

    # Estatísticas do escritório
    members = office.members.filter_by(is_active=True).all()
    pending_invites = office.invites.filter_by(status="pending").count()
    max_members = office.get_max_members()

    # Obter roles info para exibição
    roles_info = OFFICE_ROLES

    return render_template(
        "office/dashboard.html",
        title=f"Escritório - {office.name}",
        office=office,
        members=members,
        pending_invites=pending_invites,
        max_members=max_members,
        roles_info=roles_info,
        can_manage=current_user.can_manage_office(),
        is_owner=current_user.is_office_owner(),
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
        form.populate_obj(office)
        office.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        flash("Configurações salvas com sucesso!", "success")
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
    office = current_user.get_office()

    if not office:
        flash("Escritório não encontrado.", "danger")
        return redirect(url_for("office.create"))

    members_list = office.members.order_by(User.full_name).all()
    pending_invites = (
        office.invites.filter_by(status="pending")
        .order_by(OfficeInvite.created_at.desc())
        .all()
    )

    # Buscar inviters para os convites pendentes
    inviter_ids = set(invite.invited_by_id for invite in pending_invites)
    inviter_users = (
        {u.id: u for u in User.query.filter(User.id.in_(inviter_ids)).all()}
        if inviter_ids
        else {}
    )

    # Forms
    invite_form = InviteMemberForm()
    role_form = ChangeMemberRoleForm()

    return render_template(
        "office/members.html",
        title="Membros do Escritório",
        office=office,
        members=members_list,
        pending_invites=pending_invites,
        inviter_users=inviter_users,
        invite_form=invite_form,
        role_form=role_form,
        roles_info=OFFICE_ROLES,
        can_manage=current_user.can_manage_office(),
        is_owner=current_user.is_office_owner(),
        can_add_member=office.can_add_member(),
        max_members=office.get_max_members(),
    )


@bp.route("/members/invite", methods=["POST"])
@login_required
@lawyer_required
@office_admin_required
def invite_member():
    """Enviar convite para novo membro"""
    office = current_user.get_office()

    if not office:
        flash("Escritório não encontrado.", "danger")
        return redirect(url_for("office.create"))

    # Verificar se pode adicionar mais membros
    if not office.can_add_member():
        flash(
            f"Limite de {office.get_max_members()} membros atingido. Faça upgrade do plano para adicionar mais.",
            "warning",
        )
        return redirect(url_for("office.members"))

    form = InviteMemberForm()

    if form.validate_on_submit():
        email = form.email.data.lower()
        role = form.role.data

        # Verificar se já existe convite pendente
        existing_invite = OfficeInvite.query.filter_by(
            office_id=office.id, email=email, status="pending"
        ).first()

        if existing_invite:
            flash("Já existe um convite pendente para este e-mail.", "warning")
            return redirect(url_for("office.members"))

        # Verificar se já é membro
        existing_member = User.query.filter_by(email=email, office_id=office.id).first()
        if existing_member:
            flash("Este usuário já é membro do escritório.", "warning")
            return redirect(url_for("office.members"))

        # Criar convite
        invite = OfficeInvite.create_invite(
            office_id=office.id,
            email=email,
            role=role,
            invited_by_id=current_user.id,
        )

        if invite:
            db.session.commit()

            # TODO: Enviar e-mail com link do convite
            # send_invite_email(invite)

            flash(f"Convite enviado para {email}!", "success")
        else:
            flash("Erro ao criar convite.", "danger")
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
    office = current_user.get_office()

    if not office:
        flash("Escritório não encontrado.", "danger")
        return redirect(url_for("office.create"))

    member = User.query.filter_by(id=member_id, office_id=office.id).first()

    if not member:
        flash("Membro não encontrado.", "danger")
        return redirect(url_for("office.members"))

    # Não pode alterar o role do owner
    if member.office_role == "owner":
        flash("Não é possível alterar a função do proprietário.", "danger")
        return redirect(url_for("office.members"))

    # Apenas owner pode promover alguém a admin
    new_role = request.form.get("role")
    if new_role == "admin" and not current_user.is_office_owner():
        flash("Apenas o proprietário pode promover membros a administrador.", "danger")
        return redirect(url_for("office.members"))

    if new_role in OFFICE_ROLES:
        member.office_role = new_role
        db.session.commit()
        flash(
            f"Função de {member.full_name or member.username} alterada para {OFFICE_ROLES[new_role]['name']}.",
            "success",
        )
    else:
        flash("Função inválida.", "danger")

    return redirect(url_for("office.members"))


@bp.route("/members/<int:member_id>/remove", methods=["POST"])
@login_required
@lawyer_required
@office_admin_required
def remove_member(member_id):
    """Remover membro do escritório"""
    office = current_user.get_office()

    if not office:
        flash("Escritório não encontrado.", "danger")
        return redirect(url_for("office.create"))

    member = User.query.filter_by(id=member_id, office_id=office.id).first()

    if not member:
        flash("Membro não encontrado.", "danger")
        return redirect(url_for("office.members"))

    # Não pode remover o owner
    if member.office_role == "owner":
        flash("Não é possível remover o proprietário do escritório.", "danger")
        return redirect(url_for("office.members"))

    # Admin só pode ser removido pelo owner
    if member.office_role == "admin" and not current_user.is_office_owner():
        flash("Apenas o proprietário pode remover administradores.", "danger")
        return redirect(url_for("office.members"))

    # Não pode remover a si mesmo
    if member.id == current_user.id:
        flash(
            "Você não pode se remover do escritório. Use 'Sair do Escritório' ao invés.",
            "warning",
        )
        return redirect(url_for("office.members"))

    # Remover membro
    member_name = member.full_name or member.username
    office.remove_member(member)
    db.session.commit()

    flash(f"{member_name} foi removido do escritório.", "success")
    return redirect(url_for("office.members"))


@bp.route("/invites/<int:invite_id>/cancel", methods=["POST"])
@login_required
@lawyer_required
@office_admin_required
def cancel_invite(invite_id):
    """Cancelar um convite pendente"""
    office = current_user.get_office()

    if not office:
        flash("Escritório não encontrado.", "danger")
        return redirect(url_for("office.create"))

    invite = OfficeInvite.query.filter_by(
        id=invite_id, office_id=office.id, status="pending"
    ).first()

    if not invite:
        flash("Convite não encontrado.", "danger")
        return redirect(url_for("office.members"))

    invite.cancel()
    db.session.commit()

    flash("Convite cancelado.", "success")
    return redirect(url_for("office.members"))


@bp.route("/invites/<int:invite_id>/resend", methods=["POST"])
@login_required
@lawyer_required
@office_admin_required
def resend_invite(invite_id):
    """Reenviar um convite"""
    office = current_user.get_office()

    if not office:
        flash("Escritório não encontrado.", "danger")
        return redirect(url_for("office.create"))

    invite = OfficeInvite.query.filter_by(
        id=invite_id, office_id=office.id, status="pending"
    ).first()

    if not invite:
        flash("Convite não encontrado.", "danger")
        return redirect(url_for("office.members"))

    invite.resend()
    db.session.commit()

    # TODO: Reenviar e-mail
    # send_invite_email(invite)

    flash(f"Convite reenviado para {invite.email}.", "success")
    return redirect(url_for("office.members"))


# =============================================================================
# Aceitar Convite
# =============================================================================


@bp.route("/invite/<token>")
@login_required
@lawyer_required
def accept_invite_page(token):
    """Página para aceitar convite"""
    invite = OfficeInvite.query.filter_by(token=token).first()

    if not invite:
        flash("Convite não encontrado ou inválido.", "danger")
        return redirect(url_for("main.index"))

    if not invite.is_valid():
        flash("Este convite expirou ou já foi utilizado.", "warning")
        return redirect(url_for("main.index"))

    # Verificar se o usuário atual é o destinatário
    if current_user.email.lower() != invite.email.lower():
        flash("Este convite foi enviado para outro e-mail.", "danger")
        return redirect(url_for("main.index"))

    # Se já está em outro escritório
    if current_user.office_id:
        flash(
            "Você já pertence a um escritório. Saia primeiro para aceitar este convite.",
            "warning",
        )
        return redirect(url_for("office.dashboard"))

    office = invite.office
    inviter = User.query.get(invite.invited_by_id)
    role_info = OFFICE_ROLES.get(invite.role, {})

    return render_template(
        "office/accept_invite.html",
        title="Aceitar Convite",
        invite=invite,
        office=office,
        inviter=inviter,
        role_info=role_info,
    )


@bp.route("/invite/<token>/accept", methods=["POST"])
@login_required
@lawyer_required
def accept_invite(token):
    """Aceitar convite para escritório"""
    invite = OfficeInvite.query.filter_by(token=token).first()

    if not invite or not invite.is_valid():
        flash("Convite inválido ou expirado.", "danger")
        return redirect(url_for("main.index"))

    if current_user.email.lower() != invite.email.lower():
        flash("Este convite foi enviado para outro e-mail.", "danger")
        return redirect(url_for("main.index"))

    if current_user.office_id:
        flash("Você já pertence a um escritório.", "warning")
        return redirect(url_for("office.dashboard"))

    # Verificar se o escritório ainda pode adicionar membros
    office = invite.office
    if not office.can_add_member():
        flash("O escritório atingiu o limite de membros.", "warning")
        return redirect(url_for("main.index"))

    # Aceitar convite
    if invite.accept(current_user):
        db.session.commit()
        flash(f"Bem-vindo ao escritório {office.name}!", "success")
        return redirect(url_for("office.dashboard"))
    else:
        flash("Erro ao aceitar convite.", "danger")
        return redirect(url_for("main.index"))


@bp.route("/invite/<token>/decline", methods=["POST"])
@login_required
def decline_invite(token):
    """Recusar convite"""
    invite = OfficeInvite.query.filter_by(token=token).first()

    if not invite:
        flash("Convite não encontrado.", "danger")
        return redirect(url_for("main.index"))

    if current_user.email.lower() != invite.email.lower():
        flash("Este convite foi enviado para outro e-mail.", "danger")
        return redirect(url_for("main.index"))

    invite.status = "declined"
    db.session.commit()

    flash("Convite recusado.", "info")
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

    # Obter membros elegíveis (exceto o owner atual)
    eligible_members = office.members.filter(
        User.id != current_user.id, User.is_active == True
    ).all()

    form.new_owner_id.choices = [
        (m.id, f"{m.full_name or m.username} ({m.email})") for m in eligible_members
    ]

    if not eligible_members:
        flash(
            "Não há outros membros elegíveis para transferir a propriedade.", "warning"
        )
        return redirect(url_for("office.dashboard"))

    if form.validate_on_submit():
        new_owner = User.query.get(form.new_owner_id.data)

        if new_owner and new_owner.office_id == office.id:
            office.transfer_ownership(new_owner)
            db.session.commit()

            flash(
                f"Propriedade transferida para {new_owner.full_name or new_owner.username}.",
                "success",
            )
            return redirect(url_for("office.dashboard"))
        else:
            flash("Usuário inválido para transferência.", "danger")

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
    office = current_user.get_office()

    if not office:
        flash("Escritório não encontrado.", "danger")
        return redirect(url_for("main.index"))

    # Owner não pode sair sem transferir propriedade
    if current_user.is_office_owner():
        flash(
            "Você é o proprietário. Transfira a propriedade antes de sair ou exclua o escritório.",
            "danger",
        )
        return redirect(url_for("office.dashboard"))

    office_name = office.name
    office.remove_member(current_user)
    db.session.commit()

    flash(f"Você saiu do escritório {office_name}.", "info")
    return redirect(url_for("main.index"))


@bp.route("/delete", methods=["POST"])
@login_required
@lawyer_required
@office_owner_required
def delete_office():
    """Excluir escritório"""
    office = current_user.get_office()

    if not office:
        flash("Escritório não encontrado.", "danger")
        return redirect(url_for("main.index"))

    # Verificar se há outros membros
    member_count = office.get_member_count()
    if member_count > 1:
        flash("Remova todos os membros antes de excluir o escritório.", "danger")
        return redirect(url_for("office.members"))

    office_name = office.name

    # Desvincular o owner
    current_user.office_id = None
    current_user.office_role = None

    # Excluir o escritório (cascata vai excluir convites)
    db.session.delete(office)
    db.session.commit()

    flash(f"Escritório '{office_name}' excluído com sucesso.", "info")
    return redirect(url_for("main.index"))

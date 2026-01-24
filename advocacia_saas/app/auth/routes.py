"""
Auth Routes - Rotas de Autenticação (Controllers).

Este módulo contém as rotas HTTP para autenticação, delegando a lógica
de negócio para os serviços especializados.
"""

from datetime import datetime, timezone
from io import BytesIO
from urllib.parse import urlparse

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask_login import current_user, login_required
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app import limiter
from app.auth import bp
from app.auth.forms import (
    ChangePasswordForm,
    LoginForm,
    ProfileForm,
    RegistrationForm,
    TwoFactorSetupForm,
    TwoFactorVerifyForm,
)
from app.auth.services import (
    AuthService,
    PasswordService,
    ProfileService,
    RegistrationService,
    TimezoneService,
    TwoFactorService,
)
from app.models import User
from app.rate_limits import LOGIN_LIMIT
from app.utils.audit import AuditManager

# =============================================================================
# MIDDLEWARE
# =============================================================================


@bp.before_app_request
def check_password_expiration():
    """
    Middleware que verifica se a senha do usuário expirou.
    Redireciona para mudança de senha se necessário.
    """
    exempt_endpoints = [
        "auth.login",
        "auth.logout",
        "auth.register",
        "auth.change_password",
        "static",
    ]

    if current_user.is_authenticated:
        # Master é isento de verificações
        if current_user.is_master:
            return

        if request.endpoint and request.endpoint not in exempt_endpoints:
            if PasswordService.is_password_change_required(current_user):
                flash("Sua senha expirou. Por favor, defina uma nova senha.", "warning")
                return redirect(url_for("auth.change_password"))

            elif current_user.should_show_password_warning():
                days_left = current_user.days_until_password_expires()
                flash(
                    f"Sua senha expira em {days_left} dia(s). "
                    f"<a href='{url_for('auth.change_password')}' class='alert-link'>Altere agora</a> "
                    f"para manter sua conta segura.",
                    "info",
                )


# =============================================================================
# LOGIN / LOGOUT / REGISTER
# =============================================================================


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit(LOGIN_LIMIT, exempt_when=lambda: current_user.is_authenticated)
def login():
    """Página de login."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        try:
            result = AuthService.attempt_login(
                email=form.email.data,
                password=form.password.data,
                remember_me=form.remember_me.data,
                two_factor_code=form.two_factor_code.data,
            )

            if result.requires_2fa:
                # Precisa fornecer código 2FA
                if result.two_factor_method == "email":
                    flash(
                        "Código de autenticação enviado para seu email. Digite-o abaixo.",
                        "info",
                    )
                else:
                    flash(
                        "Este usuário requer autenticação de dois fatores. Digite o código 2FA.",
                        "warning",
                    )
                return render_template(
                    "auth/login.html",
                    title="Login",
                    form=form,
                    require_2fa=True,
                    user_email=result.user.email if result.user else None,
                    two_factor_method=result.two_factor_method,
                )

            if not result.success:
                flash(result.error_message, "error")
                return render_template("auth/login.html", title="Login", form=form)

            # Login bem-sucedido
            if result.is_demo:
                flash(
                    "Login realizado com usuário demo (dados não salvos no banco)",
                    "info",
                )
            elif result.user.is_master:
                flash("Login realizado com sucesso (usuário master)", "success")

            if result.is_password_expired:
                flash("Sua senha expirou. Por favor, defina uma nova senha.", "warning")
                return redirect(url_for("auth.change_password"))

            next_page = request.args.get("next")
            if not next_page or urlparse(next_page).netloc != "":
                next_page = url_for("main.dashboard")
            return redirect(next_page)

        except Exception as e:
            current_app.logger.error(f"Erro durante login: {str(e)}", exc_info=True)
            from app.utils.error_messages import format_error_for_user

            error_msg = str(e).lower()
            if "database" in error_msg or "sql" in error_msg:
                error_type = "database"
            elif "permission" in error_msg:
                error_type = "permission"
            else:
                error_type = "general"

            flash(format_error_for_user(e, error_type), "error")

    return render_template("auth/login.html", title="Login", form=form)


@bp.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per hour")
def register():
    """Página de registro."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    plan_id = request.args.get("plan", type=int)
    form = RegistrationForm()

    if form.validate_on_submit():
        result = RegistrationService.register_user(
            username=form.username.data,
            email=form.email.data,
            full_name=form.full_name.data,
            password=form.password.data,
            oab_number=form.oab_number.data,
            phone=form.phone.data,
            cep=form.cep.data,
            street=form.street.data,
            number=form.number.data,
            uf=form.uf.data,
            city=form.city.data,
            neighborhood=form.neighborhood.data,
            complement=form.complement.data,
            user_type=form.user_type.data,
            specialties=form.specialties.data
            if form.user_type.data == "advogado"
            else None,
            consent_personal_data=form.consent_personal_data.data,
            consent_marketing=form.consent_marketing.data,
            consent_terms=form.consent_terms.data,
            plan_id=plan_id,
        )

        if result.was_referred:
            flash(
                f"Cadastro realizado com sucesso! Você foi indicado e ganhará créditos bônus ao assinar. "
                f"Você tem {result.trial_days} dias gratuitos para testar o sistema.",
                "success",
            )
        else:
            flash(
                f"Cadastro realizado com sucesso! Você tem {result.trial_days} dias gratuitos para testar o sistema.",
                "success",
            )

        if plan_id:
            flash("Complete o pagamento para ativar seu plano.", "info")
            return redirect(
                url_for("checkout.create_checkout_session", plan_id=plan_id)
            )

        return redirect(url_for("main.dashboard"))

    return render_template(
        "auth/register.html", title="Cadastro", form=form, plan_id=plan_id
    )


@bp.route("/logout")
@login_required
def logout():
    """Realiza logout do usuário."""
    AuthService.logout(current_user)
    return redirect(url_for("main.index"))


# =============================================================================
# PROFILE
# =============================================================================


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """Página de perfil do usuário."""
    is_demo = current_user.id == 999999
    form = ProfileForm(current_user.email, current_user.user_type)

    if form.validate_on_submit():
        success, error = ProfileService.update_profile(
            user=current_user,
            full_name=form.full_name.data,
            email=form.email.data,
            oab_number=form.oab_number.data,
            phone=form.phone.data,
            cep=form.cep.data,
            street=form.street.data,
            number=form.number.data,
            uf=form.uf.data,
            city=form.city.data,
            neighborhood=form.neighborhood.data,
            complement=form.complement.data,
            specialties=form.specialties.data,
            quick_actions=form.quick_actions.data,
        )

        if success:
            flash("Perfil atualizado com sucesso!", "success")
        else:
            flash(error, "warning")

        return redirect(url_for("auth.profile"))

    elif request.method == "GET":
        form.full_name.data = current_user.full_name
        form.email.data = current_user.email
        form.oab_number.data = current_user.oab_number
        form.phone.data = current_user.phone
        form.cep.data = current_user.cep
        form.street.data = current_user.street
        form.number.data = current_user.number
        form.uf.data = current_user.uf
        form.city.data = current_user.city
        form.neighborhood.data = current_user.neighborhood
        form.complement.data = current_user.complement
        form.specialties.data = current_user.get_specialties()
        form.quick_actions.data = current_user.get_quick_actions()

    return render_template(
        "auth/profile.html", title="Perfil", form=form, is_demo=is_demo
    )


@bp.route("/upload_logo", methods=["POST"])
@login_required
def upload_logo():
    """Upload do logo do usuário."""
    file = request.files.get("logo")
    success, message = ProfileService.upload_logo(current_user, file)

    if success:
        flash(message, "success")
    else:
        flash(message, "error")

    return redirect(url_for("auth.profile"))


# =============================================================================
# PASSWORD
# =============================================================================


@bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    """Página para mudança de senha do usuário."""
    form = ChangePasswordForm()
    is_forced = PasswordService.is_password_change_required(current_user)

    if form.validate_on_submit():
        success, message = PasswordService.change_password(
            current_user, form.current_password.data, form.new_password.data
        )

        if success:
            flash(message, "success")
            return redirect(url_for("main.dashboard"))
        else:
            flash(message, "error")

    return render_template(
        "auth/change_password.html",
        title="Alterar Senha",
        form=form,
        is_forced=is_forced,
        days_left=current_user.days_until_password_expires(),
    )


# =============================================================================
# TIMEZONE
# =============================================================================


@bp.route("/update_timezone", methods=["POST"])
@login_required
def update_timezone():
    """Atualiza o fuso horário do usuário."""
    timezone_str = request.form.get("timezone")

    if timezone_str:
        success, message = TimezoneService.update_timezone(current_user, timezone_str)
        flash(message, "success" if success else "error")
    else:
        flash("Fuso horário não fornecido.", "error")

    return redirect(request.referrer or url_for("auth.profile"))


# =============================================================================
# TWO-FACTOR AUTHENTICATION (2FA)
# =============================================================================


@bp.route("/2fa/setup", methods=["GET", "POST"])
@login_required
def setup_2fa():
    """Configurar 2FA para o usuário."""
    from app.services import EmailService, generate_email_2fa_code

    if not TwoFactorService.can_use_2fa(current_user):
        flash("2FA não está disponível para seu tipo de usuário.", "error")
        return redirect(url_for("auth.profile"))

    if current_user.two_factor_enabled:
        flash("2FA já está habilitado para sua conta.", "info")
        return redirect(url_for("auth.profile"))

    form = TwoFactorSetupForm()
    totp_uri = None
    qr_code_data = None

    if form.validate_on_submit():
        method = form.method.data

        if method == "email":
            code = generate_email_2fa_code()
            current_user.email_2fa_code = code

            from datetime import timedelta

            from app import db

            current_user.email_2fa_code_expires = datetime.now(
                timezone.utc
            ) + timedelta(minutes=10)
            db.session.commit()

            if EmailService.send_2fa_code_email(
                current_user.email, code, method="email"
            ):
                flash(
                    f"Código enviado para {current_user.email}. Verifique seu email.",
                    "info",
                )
                session["pending_2fa_method"] = "email"
                return render_template(
                    "auth/verify_2fa_setup.html",
                    form=form,
                    method="email",
                    email=current_user.email,
                )
            else:
                flash("Erro ao enviar código. Tente novamente.", "error")
                return render_template("auth/setup_2fa.html", form=form)

        # Para TOTP - Verificar código
        if current_user.verify_2fa_code(form.verification_code.data):
            backup_codes = TwoFactorService.enable_2fa(current_user, method)
            session["backup_codes"] = backup_codes
            flash("2FA habilitado com sucesso!", "success")
            return redirect(url_for("auth.show_backup_codes"))
        else:
            flash("Código de verificação inválido.", "error")

    # Preparar dados para TOTP
    if form.method.data == "totp" or not form.method.data:
        totp_uri, qr_code_data = TwoFactorService.generate_totp_setup(current_user)

    return render_template(
        "auth/setup_2fa.html", form=form, totp_uri=totp_uri, qr_code_data=qr_code_data
    )


@bp.route("/2fa/show-backup-codes")
@login_required
def show_backup_codes():
    """Mostrar códigos de backup após configurar 2FA."""
    if not current_user.two_factor_enabled:
        return redirect(url_for("auth.profile"))

    backup_codes = session.pop("backup_codes", None)
    if not backup_codes:
        backup_codes = current_user.get_backup_codes()

    return render_template("auth/backup_codes.html", backup_codes=backup_codes)


@bp.route("/2fa/manage")
@login_required
def manage_2fa():
    """Página para gerenciar configurações de 2FA."""
    return render_template("auth/manage_2fa.html")


@bp.route("/2fa/disable", methods=["POST"])
@login_required
def disable_2fa():
    """Desabilitar 2FA."""
    if not current_user.two_factor_enabled:
        flash("2FA não está habilitado.", "error")
        return redirect(url_for("auth.profile"))

    TwoFactorService.disable_2fa(current_user)
    flash("2FA desabilitado com sucesso.", "success")
    return redirect(url_for("auth.profile"))


@bp.route("/2fa/regenerate-codes", methods=["POST"])
@login_required
def regenerate_backup_codes():
    """Regenerar códigos de recuperação."""
    if not current_user.two_factor_enabled:
        flash("2FA não está habilitado.", "error")
        return redirect(url_for("auth.profile"))

    backup_codes = TwoFactorService.regenerate_backup_codes(current_user)
    session["backup_codes"] = backup_codes

    flash("Códigos de recuperação regenerados com sucesso!", "success")
    return redirect(url_for("auth.show_backup_codes"))


@bp.route("/2fa/download-codes")
@login_required
def download_backup_codes():
    """Download dos códigos de recuperação em PDF."""
    if not current_user.two_factor_enabled:
        flash("2FA não está habilitado.", "error")
        return redirect(url_for("auth.profile"))

    backup_codes = current_user.get_backup_codes()
    if not backup_codes:
        flash("Nenhum código de recuperação disponível.", "error")
        return redirect(url_for("auth.profile"))

    # Registrar auditoria
    AuditManager.log_change(
        entity_type="user",
        entity_id=current_user.id,
        action="2fa_backup_codes_downloaded",
        description="Códigos de recuperação 2FA baixados em PDF",
        additional_metadata={"ip_address": request.remote_addr},
    )

    # Criar PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=24,
        textColor=colors.HexColor("#1e40af"),
        spaceAfter=30,
        alignment=1,
    )

    elements.append(Paragraph("Códigos de Recuperação - 2FA", title_style))
    elements.append(Spacer(1, 0.3 * inch))

    info_style = ParagraphStyle(
        "Info",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#666666"),
        spaceAfter=20,
    )

    user_info = (
        f"<b>Usuário:</b> {current_user.email}<br/>"
        f"<b>Data:</b> {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M:%S')}<br/>"
        f"<b>Sistema:</b> Petitio"
    )
    elements.append(Paragraph(user_info, info_style))
    elements.append(Spacer(1, 0.2 * inch))

    warning_style = ParagraphStyle(
        "Warning",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#b91c1c"),
        spaceAfter=20,
    )

    warning = (
        "<b>⚠️ IMPORTANTE:</b> Armazene estes códigos em um local seguro. "
        "Use um código quando não conseguir acessar seu autenticador. "
        "Cada código só pode ser usado uma vez."
    )
    elements.append(Paragraph(warning, warning_style))
    elements.append(Spacer(1, 0.3 * inch))

    codes_data = [["Código de Recuperação"]]
    for i, code in enumerate(backup_codes, 1):
        codes_data.append([f"{i}. {code}"])

    table = Table(codes_data, colWidths=[5 * inch])
    table_style = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e40af")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 12),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f3f4f6")),
            ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#d1d5db")),
            ("FONTNAME", (0, 1), (-1, -1), "Courier"),
            ("FONTSIZE", (0, 1), (-1, -1), 10),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [colors.white, colors.HexColor("#f9fafb")],
            ),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]
    )
    table.setStyle(table_style)
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"backup-codes-2fa-{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf",
    )


@bp.route("/2fa/verify", methods=["GET", "POST"])
def verify_2fa():
    """Página para verificar 2FA durante login."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    user_email = request.args.get("email")
    if not user_email:
        return redirect(url_for("auth.login"))

    user = User.query.filter_by(email=user_email).first()
    if not user or not user.requires_2fa():
        return redirect(url_for("auth.login"))

    form = TwoFactorVerifyForm()
    if form.validate_on_submit():
        if user.verify_2fa_code(form.code.data):
            from flask_login import login_user

            login_user(user)
            next_page = request.args.get("next")
            if not next_page or urlparse(next_page).netloc != "":
                next_page = url_for("main.dashboard")
            return redirect(next_page)
        else:
            flash("Código 2FA inválido.", "error")

    return render_template("auth/verify_2fa.html", form=form, user_email=user_email)


# =============================================================================
# NOTIFICATION SETTINGS
# =============================================================================


@bp.route("/settings/notifications", methods=["GET", "POST"])
@login_required
def notification_settings():
    """Configurações de notificações do usuário."""
    from app import db

    if request.method == "POST":
        # Validar e sanitizar inputs
        try:
            alert_days = int(request.form.get("deadline_alert_days", 10))
            alert_days = max(1, min(30, alert_days))  # Entre 1 e 30 dias
        except (ValueError, TypeError):
            alert_days = 10

        # Atualizar configurações
        current_user.deadline_alert_days = alert_days
        current_user.deadline_alert_enabled = "deadline_alert_enabled" in request.form
        current_user.deadline_alert_email = "deadline_alert_email" in request.form
        current_user.deadline_alert_push = "deadline_alert_push" in request.form

        db.session.commit()
        flash("Configurações de notificação atualizadas com sucesso!", "success")
        return redirect(url_for("auth.notification_settings"))

    return render_template(
        "auth/notification_settings.html",
        title="Configurações de Notificação",
    )

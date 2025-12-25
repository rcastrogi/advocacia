import os
from urllib.parse import urlparse
import json

from flask import current_app, flash, redirect, render_template, request, url_for, session
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.utils import secure_filename

from app import db, limiter
from app.auth import bp
from app.auth.forms import ChangePasswordForm, LoginForm, ProfileForm, RegistrationForm, TwoFactorSetupForm, TwoFactorVerifyForm
from app.models import User


@bp.before_app_request
def check_password_expiration():
    """
    Middleware que verifica se a senha do usuário expirou.
    Redireciona para mudança de senha se necessário.
    """
    # Ignorar verificação para rotas públicas e de autenticação
    exempt_endpoints = [
        "auth.login",
        "auth.logout",
        "auth.register",
        "auth.change_password",
        "static",
    ]

    # Verificar apenas se usuário está autenticado
    if current_user.is_authenticated:
        # Não verificar na própria página de mudança de senha
        if request.endpoint and request.endpoint not in exempt_endpoints:
            # Verificar se senha expirou ou se mudança é forçada
            if current_user.force_password_change or current_user.is_password_expired():
                flash("Sua senha expirou. Por favor, defina uma nova senha.", "warning")
                return redirect(url_for("auth.change_password"))

            # Mostrar aviso se senha está próxima de expirar (últimos 7 dias)
            elif current_user.should_show_password_warning():
                days_left = current_user.days_until_password_expires()
                flash(
                    f"Sua senha expira em {days_left} dia(s). "
                    f"<a href='{url_for('auth.change_password')}' class='alert-link'>Altere agora</a> "
                    f"para manter sua conta segura.",
                    "info",
                )


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")  # Limita a 10 tentativas por minuto
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        # Detecta rapidamente se já existe um admin real; evita bloquear login normal
        real_admin_exists = False
        try:
            real_admin_exists = (
                User.query.filter_by(user_type="master").first() is not None
            )
        except Exception:
            pass

        # DEMO: Credenciais hardcoded para testes (não usa banco de dados)
        # Email: admin@advocaciasaas.com | Senha: admin123
        if (
            form.email.data == "admin@advocaciasaas.com"
            and form.password.data == "admin123"
            and not real_admin_exists
        ):
            from datetime import datetime, timedelta

            # Criar usuário demo em memória (não persiste no banco)
            from app.models import _demo_user_cache

            demo_user = User(
                id=999999,
                username="admin_demo",
                email="admin@advocaciasaas.com",
                full_name="Administrador Demo",
                user_type="master",
                is_active=True,
            )
            # Configurar campos de segurança para evitar expiração
            demo_user.created_at = datetime.now(timezone.utc)
            demo_user.password_changed_at = datetime.now(timezone.utc)
            demo_user.password_expires_at = datetime.now(timezone.utc) + timedelta(days=9999)
            demo_user.password_history = "[]"
            demo_user.force_password_change = False
            try:
                demo_user.set_password("admin123", skip_history_check=True)
            except TypeError:
                demo_user.set_password("admin123")

            # Armazenar no cache para o load_user encontrar
            _demo_user_cache[999999] = demo_user

            login_user(demo_user, remember=form.remember_me.data)
            flash(
                "Login realizado com usuário demo (dados não salvos no banco)", "info"
            )
            next_page = request.args.get("next")
            if not next_page or urlparse(next_page).netloc != "":
                next_page = url_for("main.dashboard")
            return redirect(next_page)

        # Fluxo normal: consultar banco de dados para outros usuários
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            # Verificar se usuário requer 2FA
            if user.requires_2fa():
                # Verificar código 2FA
                if not form.two_factor_code.data:
                    flash("Este usuário requer autenticação de dois fatores. Digite o código 2FA.", "warning")
                    return render_template("auth/login.html", title="Login", form=form, require_2fa=True, user_email=user.email)

                if not user.verify_2fa_code(form.two_factor_code.data):
                    flash("Código 2FA inválido", "error")
                    return render_template("auth/login.html", title="Login", form=form, require_2fa=True, user_email=user.email)

            login_user(user, remember=form.remember_me.data)

            # Verificar se senha expirou imediatamente após login
            if user.force_password_change or user.is_password_expired():
                flash("Sua senha expirou. Por favor, defina uma nova senha.", "warning")
                return redirect(url_for("auth.change_password"))

            next_page = request.args.get("next")
            if not next_page or urlparse(next_page).netloc != "":
                next_page = url_for("main.dashboard")
            return redirect(next_page)
        flash("Email ou senha inválidos", "error")
    return render_template("auth/login.html", title="Login", form=form)


@bp.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per hour")  # Limita a 5 registros por hora
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    # Capture plan_id from query parameters
    plan_id = request.args.get("plan", type=int)

    form = RegistrationForm()
    if form.validate_on_submit():
        # Set billing status based on whether a plan was selected
        billing_status = "pending_payment" if plan_id else "active"

        user = User(
            username=form.username.data,
            email=form.email.data,
            full_name=form.full_name.data,
            oab_number=form.oab_number.data,
            phone=form.phone.data,
            # Address fields
            cep=form.cep.data,
            street=form.street.data,
            number=form.number.data,
            uf=form.uf.data,
            city=form.city.data,
            neighborhood=form.neighborhood.data,
            complement=form.complement.data,
            user_type=form.user_type.data,
            billing_status=billing_status,
        )
        user.set_password(form.password.data)

        # Salvar especialidades se for advogado
        if form.user_type.data == "advogado" and form.specialties.data:
            user.set_specialties(form.specialties.data)

        db.session.add(user)
        db.session.commit()

        # Processar consentimentos LGPD
        from app.models import DataConsent, DataProcessingLog

        # Consentimento para dados pessoais (obrigatório)
        if form.consent_personal_data.data:
            personal_consent = DataConsent(
                user_id=user.id,
                consent_type="personal_data",
                consent_purpose="Prestação de serviços da plataforma Petitio, incluindo criação de petições, gestão de clientes e funcionalidades do sistema.",
                consent_version="1.0",
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent"),
                consent_method="registration_form",
            )
            db.session.add(personal_consent)

            # Log de processamento
            log = DataProcessingLog(
                user_id=user.id,
                action="user_registration",
                data_category="personal_data",
                purpose="service_provision",
                legal_basis="LGPD Art. 7º, V (consentimento)",
                endpoint=request.path,
                additional_data=json.dumps({
                    "user_type": form.user_type.data,
                    "registration_method": "web_form"
                })
            )
            db.session.add(log)

        # Consentimento para marketing (opcional)
        if form.consent_marketing.data:
            marketing_consent = DataConsent(
                user_id=user.id,
                consent_type="marketing",
                consent_purpose="Envio de comunicações de marketing, newsletters e informações sobre novos recursos e atualizações da plataforma.",
                consent_version="1.0",
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent"),
                consent_method="registration_form",
            )
            db.session.add(marketing_consent)

            # Log de processamento
            log = DataProcessingLog(
                user_id=user.id,
                action="marketing_consent_given",
                data_category="contact_data",
                purpose="marketing_communications",
                legal_basis="LGPD Art. 7º, V (consentimento)",
                endpoint=request.path,
            )
            db.session.add(log)

        # Consentimento para termos (obrigatório)
        if form.consent_terms.data:
            terms_consent = DataConsent(
                user_id=user.id,
                consent_type="terms_acceptance",
                consent_purpose="Aceitação dos Termos de Uso e Política de Privacidade da plataforma Petitio.",
                consent_version="1.0",
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent"),
                consent_method="registration_form",
            )
            db.session.add(terms_consent)

        db.session.commit()

        # Iniciar período de trial automaticamente para novos usuários
        from flask import current_app

        trial_days = current_app.config.get("DEFAULT_TRIAL_DAYS", 3)
        user.start_trial(trial_days)
        db.session.commit()

        # Auto-login the new user
        login_user(user)

        flash(
            f"Cadastro realizado com sucesso! Você tem {trial_days} dias gratuitos para testar o sistema.",
            "success",
        )

        # If a plan was selected, redirect to checkout
        if plan_id:
            flash("Complete o pagamento para ativar seu plano.", "info")
            return redirect(
                url_for("checkout.create_checkout_session", plan_id=plan_id)
            )

        # Otherwise, go to dashboard
        return redirect(url_for("main.dashboard"))

    return render_template(
        "auth/register.html", title="Cadastro", form=form, plan_id=plan_id
    )


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    # Verificar se é usuário demo
    is_demo = current_user.id == 999999

    form = ProfileForm(current_user.email)
    if form.validate_on_submit():
        if is_demo:
            flash(
                "Não é possível editar o perfil do usuário demo. Os dados não são salvos no banco.",
                "warning",
            )
            return redirect(url_for("auth.profile"))

        current_user.full_name = form.full_name.data
        current_user.email = form.email.data
        current_user.oab_number = form.oab_number.data
        current_user.phone = form.phone.data
        # Address fields
        current_user.cep = form.cep.data
        current_user.street = form.street.data
        current_user.number = form.number.data
        current_user.uf = form.uf.data
        current_user.city = form.city.data
        current_user.neighborhood = form.neighborhood.data
        current_user.complement = form.complement.data
        current_user.set_specialties(form.specialties.data)
        current_user.set_quick_actions(form.quick_actions.data)
        db.session.commit()
        flash("Perfil atualizado com sucesso!", "success")
        return redirect(url_for("auth.profile"))
    elif request.method == "GET":
        form.full_name.data = current_user.full_name
        form.email.data = current_user.email
        form.oab_number.data = current_user.oab_number
        form.phone.data = current_user.phone
        # Address fields
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
    # Verificar se é usuário demo
    if current_user.id == 999999:
        flash("Não é possível fazer upload de logo para o usuário demo.", "warning")
        return redirect(url_for("auth.profile"))

    if "logo" not in request.files:
        flash("Nenhum arquivo selecionado", "error")
        return redirect(url_for("auth.profile"))

    file = request.files["logo"]
    if file.filename == "":
        flash("Nenhum arquivo selecionado", "error")
        return redirect(url_for("auth.profile"))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Add user id to filename to avoid conflicts
        name, ext = os.path.splitext(filename)
        filename = f"{current_user.id}_{name}{ext}"

        file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)

        # Remove old logo if exists
        if current_user.logo_filename:
            old_path = os.path.join(
                current_app.config["UPLOAD_FOLDER"], current_user.logo_filename
            )
            if os.path.exists(old_path):
                os.remove(old_path)

        current_user.logo_filename = filename
        db.session.commit()
        flash("Logo atualizado com sucesso!", "success")
    else:
        flash("Formato de arquivo não permitido. Use PNG, JPG ou JPEG.", "error")

    return redirect(url_for("auth.profile"))


def allowed_file(filename):
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    """Rota para mudança de senha do usuário"""
    form = ChangePasswordForm()

    # Verificar se é uma mudança forçada
    is_forced = current_user.force_password_change or current_user.is_password_expired()

    if form.validate_on_submit():
        # Verificar senha atual
        if not current_user.check_password(form.current_password.data):
            flash("Senha atual incorreta.", "error")
            return render_template(
                "auth/change_password.html",
                title="Alterar Senha",
                form=form,
                is_forced=is_forced,
            )

        # Tentar definir nova senha
        try:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash("Senha alterada com sucesso!", "success")
            return redirect(url_for("main.dashboard"))
        except ValueError as e:
            flash(str(e), "error")
            return render_template(
                "auth/change_password.html",
                title="Alterar Senha",
                form=form,
                is_forced=is_forced,
            )

    return render_template(
        "auth/change_password.html",
        title="Alterar Senha",
        form=form,
        is_forced=is_forced,
        days_left=current_user.days_until_password_expires(),
    )


@bp.route("/update_timezone", methods=["POST"])
@login_required
def update_timezone():
    """Update user's timezone preference"""
    timezone = request.form.get("timezone")

    if timezone:
        # Validate timezone
        import pytz

        try:
            pytz.timezone(timezone)
            current_user.timezone = timezone
            db.session.commit()
            flash("Fuso horário atualizado com sucesso!", "success")
        except pytz.exceptions.UnknownTimeZoneError:
            flash("Fuso horário inválido.", "error")
    else:
        flash("Fuso horário não fornecido.", "error")

    return redirect(request.referrer or url_for("auth.profile"))


# =============================================================================
# TWO-FACTOR AUTHENTICATION (2FA) ROUTES
# =============================================================================

@bp.route("/2fa/setup", methods=["GET", "POST"])
@login_required
def setup_2fa():
    """Configurar 2FA para o usuário"""
    # Verificar se usuário pode usar 2FA (apenas admin e advogados)
    if not current_user.requires_2fa() and not current_user.is_admin():
        flash("2FA não está disponível para seu tipo de usuário.", "error")
        return redirect(url_for("auth.profile"))

    if current_user.two_factor_enabled:
        flash("2FA já está habilitado para sua conta.", "info")
        return redirect(url_for("auth.profile"))

    form = TwoFactorSetupForm()
    totp_uri = None
    qr_code_data = None

    if form.validate_on_submit():
        # Verificar código de verificação
        if current_user.verify_2fa_code(form.verification_code.data):
            # Habilitar 2FA
            backup_codes = current_user.enable_2fa(form.method.data)
            flash("2FA habilitado com sucesso!", "success")

            # Mostrar códigos de backup
            session['backup_codes'] = backup_codes
            return redirect(url_for("auth.show_backup_codes"))
        else:
            flash("Código de verificação inválido.", "error")

    # Preparar dados para TOTP
    if form.method.data == "totp" or not form.method.data:
        # Gerar chave secreta temporária para preview
        import pyotp
        temp_secret = pyotp.random_base32()
        totp = pyotp.TOTP(temp_secret)
        totp_uri = totp.provisioning_uri(name=current_user.email, issuer_name="Petitio")

        # Gerar dados do QR code
        import qrcode
        import io
        import base64

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        # Converter para base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_code_data = base64.b64encode(buffer.getvalue()).decode()

    return render_template("auth/setup_2fa.html", form=form, totp_uri=totp_uri, qr_code_data=qr_code_data)


@bp.route("/2fa/show-backup-codes")
@login_required
def show_backup_codes():
    """Mostrar códigos de backup após configurar 2FA"""
    if not current_user.two_factor_enabled:
        return redirect(url_for("auth.profile"))

    backup_codes = session.pop('backup_codes', None)
    if not backup_codes:
        backup_codes = current_user.get_backup_codes()

    return render_template("auth/backup_codes.html", backup_codes=backup_codes)


@bp.route("/2fa/disable", methods=["POST"])
@login_required
def disable_2fa():
    """Desabilitar 2FA"""
    if not current_user.two_factor_enabled:
        flash("2FA não está habilitado.", "error")
        return redirect(url_for("auth.profile"))

    current_user.disable_2fa()
    flash("2FA desabilitado com sucesso.", "success")
    return redirect(url_for("auth.profile"))


@bp.route("/2fa/verify", methods=["GET", "POST"])
def verify_2fa():
    """Página para verificar 2FA durante login"""
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
            login_user(user)
            next_page = request.args.get("next")
            if not next_page or urlparse(next_page).netloc != "":
                next_page = url_for("main.dashboard")
            return redirect(next_page)
        else:
            flash("Código 2FA inválido.", "error")

    return render_template("auth/verify_2fa.html", form=form, user_email=user_email)

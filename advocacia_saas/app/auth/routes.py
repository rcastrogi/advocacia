import json
import os
from datetime import datetime, timezone
from urllib.parse import urlparse

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.utils import secure_filename

from app import db, limiter
from app.auth import bp
from app.auth.forms import (
    ChangePasswordForm,
    LoginForm,
    ProfileForm,
    RegistrationForm,
    TwoFactorSetupForm,
    TwoFactorVerifyForm,
)
from app.decorators import validate_with_schema
from app.models import User
from app.rate_limits import LOGIN_LIMIT
from app.schemas import UserSchema
from app.utils.audit import AuditManager


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
        # 🔥 USUÁRIOS MASTER SÃO ISENTOS DE TODAS AS VERIFICAÇÕES DE SEGURANÇA 🔥
        if current_user.is_master:
            return  # Master tem acesso irrestrito

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
@limiter.limit(LOGIN_LIMIT, exempt_when=lambda: current_user.is_authenticated)
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        try:
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
                from datetime import datetime, timedelta, timezone

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
                demo_user.password_expires_at = datetime.now(timezone.utc) + timedelta(
                    days=9999
                )
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
                    "Login realizado com usuário demo (dados não salvos no banco)",
                    "info",
                )
                # Log de auditoria para login demo
                AuditManager.log_login(demo_user, success=True)
                next_page = request.args.get("next")
                if not next_page or urlparse(next_page).netloc != "":
                    next_page = url_for("main.dashboard")
                return redirect(next_page)

            # Fluxo normal: consultar banco de dados para outros usuários
            user = User.query.filter_by(email=form.email.data).first()
            if user and user.check_password(form.password.data):
                # 🔥 PROTEÇÃO ESPECIAL PARA USUÁRIO MASTER 🔥
                # Usuários master NUNCA são bloqueados e sempre podem fazer login
                if user.is_master:
                    # Master bypassa todas as verificações de segurança
                    login_user(user, remember=form.remember_me.data)
                    flash("Login realizado com sucesso (usuário master)", "success")
                    # Log de auditoria para login master
                    AuditManager.log_login(user, success=True)
                    next_page = request.args.get("next")
                    if not next_page or urlparse(next_page).netloc != "":
                        next_page = url_for("main.dashboard")
                    return redirect(next_page)

                # 🔥 PROTEÇÃO CONTRA USUÁRIOS INATIVOS 🔥
                # Usuários normais devem estar ativos para fazer login
                if not user.is_active:
                    flash(
                        "Sua conta foi desativada. Entre em contato com o administrador.",
                        "error",
                    )
                    return render_template("auth/login.html", title="Login", form=form)

                # Verificar se usuário requer 2FA
                if user.requires_2fa():
                    # ⏱️ Verificar se está bloqueado por múltiplas tentativas
                    if user.is_2fa_locked():
                        flash(
                            "Muitas tentativas falhadas de 2FA. Tente novamente em 15 minutos.",
                            "error",
                        )
                        # Log de auditoria
                        AuditManager.log_change(
                            entity_type="user",
                            entity_id=user.id,
                            action="2fa_locked",
                            description=f"Usuário bloqueado por múltiplas tentativas de 2FA",
                        )
                        return render_template(
                            "auth/login.html", title="Login", form=form
                        )

                    # Se 2FA por email, enviar código automaticamente
                    if user.two_factor_method == "email":
                        user.send_2fa_email_code()
                        flash(
                            "Código de autenticação enviado para seu email. Digite-o abaixo.",
                            "info",
                        )

                    # Verificar código 2FA
                    if not form.two_factor_code.data:
                        flash(
                            "Este usuário requer autenticação de dois fatores. Digite o código 2FA.",
                            "warning",
                        )
                        return render_template(
                            "auth/login.html",
                            title="Login",
                            form=form,
                            require_2fa=True,
                            user_email=user.email,
                            two_factor_method=user.two_factor_method,
                        )

                    if not user.verify_2fa_code(form.two_factor_code.data):
                        # ❌ Tentativa falhada - incrementar contador
                        user.record_2fa_failed_attempt()

                        flash("Código 2FA inválido", "error")
                        # Log de auditoria
                        AuditManager.log_change(
                            entity_type="user",
                            entity_id=user.id,
                            action="2fa_failed_attempt",
                            description=f"Tentativa falha de 2FA (tentativa {user.two_factor_failed_attempts})",
                        )

                        return render_template(
                            "auth/login.html",
                            title="Login",
                            form=form,
                            require_2fa=True,
                            user_email=user.email,
                            two_factor_method=user.two_factor_method,
                        )

                    # ✅ 2FA bem-sucedido - resetar contador
                    user.reset_2fa_failed_attempts()
                    # Log de auditoria
                    AuditManager.log_change(
                        entity_type="user",
                        entity_id=user.id,
                        action="2fa_success",
                        description=f"Login bem-sucedido com 2FA",
                    )

                login_user(user, remember=form.remember_me.data)

                # 🔥 USUÁRIOS MASTER NÃO SÃO AFETADOS POR EXPIRAÇÃO DE SENHA 🔥
                if not user.is_master and (
                    user.force_password_change or user.is_password_expired()
                ):
                    flash(
                        "Sua senha expirou. Por favor, defina uma nova senha.",
                        "warning",
                    )
                    return redirect(url_for("auth.change_password"))

                # Log de auditoria para login bem-sucedido
                AuditManager.log_login(user, success=True)

                next_page = request.args.get("next")
                if not next_page or urlparse(next_page).netloc != "":
                    next_page = url_for("main.dashboard")
                return redirect(next_page)
            flash("Email ou senha inválidos", "error")
            # Log de auditoria para login falhado
            AuditManager.log_change(
                entity_type="user",
                entity_id=0,  # ID genérico para tentativas de login
                action="login_failed",
                description=f"Tentativa de login falhada - Email: {form.email.data}",
                additional_metadata={"email_attempted": form.email.data},
            )
        except Exception as e:
            # Registrar erro detalhado
            current_app.logger.error(f"Erro durante login: {str(e)}", exc_info=True)

            # Importar helper de mensagens de erro
            from app.utils.error_messages import format_error_for_user

            # Determinar tipo de erro
            error_msg = str(e).lower()
            if "database" in error_msg or "sql" in error_msg:
                error_type = "database"
            elif "permission" in error_msg:
                error_type = "permission"
            else:
                error_type = "general"

            # Exibir erro real ou genérico baseado na configuração
            user_message = format_error_for_user(e, error_type)
            flash(user_message, "error")
            return render_template("auth/login.html", title="Login", form=form)
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
                additional_data=json.dumps(
                    {
                        "user_type": form.user_type.data,
                        "registration_method": "web_form",
                    }
                ),
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
    # Log de auditoria para logout
    AuditManager.log_logout(current_user)
    logout_user()
    # Limpar session para evitar carregar mensagens antigas
    session.clear()
    return redirect(url_for("main.index"))


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    # Verificar se é usuário demo
    is_demo = current_user.id == 999999

    form = ProfileForm(current_user.email, current_user.user_type)
    if form.validate_on_submit():
        if is_demo:
            flash(
                "Não é possível editar o perfil do usuário demo. Os dados não são salvos no banco.",
                "warning",
            )
            return redirect(url_for("auth.profile"))

        # Capturar valores antigos para auditoria
        old_values = {
            "full_name": current_user.full_name,
            "email": current_user.email,
            "oab_number": current_user.oab_number,
            "phone": current_user.phone,
            "cep": current_user.cep,
            "street": current_user.street,
            "number": current_user.number,
            "uf": current_user.uf,
            "city": current_user.city,
            "neighborhood": current_user.neighborhood,
            "complement": current_user.complement,
            "specialties": current_user.get_specialties(),
            "quick_actions": current_user.get_quick_actions(),
        }

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

        # Capturar valores novos para auditoria
        new_values = {
            "full_name": current_user.full_name,
            "email": current_user.email,
            "oab_number": current_user.oab_number,
            "phone": current_user.phone,
            "cep": current_user.cep,
            "street": current_user.street,
            "number": current_user.number,
            "uf": current_user.uf,
            "city": current_user.city,
            "neighborhood": current_user.neighborhood,
            "complement": current_user.complement,
            "specialties": current_user.get_specialties(),
            "quick_actions": current_user.get_quick_actions(),
        }

        # Identificar campos alterados
        changed_fields = []
        for key in old_values:
            if old_values[key] != new_values[key]:
                changed_fields.append(key)

        # Log de auditoria
        if changed_fields:
            AuditManager.log_user_change(
                current_user, "update", old_values, new_values, changed_fields
            )

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
    from app.services import EmailService, generate_email_2fa_code

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
        method = form.method.data

        if method == "email":
            # Para email, gerar código e enviar
            code = generate_email_2fa_code()
            current_user.email_2fa_code = code

            from datetime import timedelta

            current_user.email_2fa_code_expires = datetime.now(
                timezone.utc
            ) + timedelta(minutes=10)
            db.session.commit()

            # Enviar código por email
            if EmailService.send_2fa_code_email(
                current_user.email, code, method="email"
            ):
                flash(
                    f"Código enviado para {current_user.email}. Verifique seu email.",
                    "info",
                )
                # Mostrar formulário de verificação
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
            # Para TOTP
            # Verificar código de verificação
            if current_user.verify_2fa_code(form.verification_code.data):
                # Habilitar 2FA
                backup_codes = current_user.enable_2fa(method)

                # Registrar auditoria
                from app.utils.audit import AuditManager

                AuditManager.log_change(
                    entity_type="user",
                    entity_id=current_user.id,
                    action="2fa_enabled",
                    new_values={"method": method},
                    description=f"2FA habilitado via {method}",
                    additional_metadata={
                        "method": method,
                        "ip_address": request.remote_addr,
                    },
                )

                # Criar notificação in-app
                from app.models import Notification

                method_name = (
                    "Email" if method == "email" else "Aplicativo Autenticador (TOTP)"
                )
                Notification.create_notification(
                    user_id=current_user.id,
                    notification_type="2fa_enabled",
                    title="Autenticação de Dois Fatores Ativada",
                    message=f"2FA foi ativado com sucesso via {method_name}. Você receberá um código adicional ao fazer login.",
                )

                # Enviar email de notificação
                EmailService.send_2fa_enabled_notification(
                    current_user.email,
                    current_user.full_name or current_user.username,
                    method,
                )

                flash("2FA habilitado com sucesso!", "success")

                # Mostrar códigos de backup
                session["backup_codes"] = backup_codes
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
        import base64
        import io

        import qrcode

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        # Converter para base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_code_data = base64.b64encode(buffer.getvalue()).decode()

    return render_template(
        "auth/setup_2fa.html", form=form, totp_uri=totp_uri, qr_code_data=qr_code_data
    )


@bp.route("/2fa/show-backup-codes")
@login_required
def show_backup_codes():
    """Mostrar códigos de backup após configurar 2FA"""
    if not current_user.two_factor_enabled:
        return redirect(url_for("auth.profile"))

    backup_codes = session.pop("backup_codes", None)
    if not backup_codes:
        backup_codes = current_user.get_backup_codes()

    return render_template("auth/backup_codes.html", backup_codes=backup_codes)


@bp.route("/2fa/manage")
@login_required
def manage_2fa():
    """Página para gerenciar configurações de 2FA"""
    return render_template("auth/manage_2fa.html")


@bp.route("/2fa/disable", methods=["POST"])
@login_required
def disable_2fa():
    """Desabilitar 2FA"""
    from flask import request

    from app.models import Notification
    from app.services import EmailService
    from app.utils.audit import AuditManager

    if not current_user.two_factor_enabled:
        flash("2FA não está habilitado.", "error")
        return redirect(url_for("auth.profile"))

    # Registrar auditoria
    AuditManager.log_change(
        entity_type="user",
        entity_id=current_user.id,
        action="2fa_disabled",
        old_values={"method": current_user.two_factor_method, "enabled": True},
        new_values={"enabled": False},
        description="2FA desabilitado",
        additional_metadata={"ip_address": request.remote_addr},
    )

    # Criar notificação in-app
    Notification.create_notification(
        user_id=current_user.id,
        notification_type="2fa_disabled",
        title="Autenticação de Dois Fatores Desativada",
        message="2FA foi desativado para sua conta. Você poderá fazer login usando apenas sua senha.",
    )

    # Enviar notificação por email
    EmailService.send_2fa_disabled_notification(
        current_user.email, current_user.full_name or current_user.username
    )

    current_user.disable_2fa()
    flash("2FA desabilitado com sucesso.", "success")
    return redirect(url_for("auth.profile"))


@bp.route("/2fa/regenerate-codes", methods=["POST"])
@login_required
def regenerate_backup_codes():
    """Regenerar códigos de recuperação"""
    from flask import jsonify, request

    from app.models import Notification
    from app.utils.audit import AuditManager

    if not current_user.two_factor_enabled:
        flash("2FA não está habilitado.", "error")
        return redirect(url_for("auth.profile"))

    # Gerar novos códigos
    backup_codes = current_user.regenerate_backup_codes()

    # Registrar auditoria
    AuditManager.log_change(
        entity_type="user",
        entity_id=current_user.id,
        action="2fa_backup_codes_regenerated",
        description="Códigos de recuperação 2FA regenerados",
        additional_metadata={
            "ip_address": request.remote_addr,
            "codes_count": len(backup_codes),
        },
    )

    # Criar notificação in-app
    Notification.create_notification(
        user_id=current_user.id,
        notification_type="2fa_codes_regenerated",
        title="Códigos de Recuperação Regenerados",
        message=f"Novos códigos de recuperação 2FA foram gerados. Os códigos anteriores não são mais válidos.",
    )

    # Armazenar na sessão para exibição
    from flask import session

    session["backup_codes"] = backup_codes

    flash("Códigos de recuperação regenerados com sucesso!", "success")
    return redirect(url_for("auth.show_backup_codes"))


@bp.route("/2fa/download-codes")
@login_required
def download_backup_codes():
    """Download dos códigos de recuperação em PDF"""
    from datetime import datetime, timezone
    from io import BytesIO

    from flask import request
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    if not current_user.two_factor_enabled:
        flash("2FA não está habilitado.", "error")
        return redirect(url_for("auth.profile"))

    # Obter códigos
    backup_codes = current_user.get_backup_codes()
    if not backup_codes:
        flash("Nenhum código de recuperação disponível.", "error")
        return redirect(url_for("auth.profile"))

    # Registrar auditoria
    from app.utils.audit import AuditManager

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

    # Título
    elements.append(Paragraph("Códigos de Recuperação - 2FA", title_style))
    elements.append(Spacer(1, 0.3 * inch))

    # Informações
    info_style = ParagraphStyle(
        "Info",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#666666"),
        spaceAfter=20,
    )

    user_info = f"<b>Usuário:</b> {current_user.email}<br/><b>Data:</b> {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M:%S')}<br/><b>Sistema:</b> Petitio"
    elements.append(Paragraph(user_info, info_style))
    elements.append(Spacer(1, 0.2 * inch))

    # Aviso importante
    warning_style = ParagraphStyle(
        "Warning",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#b91c1c"),
        spaceAfter=20,
        borderPadding=10,
        borderRadius=5,
    )

    warning = "<b>⚠️ IMPORTANTE:</b> Armazene estes códigos em um local seguro. Use um código quando não conseguir acessar seu autenticador. Cada código só pode ser usado uma vez."
    elements.append(Paragraph(warning, warning_style))
    elements.append(Spacer(1, 0.3 * inch))

    # Tabela de códigos
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

    # Build PDF
    doc.build(elements)
    buffer.seek(0)

    from flask import send_file

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"backup-codes-2fa-{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf",
    )


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

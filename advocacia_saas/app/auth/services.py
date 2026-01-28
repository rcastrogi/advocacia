"""
Auth Services - Camada de Lógica de Negócio para Autenticação.

Este módulo encapsula toda a lógica de negócio relacionada à autenticação,
incluindo login, registro, 2FA, gestão de senhas e perfil.
"""

import base64
import io
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import pyotp
import qrcode
from flask import current_app, request, session
from flask_login import login_user, logout_user
from werkzeug.utils import secure_filename

from app import db
from app.auth.repository import (
    ConsentRepository,
    NotificationRepository,
    UserRepository,
)
from app.models import User, _demo_user_cache
from app.utils.audit import AuditManager


@dataclass
class LoginResult:
    """Resultado de uma tentativa de login."""

    success: bool
    user: Optional[User] = None
    error_message: Optional[str] = None
    requires_2fa: bool = False
    two_factor_method: Optional[str] = None
    is_demo: bool = False
    redirect_url: Optional[str] = None
    is_password_expired: bool = False


@dataclass
class RegistrationResult:
    """Resultado de um registro de usuário."""

    success: bool
    user: Optional[User] = None
    error_message: Optional[str] = None
    was_referred: bool = False
    trial_days: int = 0


class AuthService:
    """Serviço de autenticação principal."""

    DEMO_EMAIL = "admin@advocaciasaas.com"
    DEMO_PASSWORD = "admin123"
    DEMO_USER_ID = 999999

    @classmethod
    def attempt_login(
        cls,
        email: str,
        password: str,
        remember_me: bool = False,
        two_factor_code: Optional[str] = None,
    ) -> LoginResult:
        """
        Tenta realizar login de um usuário.

        Args:
            email: Email do usuário
            password: Senha do usuário
            remember_me: Se deve lembrar o usuário
            two_factor_code: Código 2FA se necessário

        Returns:
            LoginResult com o resultado da tentativa
        """
        # Verificar login demo
        if cls._is_demo_login(email, password):
            return cls._handle_demo_login(remember_me)

        # Buscar usuário real
        user = UserRepository.find_by_email(email)

        if not user or not user.check_password(password):
            cls._log_failed_login(email)
            return LoginResult(
                success=False,
                error_message="Email ou senha inválidos",
            )

        # Master bypassa todas as verificações
        if user.is_master:
            return cls._complete_login(user, remember_me)

        # Verificar se usuário está ativo
        if not user.is_active:
            return LoginResult(
                success=False,
                error_message="Sua conta foi desativada. Entre em contato com o administrador.",
            )

        # Verificar 2FA
        if user.requires_2fa():
            result = cls._handle_2fa_verification(user, two_factor_code)
            if not result.success:
                return result

        # Login bem-sucedido
        return cls._complete_login(user, remember_me)

    @classmethod
    def _is_demo_login(cls, email: str, password: str) -> bool:
        """Verifica se é uma tentativa de login demo."""
        if email != cls.DEMO_EMAIL or password != cls.DEMO_PASSWORD:
            return False

        # Só permite demo se não existe master real
        return not UserRepository.master_exists()

    @classmethod
    def _handle_demo_login(cls, remember_me: bool) -> LoginResult:
        """Processa login do usuário demo."""
        demo_user = User(
            id=cls.DEMO_USER_ID,
            username="admin_demo",
            email=cls.DEMO_EMAIL,
            full_name="Administrador Demo",
            user_type="master",
            is_active=True,
        )
        demo_user.created_at = datetime.now(timezone.utc)
        demo_user.password_changed_at = datetime.now(timezone.utc)
        demo_user.password_expires_at = datetime.now(timezone.utc) + timedelta(
            days=9999
        )
        demo_user.password_history = "[]"
        demo_user.force_password_change = False

        try:
            demo_user.set_password(cls.DEMO_PASSWORD, skip_history_check=True)
        except TypeError:
            demo_user.set_password(cls.DEMO_PASSWORD)

        _demo_user_cache[cls.DEMO_USER_ID] = demo_user
        login_user(demo_user, remember=remember_me)
        AuditManager.log_login(demo_user, success=True)

        return LoginResult(
            success=True,
            user=demo_user,
            is_demo=True,
        )

    @classmethod
    def _handle_2fa_verification(cls, user: User, code: Optional[str]) -> LoginResult:
        """Verifica autenticação de dois fatores."""
        # Verificar bloqueio por tentativas
        if user.is_2fa_locked():
            AuditManager.log_change(
                entity_type="user",
                entity_id=user.id,
                action="2fa_locked",
                description="Usuário bloqueado por múltiplas tentativas de 2FA",
            )
            return LoginResult(
                success=False,
                error_message="Muitas tentativas falhadas de 2FA. Tente novamente em 15 minutos.",
            )

        # Se é 2FA por email, enviar código
        if user.two_factor_method == "email":
            user.send_2fa_email_code()

        # Se não forneceu código, pedir
        if not code:
            return LoginResult(
                success=False,
                requires_2fa=True,
                two_factor_method=user.two_factor_method,
                user=user,
            )

        # Verificar código
        if not user.verify_2fa_code(code):
            user.record_2fa_failed_attempt()
            AuditManager.log_change(
                entity_type="user",
                entity_id=user.id,
                action="2fa_failed_attempt",
                description=f"Tentativa falha de 2FA (tentativa {user.two_factor_failed_attempts})",
            )
            return LoginResult(
                success=False,
                error_message="Código 2FA inválido",
                requires_2fa=True,
                two_factor_method=user.two_factor_method,
                user=user,
            )

        # 2FA válido
        user.reset_2fa_failed_attempts()
        AuditManager.log_change(
            entity_type="user",
            entity_id=user.id,
            action="2fa_success",
            description="Login bem-sucedido com 2FA",
        )
        return LoginResult(success=True, user=user)

    @classmethod
    def _complete_login(cls, user: User, remember_me: bool) -> LoginResult:
        """Completa o processo de login."""
        login_user(user, remember=remember_me)
        AuditManager.log_login(user, success=True)

        # Verificar expiração de senha (exceto master)
        if not user.is_master and (
            user.force_password_change or user.is_password_expired()
        ):
            return LoginResult(
                success=True,
                user=user,
                is_password_expired=True,
            )

        return LoginResult(success=True, user=user)

    @classmethod
    def _log_failed_login(cls, email: str):
        """Registra tentativa de login falhada."""
        AuditManager.log_change(
            entity_type="user",
            entity_id=0,
            action="login_failed",
            description=f"Tentativa de login falhada - Email: {email}",
            additional_metadata={"email_attempted": email},
        )

    @staticmethod
    def logout(user: User):
        """Realiza logout do usuário."""
        AuditManager.log_logout(user)
        logout_user()
        session.clear()


class RegistrationService:
    """Serviço de registro de usuários."""

    @classmethod
    def register_user(
        cls,
        username: str,
        email: str,
        full_name: str,
        password: str,
        oab_number: Optional[str] = None,
        phone: Optional[str] = None,
        cep: Optional[str] = None,
        street: Optional[str] = None,
        number: Optional[str] = None,
        uf: Optional[str] = None,
        city: Optional[str] = None,
        neighborhood: Optional[str] = None,
        complement: Optional[str] = None,
        user_type: str = "advogado",
        specialties: Optional[list] = None,
        consent_personal_data: bool = False,
        consent_marketing: bool = False,
        consent_terms: bool = False,
        plan_id: Optional[int] = None,
    ) -> RegistrationResult:
        """
        Registra um novo usuário no sistema.

        Args:
            Dados do formulário de registro

        Returns:
            RegistrationResult com o resultado
        """
        # Determinar status de billing
        billing_status = "pending_payment" if plan_id else "active"

        # Criar usuário
        user = UserRepository.create_user(
            username=username,
            email=email,
            full_name=full_name,
            password=password,
            oab_number=oab_number,
            phone=phone,
            cep=cep,
            street=street,
            number=number,
            uf=uf,
            city=city,
            neighborhood=neighborhood,
            complement=complement,
            user_type=user_type,
            billing_status=billing_status,
            specialties=specialties,
        )

        # Processar consentimentos LGPD
        cls._process_consents(
            user, consent_personal_data, consent_marketing, consent_terms
        )

        # Processar indicação
        was_referred = cls._process_referral(user)

        # Iniciar período trial
        trial_days = current_app.config.get("DEFAULT_TRIAL_DAYS", 3)
        user.start_trial(trial_days)
        db.session.commit()

        # Auto-login
        login_user(user)

        return RegistrationResult(
            success=True,
            user=user,
            was_referred=was_referred,
            trial_days=trial_days,
        )

    @classmethod
    def _process_consents(
        cls,
        user: User,
        consent_personal_data: bool,
        consent_marketing: bool,
        consent_terms: bool,
    ):
        """Processa os consentimentos LGPD do registro."""
        if consent_personal_data:
            ConsentRepository.create_consent(
                user_id=user.id,
                consent_type="personal_data",
                consent_purpose=(
                    "Prestação de serviços da plataforma Petitio, incluindo "
                    "criação de petições, gestão de clientes e funcionalidades do sistema."
                ),
            )
            ConsentRepository.log_processing(
                user_id=user.id,
                action="user_registration",
                data_category="personal_data",
                purpose="service_provision",
                legal_basis="LGPD Art. 7º, V (consentimento)",
                additional_data={
                    "user_type": user.user_type,
                    "registration_method": "web_form",
                },
            )

        if consent_marketing:
            ConsentRepository.create_consent(
                user_id=user.id,
                consent_type="marketing",
                consent_purpose=(
                    "Envio de comunicações de marketing, newsletters e "
                    "informações sobre novos recursos e atualizações da plataforma."
                ),
            )
            ConsentRepository.log_processing(
                user_id=user.id,
                action="marketing_consent_given",
                data_category="contact_data",
                purpose="marketing_communications",
                legal_basis="LGPD Art. 7º, V (consentimento)",
            )

        if consent_terms:
            ConsentRepository.create_consent(
                user_id=user.id,
                consent_type="terms_acceptance",
                consent_purpose=(
                    "Aceitação dos Termos de Uso e Política de Privacidade "
                    "da plataforma Petitio."
                ),
            )

        ConsentRepository.commit()

    @staticmethod
    def _process_referral(user: User) -> bool:
        """Processa indicação se houver."""
        from app.referral.routes import process_referral_registration

        referral = process_referral_registration(user.email, user.id)
        if referral:
            current_app.logger.info(
                f"User {user.id} registered via referral from {referral.referrer_id}"
            )
            return True
        return False


class ProfileService:
    """Serviço de gestão de perfil do usuário."""

    @staticmethod
    def update_profile(
        user: User,
        full_name: str,
        email: str,
        oab_number: Optional[str] = None,
        phone: Optional[str] = None,
        cep: Optional[str] = None,
        street: Optional[str] = None,
        number: Optional[str] = None,
        uf: Optional[str] = None,
        city: Optional[str] = None,
        neighborhood: Optional[str] = None,
        complement: Optional[str] = None,
        specialties: Optional[list] = None,
        quick_actions: Optional[list] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Atualiza o perfil do usuário.

        Returns:
            Tupla (success, error_message)
        """
        # Verificar se é demo
        if user.id == 999999:
            return False, "Não é possível editar o perfil do usuário demo."

        # Capturar valores antigos para auditoria
        old_values = {
            "full_name": user.full_name,
            "email": user.email,
            "oab_number": user.oab_number,
            "phone": user.phone,
            "cep": user.cep,
            "street": user.street,
            "number": user.number,
            "uf": user.uf,
            "city": user.city,
            "neighborhood": user.neighborhood,
            "complement": user.complement,
            "specialties": user.get_specialties(),
            "quick_actions": user.get_quick_actions(),
        }

        # Atualizar campos
        user.full_name = full_name
        user.email = email
        user.oab_number = oab_number
        user.phone = phone
        user.cep = cep
        user.street = street
        user.number = number
        user.uf = uf
        user.city = city
        user.neighborhood = neighborhood
        user.complement = complement

        if specialties is not None:
            user.set_specialties(specialties)
        if quick_actions is not None:
            user.set_quick_actions(quick_actions)

        db.session.commit()

        # Capturar valores novos e registrar auditoria
        new_values = {
            "full_name": user.full_name,
            "email": user.email,
            "oab_number": user.oab_number,
            "phone": user.phone,
            "cep": user.cep,
            "street": user.street,
            "number": user.number,
            "uf": user.uf,
            "city": user.city,
            "neighborhood": user.neighborhood,
            "complement": user.complement,
            "specialties": user.get_specialties(),
            "quick_actions": user.get_quick_actions(),
        }

        changed_fields = [k for k in old_values if old_values[k] != new_values[k]]

        if changed_fields:
            AuditManager.log_user_change(
                user, "update", old_values, new_values, changed_fields
            )

        return True, None

    @staticmethod
    def upload_logo(user: User, file) -> Tuple[bool, str]:
        """
        Faz upload do logo do usuário.

        Returns:
            Tupla (success, message)
        """
        if user.id == 999999:
            return False, "Não é possível fazer upload de logo para o usuário demo."

        if not file or file.filename == "":
            return False, "Nenhum arquivo selecionado"

        allowed_extensions = {"png", "jpg", "jpeg", "gif"}
        ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else ""

        if ext not in allowed_extensions:
            return False, "Formato de arquivo não permitido. Use PNG, JPG ou JPEG."

        filename = secure_filename(file.filename)
        name, file_ext = os.path.splitext(filename)
        filename = f"{user.id}_{name}{file_ext}"

        file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)

        # Remover logo antigo
        if user.logo_filename:
            old_path = os.path.join(
                current_app.config["UPLOAD_FOLDER"], user.logo_filename
            )
            if os.path.exists(old_path):
                os.remove(old_path)

        user.logo_filename = filename
        db.session.commit()

        return True, "Logo atualizado com sucesso!"


class PasswordService:
    """Serviço de gestão de senhas."""

    @staticmethod
    def change_password(
        user: User, current_password: str, new_password: str
    ) -> Tuple[bool, str]:
        """
        Altera a senha do usuário.

        Returns:
            Tupla (success, message)
        """
        if not user.check_password(current_password):
            return False, "Senha atual incorreta."

        try:
            user.set_password(new_password)
            db.session.commit()
            return True, "Senha alterada com sucesso!"
        except ValueError as e:
            return False, str(e)

    @staticmethod
    def is_password_change_required(user: User) -> bool:
        """Verifica se o usuário precisa trocar a senha."""
        if user.is_master:
            return False
        return user.force_password_change or user.is_password_expired()


class TwoFactorService:
    """Serviço de autenticação de dois fatores."""

    @classmethod
    def can_use_2fa(cls, user: User) -> bool:
        """Verifica se o usuário pode usar 2FA."""
        return user.requires_2fa() or user.is_admin()

    @classmethod
    def generate_totp_setup(cls, user: User) -> Tuple[str, str]:
        """
        Gera dados para configuração de TOTP.

        Returns:
            Tupla (totp_uri, qr_code_base64)
        """
        temp_secret = pyotp.random_base32()
        totp = pyotp.TOTP(temp_secret)
        totp_uri = totp.provisioning_uri(name=user.email, issuer_name="Petitio")

        # Gerar QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_code_data = base64.b64encode(buffer.getvalue()).decode()

        return totp_uri, qr_code_data

    @classmethod
    def enable_2fa(cls, user: User, method: str) -> list:
        """
        Habilita 2FA para o usuário.

        Returns:
            Lista de códigos de backup
        """
        from app.services import EmailService

        backup_codes = user.enable_2fa(method)

        # Registrar auditoria
        AuditManager.log_change(
            entity_type="user",
            entity_id=user.id,
            action="2fa_enabled",
            new_values={"method": method},
            description=f"2FA habilitado via {method}",
            additional_metadata={
                "method": method,
                "ip_address": request.remote_addr if request else None,
            },
        )

        # Criar notificação
        method_name = "Email" if method == "email" else "Aplicativo Autenticador (TOTP)"
        NotificationRepository.create_notification(
            user_id=user.id,
            notification_type="2fa_enabled",
            title="Autenticação de Dois Fatores Ativada",
            message=f"2FA foi ativado com sucesso via {method_name}. "
            "Você receberá um código adicional ao fazer login.",
        )

        # Enviar email de notificação
        EmailService.send_2fa_enabled_notification(
            user.email, user.full_name or user.username, method
        )

        return backup_codes

    @classmethod
    def disable_2fa(cls, user: User):
        """Desabilita 2FA para o usuário."""
        from app.services import EmailService

        # Registrar auditoria
        AuditManager.log_change(
            entity_type="user",
            entity_id=user.id,
            action="2fa_disabled",
            old_values={"method": user.two_factor_method, "enabled": True},
            new_values={"enabled": False},
            description="2FA desabilitado",
            additional_metadata={
                "ip_address": request.remote_addr if request else None
            },
        )

        # Criar notificação
        NotificationRepository.create_notification(
            user_id=user.id,
            notification_type="2fa_disabled",
            title="Autenticação de Dois Fatores Desativada",
            message="2FA foi desativado para sua conta. "
            "Você poderá fazer login usando apenas sua senha.",
        )

        # Enviar email
        EmailService.send_2fa_disabled_notification(
            user.email, user.full_name or user.username
        )

        user.disable_2fa()

    @classmethod
    def regenerate_backup_codes(cls, user: User) -> list:
        """Regenera códigos de backup."""
        backup_codes = user.regenerate_backup_codes()

        # Registrar auditoria
        AuditManager.log_change(
            entity_type="user",
            entity_id=user.id,
            action="2fa_backup_codes_regenerated",
            description="Códigos de recuperação 2FA regenerados",
            additional_metadata={
                "ip_address": request.remote_addr if request else None,
                "codes_count": len(backup_codes),
            },
        )

        # Criar notificação
        NotificationRepository.create_notification(
            user_id=user.id,
            notification_type="2fa_codes_regenerated",
            title="Códigos de Recuperação Regenerados",
            message="Novos códigos de recuperação 2FA foram gerados. "
            "Os códigos anteriores não são mais válidos.",
        )

        return backup_codes


class TimezoneService:
    """Serviço de gestão de fuso horário."""

    @staticmethod
    def update_timezone(user: User, timezone_str: str) -> Tuple[bool, str]:
        """
        Atualiza o fuso horário do usuário.

        Returns:
            Tupla (success, message)
        """
        import pytz

        try:
            pytz.timezone(timezone_str)
            user.timezone = timezone_str
            db.session.commit()
            return True, "Fuso horário atualizado com sucesso!"
        except pytz.exceptions.UnknownTimeZoneError:
            return False, "Fuso horário inválido."

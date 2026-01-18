import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db, login_manager

# Cache para usuário demo em memória
_demo_user_cache = {}

# Tabela de associação para relação muitos-para-muitos entre clientes e advogados
client_lawyers = db.Table(
    "client_lawyers",
    db.Column("client_id", db.Integer, db.ForeignKey("client.id"), primary_key=True),
    db.Column("lawyer_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("created_at", db.DateTime, default=lambda: datetime.now(timezone.utc)),
    db.Column(
        "specialty", db.String(100)
    ),  # área de atuação: 'familiar', 'trabalhista', etc
    db.Column("is_primary", db.Boolean, default=False),  # advogado principal do cliente
)

# Tabela de associação para relação muitos-para-muitos entre planos e features
plan_features = db.Table(
    "plan_features",
    db.Column(
        "plan_id", db.Integer, db.ForeignKey("billing_plans.id"), primary_key=True
    ),
    db.Column("feature_id", db.Integer, db.ForeignKey("features.id"), primary_key=True),
    db.Column(
        "limit_value", db.Integer, nullable=True
    ),  # Limite específico (ex: 100 créditos, 50 processos)
    db.Column("config_json", db.Text, nullable=True),  # Configurações extras em JSON
    db.Column("created_at", db.DateTime, default=lambda: datetime.now(timezone.utc)),
)

LEGACY_QUICK_ACTION_KEYS = {
    "petitions_civil": "petition:peticao-inicial-civel",
    "petitions_family": "petition:peticao-familia-divorcio",
}

DEFAULT_QUICK_ACTIONS = [
    "clients_new",
    "petition:peticao-inicial-civel",
    "petition:peticao-familia-divorcio",
    "clients_search",
]


@login_manager.user_loader
def load_user(user_id):
    user_id = int(user_id)
    # Se for o usuário demo (ID 999999), retornar do cache
    if user_id == 999999 and user_id in _demo_user_cache:
        return _demo_user_cache[user_id]
    # Caso contrário, buscar no banco de dados
    return db.session.get(User, user_id)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    user_type = db.Column(
        db.String(20), nullable=False, default="advogado"
    )  # 'master' = Dono do sistema (acesso total)
    # 'admin' = Administrador de escritório (futuro) - controla vários advogados
    # 'advogado' = Advogado individual ou de escritório
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Profile information
    full_name = db.Column(db.String(200))
    oab_number = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    nationality = db.Column(db.String(50))

    # Address (padronizado como em Client)
    cep = db.Column(db.String(10))
    street = db.Column(db.String(200))
    number = db.Column(db.String(20))
    uf = db.Column(db.String(2))
    city = db.Column(db.String(100))
    neighborhood = db.Column(db.String(100))
    complement = db.Column(db.String(200))

    logo_filename = db.Column(db.String(200))
    billing_status = db.Column(
        db.String(20), default="active"
    )  # active, delinquent, trial, pending_payment
    quick_actions = db.Column(db.Text, default=json.dumps(DEFAULT_QUICK_ACTIONS))
    specialties = db.Column(db.Text)  # JSON array of specialties for lawyers

    # User preferences
    timezone = db.Column(
        db.String(50), default="America/Sao_Paulo"
    )  # User's preferred timezone

    # Trial management
    trial_start_date = db.Column(db.DateTime)
    trial_days = db.Column(db.Integer, default=0)
    trial_active = db.Column(db.Boolean, default=False)

    # Password security fields
    password_changed_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    password_expires_at = db.Column(db.DateTime)
    password_history = db.Column(
        db.Text, default="[]"
    )  # JSON array of last 3 password hashes
    force_password_change = db.Column(db.Boolean, default=False)

    # Two-Factor Authentication (2FA) fields
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_method = db.Column(
        db.String(20), default="totp"
    )  # 'totp', 'email' or 'sms'
    totp_secret = db.Column(db.String(32))  # Secret key for TOTP
    two_factor_backup_codes = db.Column(db.Text)  # JSON array of backup codes
    two_factor_last_used = db.Column(db.DateTime)  # Last time 2FA was used
    email_2fa_code = db.Column(db.String(6))  # Temporary code for email 2FA
    email_2fa_code_expires = db.Column(db.DateTime)  # Expiration time for email code
    two_factor_failed_attempts = db.Column(db.Integer, default=0)  # Failed 2FA attempts
    two_factor_locked_until = db.Column(
        db.DateTime
    )  # Bloqueado até esta data após múltiplas tentativas

    # Office (Escritório) - Multi-users support
    office_id = db.Column(
        db.Integer,
        db.ForeignKey("offices.id", use_alter=True, name="fk_user_office"),
        nullable=True,
    )
    office_role = db.Column(
        db.String(20), nullable=True
    )  # owner, admin, lawyer, secretary, intern

    # Relationships
    clients = db.relationship(
        "Client",
        backref="lawyer",
        lazy="dynamic",
        foreign_keys="Client.lawyer_id",
    )
    plans = db.relationship(
        "UserPlan",
        backref="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    petition_usages = db.relationship(
        "PetitionUsage",
        backref="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def set_password(self, password, skip_history_check=False):
        """
        Define uma nova senha para o usuário.

        Args:
            password: A nova senha em texto plano
            skip_history_check: Se True, pula a verificação de histórico (útil para admin inicial)

        Raises:
            ValueError: Se a senha já foi usada nas últimas 3 mudanças
        """
        new_hash = generate_password_hash(password)

        # Verificar se a senha já foi usada recentemente (exceto no setup inicial)
        if not skip_history_check and self.password_hash:
            history = json.loads(self.password_history) if self.password_history else []

            # Verificar contra a senha atual
            if check_password_hash(self.password_hash, password):
                raise ValueError("Você não pode usar sua senha atual.")

            # Verificar contra o histórico
            for old_hash in history:
                if check_password_hash(old_hash, password):
                    raise ValueError(
                        "Esta senha já foi utilizada recentemente. Por favor, escolha uma senha diferente."
                    )

        # Atualizar histórico antes de mudar a senha
        if self.password_hash:
            history = json.loads(self.password_history) if self.password_history else []
            history.insert(0, self.password_hash)  # Adiciona a senha atual no início
            history = history[:3]  # Mantém apenas as últimas 3
            self.password_history = json.dumps(history)

        # Definir nova senha e datas
        self.password_hash = new_hash
        self.password_changed_at = datetime.now(timezone.utc)
        self.password_expires_at = datetime.now(timezone.utc) + timedelta(
            days=90
        )  # 3 meses
        self.force_password_change = False

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_password_expired(self):
        """Verifica se a senha está expirada"""
        if not self.password_expires_at:
            return True  # Se não tem data de expiração, força mudança
        return (
            datetime.now(timezone.utc).replace(tzinfo=None) > self.password_expires_at
        )

    def days_until_password_expires(self):
        """Retorna quantos dias faltam para a senha expirar"""
        if not self.password_expires_at:
            return 0
        delta = self.password_expires_at - datetime.now(timezone.utc).replace(
            tzinfo=None
        )
        return max(0, delta.days)

    def should_show_password_warning(self):
        """Retorna True se deve mostrar aviso de senha próxima do vencimento (7 dias)"""
        days = self.days_until_password_expires()
        return 0 < days <= 7

    def __repr__(self):
        return f"<User {self.username}>"

    @property
    def is_delinquent(self):
        return self.billing_status == "delinquent"

    @property
    def is_trial_expired(self):
        """Verifica se o trial expirou"""
        if not self.trial_active or not self.trial_start_date or not self.trial_days:
            return False
        from datetime import timedelta

        trial_end_date = self.trial_start_date + timedelta(days=self.trial_days)
        return datetime.now(timezone.utc).replace(tzinfo=None) > trial_end_date

    @property
    def trial_days_remaining(self):
        """Retorna quantos dias restam no trial"""
        if not self.trial_active or not self.trial_start_date or not self.trial_days:
            return 0
        from datetime import timedelta

        trial_end_date = self.trial_start_date + timedelta(days=self.trial_days)
        remaining = trial_end_date - datetime.now(timezone.utc)
        return max(0, remaining.days)

    def start_trial(self, days):
        """Inicia um período de trial"""
        self.trial_start_date = datetime.now(timezone.utc)
        self.trial_days = days
        self.trial_active = True
        self.billing_status = "trial"

    def end_trial(self):
        """Encerra o período de trial"""
        self.trial_active = False
        self.billing_status = "inactive"  # Usuário fica inativo até assinar

    def get_active_plan(self):
        return self.plans.filter_by(is_current=True).first()

    def has_active_subscription(self):
        plan = self.get_active_plan()
        return plan is not None and plan.status == "active"

    def get_specialties(self):
        """Retorna lista de especialidades do advogado"""
        if not self.specialties:
            return []
        try:
            return json.loads(self.specialties)
        except (TypeError, ValueError):
            return []

    def set_specialties(self, specialties_list):
        """Define as especialidades do advogado"""
        if isinstance(specialties_list, list):
            self.specialties = json.dumps(specialties_list)
        else:
            self.specialties = json.dumps([])

    def has_specialty(self, specialty):
        """Verifica se o advogado tem uma especialidade específica"""
        return specialty in self.get_specialties()

    def get_quick_actions(self):
        try:
            stored = json.loads(self.quick_actions) if self.quick_actions else []
        except (TypeError, ValueError):
            stored = []

        if not stored:
            return list(DEFAULT_QUICK_ACTIONS)

        return [LEGACY_QUICK_ACTION_KEYS.get(key, key) for key in stored]

    def set_quick_actions(self, actions: list[str]):
        if not actions:
            actions = list(DEFAULT_QUICK_ACTIONS)
        normalized = [LEGACY_QUICK_ACTION_KEYS.get(key, key) for key in actions]
        self.quick_actions = json.dumps(normalized)

    # =============================================================================
    # LGPD METHODS
    # =============================================================================

    def anonymize_personal_data(self):
        """Anonimiza dados pessoais do usuário (LGPD)"""
        import secrets
        import string

        # Gerar identificadores anônimos
        anon_id = f"ANON_{secrets.token_hex(8)}"

        # Dados antes da anonimização (para auditoria)
        original_data = {
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "cpf_cnpj": getattr(self, "cpf_cnpj", None),
            "address": {
                "street": self.street,
                "city": self.city,
                "state": self.state,
                "zip_code": self.zip_code,
            },
        }

        # Anonimizar dados pessoais
        self.full_name = f"Usuário Anônimo {anon_id}"
        self.email = f"anon_{anon_id}@anonymous.local"
        self.phone = None
        self.cpf_cnpj = None

        # Anonimizar endereço
        self.street = "Endereço Anônimo"
        self.city = "Cidade Anônima"
        self.state = "UF"
        self.zip_code = "00000-000"
        self.neighborhood = "Bairro Anônimo"
        self.complement = None

        # Limpar outros dados pessoais
        self.logo_filename = None
        self.specialties = None

        # Marcar como anonimizado
        self.billing_status = "anonymized"

        db.session.commit()

        return {
            "anon_id": anon_id,
            "original_data": original_data,
            "anonymized_at": datetime.now(timezone.utc).isoformat(),
        }

    def restore_from_anonymization(self, anonymization_request):
        """Restaura dados originais após anonimização (LGPD Art. 18)"""
        import json

        if self.billing_status != "anonymized":
            raise ValueError("Usuário não está anonimizado")

        if not anonymization_request or anonymization_request.status != "completed":
            raise ValueError("Solicitação de anonimização inválida ou não processada")

        try:
            # Obter dados originais
            original_data = json.loads(
                anonymization_request.anonymized_data or "{}"
            ).get("original_data", {})

            if not original_data:
                raise ValueError(
                    "Dados originais não encontrados na solicitação de anonimização"
                )

            # Restaurar dados pessoais
            self.full_name = original_data.get("full_name", self.full_name)
            self.email = original_data.get("email", self.email)
            self.phone = original_data.get("phone")
            self.cpf_cnpj = original_data.get("cpf_cnpj")

            # Restaurar endereço
            address = original_data.get("address", {})
            self.street = address.get("street")
            self.city = address.get("city")
            self.state = address.get("state")
            self.zip_code = address.get("zip_code")

            # Marcar como ativo novamente
            self.billing_status = "active"

            db.session.commit()

            return {
                "user_id": self.id,
                "restored_fields": list(original_data.keys()),
                "restored_at": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            db.session.rollback()
            raise Exception(f"Erro ao restaurar dados: {str(e)}")

    def delete_user_data(self):
        """Exclui permanentemente os dados do usuário (LGPD - Direito ao Esquecimento)"""
        if self.is_master:
            raise ValueError("Usuários master não podem ser excluídos ou anonimizados")

        try:
            # Dados antes da exclusão (para auditoria)
            audit_data = {
                "user_id": self.id,
                "username": self.username,
                "email": self.email,
                "full_name": self.full_name,
                "deleted_at": datetime.now(timezone.utc).isoformat(),
                "data_types_deleted": [],
            }

            # 1. Excluir relacionamentos e dados associados
            # Excluir clients relacionados
            for client in self.clients.all():
                db.session.delete(client)
            audit_data["data_types_deleted"].append("clients")

            # Excluir planos
            for plan in self.plans.all():
                db.session.delete(plan)
            audit_data["data_types_deleted"].append("plans")

            # Excluir usos de petições
            for usage in self.petition_usages.all():
                db.session.delete(usage)
            audit_data["data_types_deleted"].append("petition_usages")

            # Excluir templates de petições
            for template in self.petition_templates.all():
                db.session.delete(template)
            audit_data["data_types_deleted"].append("petition_templates")

            # Excluir consentimentos LGPD
            from app.models import (
                AnonymizationRequest,
                DataConsent,
                DataProcessingLog,
                DeletionRequest,
            )

            DataConsent.query.filter_by(user_id=self.id).delete()
            audit_data["data_types_deleted"].append("data_consents")

            # Excluir logs de processamento
            DataProcessingLog.query.filter_by(user_id=self.id).delete()
            audit_data["data_types_deleted"].append("processing_logs")

            # Excluir solicitações LGPD
            DeletionRequest.query.filter_by(user_id=self.id).delete()
            AnonymizationRequest.query.filter_by(user_id=self.id).delete()
            audit_data["data_types_deleted"].append("lgpd_requests")

            # 2. Limpar dados pessoais da conta (não excluir a conta em si para manter integridade referencial)
            self.username = f"deleted_user_{self.id}"
            self.email = f"deleted_user_{self.id}@deleted.local"
            self.password_hash = "DELETED"
            self.full_name = "Usuário Excluído"
            self.phone = None
            self.nationality = None
            self.cep = None
            self.street = None
            self.number = None
            self.uf = None
            self.city = None
            self.neighborhood = None
            self.complement = None
            self.logo_filename = None
            self.quick_actions = None
            self.specialties = None
            self.timezone = "UTC"
            self.billing_status = "deleted"
            self.is_active = False

            # Limpar dados de segurança
            self.password_changed_at = None
            self.password_expires_at = None
            self.password_history = None
            self.force_password_change = False

            # Limpar dados de trial
            self.trial_start_date = None
            self.trial_days = 0
            self.trial_active = False

            db.session.commit()

            # Log de auditoria da exclusão
            log = DataProcessingLog(
                user_id=self.id,
                action="user_data_deletion",
                data_category="all_user_data",
                purpose="right_to_erasure",
                legal_basis="LGPD Art. 18",
                additional_data=json.dumps(audit_data),
            )
            db.session.add(log)
            db.session.commit()

            return audit_data

        except Exception as e:
            db.session.rollback()
            raise Exception(f"Erro ao excluir dados do usuário: {str(e)}")

    def request_data_deletion(self, reason):
        """Cria solicitação de exclusão de dados"""
        from app.models import DeletionRequest

        request = DeletionRequest(
            user_id=self.id,
            request_reason=reason,
            deletion_scope=json.dumps(["account", "data", "documents"]),
        )

        db.session.add(request)
        db.session.commit()

        return request

    def has_valid_consent(self, consent_type):
        """Verifica se usuário tem consentimento válido para determinado tipo"""
        consent = DataConsent.query.filter_by(
            user_id=self.id, consent_type=consent_type, consented=True
        ).first()

        return consent and consent.is_valid() if consent else False

    # =============================================================================
    # FEATURE ACCESS METHODS (Sistema Modular)
    # =============================================================================

    def get_current_plan(self):
        """Retorna o plano atual do usuário"""
        user_plan = self.plans.filter_by(is_current=True, status="active").first()
        if user_plan:
            return user_plan.plan
        return None

    def has_feature(self, feature_slug):
        """
        Verifica se o usuário tem acesso a uma feature específica.

        Master users têm acesso a todas as features.
        Usuários normais dependem do plano ativo.

        Args:
            feature_slug: Slug da feature (ex: 'ai_petitions', 'portal_cliente')

        Returns:
            bool: True se tem acesso à feature
        """
        # Master sempre tem acesso total
        if self.is_master:
            return True

        # Buscar plano atual
        plan = self.get_current_plan()
        if not plan:
            return False

        return plan.has_feature(feature_slug)

    def get_feature_limit(self, feature_slug):
        """
        Obtém o limite de uma feature para o usuário.

        Args:
            feature_slug: Slug da feature

        Returns:
            int ou None: Limite da feature (None = ilimitado ou não aplicável)
        """
        # Master não tem limites
        if self.is_master:
            return None  # Ilimitado

        plan = self.get_current_plan()
        if not plan:
            return 0

        return plan.get_feature_limit(feature_slug)

    def get_monthly_credits(self, feature_slug):
        """
        Retorna os créditos mensais que o usuário tem direito por uma feature.
        Útil para features do tipo 'credits' que renovam mensalmente.

        Args:
            feature_slug: Slug da feature de créditos (ex: 'ai_credits_monthly')

        Returns:
            int: Quantidade de créditos mensais (0 se não tem a feature)
        """
        if self.is_master:
            return -1  # Ilimitado (representado por -1)

        plan = self.get_current_plan()
        if not plan or not plan.has_feature(feature_slug):
            return 0

        return plan.get_feature_limit(feature_slug) or 0

    def get_all_features(self):
        """
        Retorna todas as features disponíveis para o usuário.

        Returns:
            list: Lista de dicts com feature e configuração
        """
        if self.is_master:
            # Master vê todas as features ativas
            from app.models import Feature

            features = Feature.query.filter_by(is_active=True).all()
            return [{"feature": f, "limit": None, "config": {}} for f in features]

        plan = self.get_current_plan()
        if not plan:
            return []

        return plan.get_all_features_with_limits()

    def is_admin(self):
        """
        Verifica se é administrador (master ou admin de escritório)

        - master: Dono do sistema, acesso total a tudo
        - admin: Administrador de escritório de advocacia (futuro)

        Returns:
            bool: True se é master ou admin
        """
        return self.user_type in ["master", "admin"]

    @property
    def is_master(self):
        """
        Verifica se é usuário master (super admin)

        Master é o dono do sistema com acesso total.
        Tem permissão para tudo, incluindo:
        - Gerenciar outros usuários
        - Acessar dados de qualquer escritório
        - Configurar sistema inteiro
        - Nunca pode ter acesso bloqueado

        Returns:
            bool: True se é master
        """
        return self.user_type == "master"

    @property
    def is_client(self):
        """Verifica se é usuário cliente (acessa portal do cliente)"""
        from app.models import Client

        return Client.query.filter_by(user_id=self.id).first() is not None

    def deactivate(self):
        """Desativa o usuário (com proteção para master)"""
        if self.is_master:
            raise ValueError("Usuários master não podem ser desativados")
        self.is_active = False

    def activate(self):
        """Ativa o usuário"""
        self.is_active = True

    # =============================================================================
    # TWO-FACTOR AUTHENTICATION (2FA) METHODS
    # =============================================================================

    def enable_2fa(self, method="totp"):
        """Habilita 2FA para o usuário com códigos de recuperação mais robustos"""
        import json
        import secrets

        import pyotp

        self.two_factor_method = method
        self.two_factor_enabled = True

        if method == "totp":
            # Gera chave secreta TOTP
            self.totp_secret = pyotp.random_base32()

        # Gera códigos de backup mais robustos (12 caracteres em formato XXXX-XXXX-XXXX)
        backup_codes = []
        for _ in range(10):
            # Gera 3 segmentos de 4 caracteres aleatórios
            code = "-".join(
                [
                    secrets.token_hex(2).upper()  # 4 caracteres hex = 16 bits
                    for _ in range(3)
                ]
            )
            backup_codes.append(code)

        self.two_factor_backup_codes = json.dumps(backup_codes)

        db.session.commit()
        return backup_codes

    def disable_2fa(self):
        """Desabilita 2FA para o usuário"""
        self.two_factor_enabled = False
        self.two_factor_method = None
        self.totp_secret = None
        self.two_factor_backup_codes = None
        self.two_factor_last_used = None
        db.session.commit()

    def verify_2fa_code(self, code):
        """Verifica código 2FA (TOTP, Email ou backup)"""
        import json

        import pyotp

        if not self.two_factor_enabled:
            return True  # Se 2FA não está habilitado, permite login

        # Verifica códigos de backup primeiro
        if self.two_factor_backup_codes:
            try:
                backup_codes = json.loads(self.two_factor_backup_codes)
                if code in backup_codes:
                    # Remove o código usado
                    backup_codes.remove(code)
                    self.two_factor_backup_codes = json.dumps(backup_codes)
                    self.two_factor_last_used = datetime.now(timezone.utc)
                    db.session.commit()
                    return True
            except (json.JSONDecodeError, ValueError):
                pass

        # Verifica código de email 2FA
        if self.two_factor_method == "email" and self.email_2fa_code:
            # Verifica se código não expirou (10 minutos)
            if (
                self.email_2fa_code_expires
                and datetime.now(timezone.utc) <= self.email_2fa_code_expires
            ):
                if code == self.email_2fa_code:
                    # Limpar código após uso
                    self.email_2fa_code = None
                    self.email_2fa_code_expires = None
                    self.two_factor_last_used = datetime.now(timezone.utc)
                    db.session.commit()
                    return True
            else:
                # Código expirou
                self.email_2fa_code = None
                self.email_2fa_code_expires = None
                db.session.commit()
                return False

        # Verifica TOTP
        if self.two_factor_method == "totp" and self.totp_secret:
            totp = pyotp.TOTP(self.totp_secret)
            if totp.verify(code, valid_window=1):  # 30 segundos de tolerância
                self.two_factor_last_used = datetime.now(timezone.utc)
                db.session.commit()
                return True

        return False

    def get_totp_uri(self):
        """Retorna URI para configurar TOTP no app autenticador"""
        import pyotp

        if not self.totp_secret:
            return None

        totp = pyotp.TOTP(self.totp_secret)
        return totp.provisioning_uri(name=self.email, issuer_name="Petitio")

    def send_2fa_email_code(self) -> bool:
        """
        Gera e envia código 2FA por email
        Retorna True se enviado com sucesso
        """
        from datetime import timedelta

        from app.services import EmailService, generate_email_2fa_code

        # Gerar código de 6 dígitos
        code = generate_email_2fa_code()

        # Definir expiração em 10 minutos
        self.email_2fa_code = code
        self.email_2fa_code_expires = datetime.now(timezone.utc) + timedelta(minutes=10)
        db.session.commit()

        # Enviar por email
        return EmailService.send_2fa_code_email(self.email, code, method="email")

    def is_2fa_locked(self) -> bool:
        """Verifica se usuário está bloqueado por múltiplas tentativas de 2FA"""
        if not self.two_factor_locked_until:
            return False

        if datetime.now(timezone.utc) > self.two_factor_locked_until:
            # Bloqueio expirou
            self.two_factor_locked_until = None
            self.two_factor_failed_attempts = 0
            db.session.commit()
            return False

        return True

    def record_2fa_failed_attempt(self):
        """Registra tentativa falhada de 2FA. Bloqueia após 3 tentativas"""
        from datetime import timedelta

        self.two_factor_failed_attempts = (self.two_factor_failed_attempts or 0) + 1

        if self.two_factor_failed_attempts >= 3:
            # Bloquear por 15 minutos
            self.two_factor_locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=15
            )

        db.session.commit()

    def reset_2fa_failed_attempts(self):
        """Reseta contador de tentativas falhadas após sucesso"""
        self.two_factor_failed_attempts = 0
        self.two_factor_locked_until = None
        db.session.commit()

    def requires_2fa(self):
        """Verifica se usuário deve usar 2FA (administradores e advogados)"""
        return (
            self.user_type in ["master", "admin", "advogado"]
            and self.two_factor_enabled
        )

    def get_backup_codes(self):
        """Retorna códigos de backup (apenas para exibição uma vez)"""
        import json

        if not self.two_factor_backup_codes:
            return []

        try:
            return json.loads(self.two_factor_backup_codes)
        except json.JSONDecodeError:
            return []

    def regenerate_backup_codes(self):
        """Gera novos códigos de recuperação, invalidando os antigos"""
        import json
        import secrets

        # Gera novos códigos de backup (12 caracteres em formato XXXX-XXXX-XXXX)
        backup_codes = []
        for _ in range(10):
            code = "-".join(
                [
                    secrets.token_hex(2).upper()  # 4 caracteres hex = 16 bits
                    for _ in range(3)
                ]
            )
            backup_codes.append(code)

        self.two_factor_backup_codes = json.dumps(backup_codes)
        db.session.commit()
        return backup_codes

    def count_remaining_backup_codes(self):
        """Retorna quantidade de códigos de backup não utilizados"""
        return len(self.get_backup_codes())

    # =============================================================================
    # OFFICE (ESCRITÓRIO) METHODS
    # =============================================================================

    def get_office(self):
        """Retorna o escritório do usuário (se pertencer a um)"""
        if self.office_id:
            return Office.query.get(self.office_id)
        return None

    def is_office_owner(self):
        """Verifica se é dono de algum escritório"""
        return Office.query.filter_by(owner_id=self.id).first() is not None

    def get_owned_office(self):
        """Retorna o escritório que o usuário é dono"""
        return Office.query.filter_by(owner_id=self.id).first()

    def can_manage_office(self):
        """Verifica se pode gerenciar o escritório (dono ou admin)"""
        if self.is_master:
            return True
        return self.office_role in ["owner", "admin"]

    def get_office_members(self):
        """Retorna todos os membros do escritório do usuário"""
        if not self.office_id:
            return []
        return User.query.filter_by(office_id=self.office_id, is_active=True).all()

    def can_access_user_data(self, target_user_id):
        """Verifica se pode acessar dados de outro usuário (mesmo escritório)"""
        if self.is_master:
            return True
        if self.id == target_user_id:
            return True
        target_user = User.query.get(target_user_id)
        if not target_user:
            return False
        # Mesmo escritório = pode acessar
        return self.office_id and self.office_id == target_user.office_id


# =============================================================================
# OFFICE MODEL - Modelo de Escritório de Advocacia
# =============================================================================


class Office(db.Model):
    """
    Escritório de Advocacia.

    Agrupa usuários (advogados, secretárias, estagiários) em um escritório.
    O plano de cobrança é vinculado ao escritório, não aos usuários individuais.
    """

    __tablename__ = "offices"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)

    # Dono do escritório (quem criou e é responsável pelo pagamento)
    owner_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", use_alter=True, name="fk_office_owner"),
        nullable=False,
    )

    # Informações do escritório
    cnpj = db.Column(db.String(20))
    oab_number = db.Column(db.String(50))  # OAB do escritório (se for sociedade)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    website = db.Column(db.String(200))

    # Endereço
    cep = db.Column(db.String(10))
    street = db.Column(db.String(200))
    number = db.Column(db.String(20))
    complement = db.Column(db.String(200))
    neighborhood = db.Column(db.String(100))
    city = db.Column(db.String(100))
    uf = db.Column(db.String(2))

    # Branding
    logo_filename = db.Column(db.String(200))
    primary_color = db.Column(db.String(7), default="#1a73e8")  # Hex color

    # Configurações
    settings = db.Column(db.Text, default="{}")  # JSON com configurações extras

    # Status
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relacionamentos
    owner = db.relationship("User", foreign_keys=[owner_id], backref="owned_offices")
    members = db.relationship(
        "User", foreign_keys="User.office_id", backref="office", lazy="dynamic"
    )
    invites = db.relationship(
        "OfficeInvite", backref="office", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Office {self.name}>"

    @staticmethod
    def generate_slug(name):
        """Gera slug único baseado no nome"""
        import re
        import unicodedata

        # Normalizar e remover acentos
        slug = unicodedata.normalize("NFKD", name.lower())
        slug = slug.encode("ASCII", "ignore").decode("ASCII")
        # Remover caracteres especiais
        slug = re.sub(r"[^\w\s-]", "", slug)
        # Substituir espaços por hífens
        slug = re.sub(r"[\s_]+", "-", slug).strip("-")

        # Verificar unicidade
        base_slug = slug
        counter = 1
        while Office.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug

    def get_settings(self):
        """Retorna configurações como dict"""
        if not self.settings:
            return {}
        try:
            return json.loads(self.settings)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_settings(self, settings_dict):
        """Define configurações a partir de dict"""
        self.settings = json.dumps(settings_dict)

    def update_setting(self, key, value):
        """Atualiza uma configuração específica"""
        settings = self.get_settings()
        settings[key] = value
        self.set_settings(settings)

    def get_member_count(self):
        """Retorna número de membros ativos"""
        return self.members.filter_by(is_active=True).count()

    def get_max_members(self):
        """Retorna limite de membros baseado no plano do dono"""
        owner = User.query.get(self.owner_id)
        if owner:
            limit = owner.get_feature_limit("multi_users")
            return limit if limit else 999  # None = ilimitado
        return 1

    def can_add_member(self):
        """Verifica se pode adicionar mais membros"""
        current = self.get_member_count()
        max_members = self.get_max_members()
        return current < max_members

    def add_member(self, user, role="lawyer"):
        """Adiciona um membro ao escritório"""
        if not self.can_add_member():
            raise ValueError(
                f"Limite de {self.get_max_members()} membros atingido. Faça upgrade do plano."
            )

        user.office_id = self.id
        user.office_role = role
        db.session.commit()
        return True

    def remove_member(self, user):
        """Remove um membro do escritório"""
        if user.id == self.owner_id:
            raise ValueError("Não é possível remover o dono do escritório")

        user.office_id = None
        user.office_role = None
        db.session.commit()
        return True

    def transfer_ownership(self, new_owner):
        """Transfere a propriedade do escritório para outro membro"""
        if new_owner.office_id != self.id:
            raise ValueError("Novo dono deve ser membro do escritório")

        # Atualiza roles
        old_owner = User.query.get(self.owner_id)
        if old_owner:
            old_owner.office_role = "admin"  # Rebaixa para admin

        new_owner.office_role = "owner"
        self.owner_id = new_owner.id

        db.session.commit()
        return True

    def get_members_by_role(self, role):
        """Retorna membros por role"""
        return self.members.filter_by(office_role=role, is_active=True).all()

    def get_all_clients(self):
        """Retorna todos os clientes do escritório (de todos os membros)"""
        member_ids = [m.id for m in self.members.filter_by(is_active=True).all()]
        return Client.query.filter(Client.lawyer_id.in_(member_ids)).all()


class OfficeInvite(db.Model):
    """
    Convites para novos membros do escritório.

    Permite convidar advogados, secretárias, estagiários por email.
    O convite expira em 7 dias por padrão.
    """

    __tablename__ = "office_invites"

    id = db.Column(db.Integer, primary_key=True)
    office_id = db.Column(db.Integer, db.ForeignKey("offices.id"), nullable=False)

    # Quem está sendo convidado
    email = db.Column(db.String(120), nullable=False)
    role = db.Column(
        db.String(20), default="lawyer"
    )  # owner, admin, lawyer, secretary, intern

    # Token para aceitar convite
    token = db.Column(db.String(100), unique=True, nullable=False)

    # Quem convidou
    invited_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # Status
    status = db.Column(
        db.String(20), default="pending"
    )  # pending, accepted, expired, cancelled

    # Datas
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=False)
    accepted_at = db.Column(db.DateTime)

    # Relacionamentos
    invited_by = db.relationship("User", foreign_keys=[invited_by_id])

    def __repr__(self):
        return f"<OfficeInvite {self.email} -> {self.office_id}>"

    @staticmethod
    def generate_token():
        """Gera token único para o convite"""
        import secrets

        return secrets.token_urlsafe(32)

    @staticmethod
    def create_invite(office, email, role, invited_by, days_valid=7):
        """Cria um novo convite"""
        # Verificar se já existe convite pendente
        existing = OfficeInvite.query.filter_by(
            office_id=office.id, email=email, status="pending"
        ).first()

        if existing:
            # Atualiza o convite existente
            existing.token = OfficeInvite.generate_token()
            existing.expires_at = datetime.now(timezone.utc) + timedelta(
                days=days_valid
            )
            existing.role = role
            existing.invited_by_id = invited_by.id
            db.session.commit()
            return existing

        # Cria novo convite
        invite = OfficeInvite(
            office_id=office.id,
            email=email,
            role=role,
            token=OfficeInvite.generate_token(),
            invited_by_id=invited_by.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=days_valid),
        )

        db.session.add(invite)
        db.session.commit()
        return invite

    def is_expired(self):
        """Verifica se convite expirou"""
        return datetime.now(timezone.utc) > self.expires_at

    def is_valid(self):
        """Verifica se convite ainda é válido"""
        return self.status == "pending" and not self.is_expired()

    def accept(self, user):
        """Aceita o convite e adiciona usuário ao escritório"""
        if not self.is_valid():
            raise ValueError("Convite expirado ou já utilizado")

        office = Office.query.get(self.office_id)
        if not office:
            raise ValueError("Escritório não encontrado")

        if not office.can_add_member():
            raise ValueError("Limite de membros do escritório atingido")

        # Adiciona ao escritório
        user.office_id = self.office_id
        user.office_role = self.role

        # Marca convite como aceito
        self.status = "accepted"
        self.accepted_at = datetime.now(timezone.utc)

        db.session.commit()
        return True

    def cancel(self):
        """Cancela o convite"""
        self.status = "cancelled"
        db.session.commit()

    def resend(self, days_valid=7):
        """Reenvia o convite com novo token e data de expiração"""
        if self.status != "pending":
            self.status = "pending"

        self.token = OfficeInvite.generate_token()
        self.expires_at = datetime.now(timezone.utc) + timedelta(days=days_valid)
        db.session.commit()
        return self


# Roles disponíveis para membros de escritório
OFFICE_ROLES = {
    "owner": {
        "name": "Proprietário",
        "description": "Dono do escritório. Acesso total e responsável pelo pagamento.",
        "permissions": ["all"],
    },
    "admin": {
        "name": "Administrador",
        "description": "Pode gerenciar membros e configurações do escritório.",
        "permissions": [
            "manage_members",
            "manage_settings",
            "view_reports",
            "manage_clients",
            "manage_processes",
        ],
    },
    "lawyer": {
        "name": "Advogado",
        "description": "Advogado do escritório. Acesso a clientes e processos.",
        "permissions": [
            "manage_clients",
            "manage_processes",
            "create_petitions",
            "view_calendar",
        ],
    },
    "secretary": {
        "name": "Secretária",
        "description": "Apoio administrativo. Agenda, clientes e documentos.",
        "permissions": [
            "view_clients",
            "manage_calendar",
            "manage_documents",
            "view_processes",
        ],
    },
    "intern": {
        "name": "Estagiário",
        "description": "Estagiário com acesso limitado.",
        "permissions": ["view_clients", "view_processes", "view_calendar"],
    },
}


class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # Escritório ao qual o cliente pertence (principal vínculo)
    # Se NULL, usa lawyer_id para determinar o escritório (compatibilidade)
    office_id = db.Column(
        db.Integer, db.ForeignKey("offices.id"), nullable=True, index=True
    )

    # Advogado que cadastrou/responsável principal (mantido para compatibilidade)
    lawyer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # Usuário do cliente para acesso ao portal (opcional)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relacionamento com escritório
    office = db.relationship("Office", backref=db.backref("clients", lazy="dynamic"))

    # Relação muitos-para-muitos com advogados
    lawyers = db.relationship(
        "User",
        secondary=client_lawyers,
        lazy="dynamic",
        backref=db.backref("represented_clients", lazy="dynamic"),
    )

    # Personal Information
    full_name = db.Column(db.String(200), nullable=False)
    rg = db.Column(db.String(20))
    cpf_cnpj = db.Column(db.String(20), nullable=False)
    civil_status = db.Column(db.String(50))
    birth_date = db.Column(db.Date)
    profession = db.Column(db.String(100))
    nationality = db.Column(db.String(50))
    birth_place = db.Column(db.String(100))
    mother_name = db.Column(db.String(200))
    father_name = db.Column(db.String(200))

    # Address
    address_type = db.Column(db.String(20))  # 'residencial' or 'comercial'
    cep = db.Column(db.String(10))
    street = db.Column(db.String(200))
    number = db.Column(db.String(20))
    uf = db.Column(db.String(2))
    city = db.Column(db.String(100))
    neighborhood = db.Column(db.String(100))
    complement = db.Column(db.String(200))

    # Contacts
    landline_phone = db.Column(db.String(20))
    email = db.Column(db.String(120), nullable=False)
    mobile_phone = db.Column(db.String(20), nullable=False)

    # Personal Conditions
    lgbt_declared = db.Column(db.Boolean, default=False)
    has_disability = db.Column(db.Boolean, default=False)
    disability_types = db.Column(db.String(200))  # Comma-separated values

    # Pregnancy/Maternity
    is_pregnant_postpartum = db.Column(db.Boolean, default=False)
    delivery_date = db.Column(db.Date)

    # Relationships
    dependents = db.relationship(
        "Dependent", backref="client", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Client {self.full_name}>"

    def add_lawyer(self, lawyer, specialty=None, is_primary=False):
        """Adiciona um advogado à lista de advogados do cliente"""
        if not self.has_lawyer(lawyer):
            self.lawyers.append(lawyer)
            # Atualizar metadados na tabela de associação
            stmt = (
                client_lawyers.update()
                .where(
                    db.and_(
                        client_lawyers.c.client_id == self.id,
                        client_lawyers.c.lawyer_id == lawyer.id,
                    )
                )
                .values(specialty=specialty, is_primary=is_primary)
            )
            db.session.execute(stmt)

    def remove_lawyer(self, lawyer):
        """Remove um advogado da lista de advogados do cliente"""
        if self.has_lawyer(lawyer):
            self.lawyers.remove(lawyer)

    def has_lawyer(self, lawyer):
        """Verifica se o advogado já está associado ao cliente"""
        return self.lawyers.filter_by(id=lawyer.id).count() > 0

    def get_primary_lawyer(self):
        """Retorna o advogado principal (ou o que cadastrou se não houver principal marcado)"""
        # Buscar advogado marcado como principal
        stmt = (
            db.select(User)
            .join(client_lawyers)
            .where(
                db.and_(
                    client_lawyers.c.client_id == self.id,
                    client_lawyers.c.is_primary.is_(True),
                )
            )
        )
        primary = db.session.execute(stmt).scalar()

        if primary:
            return primary

        # Se não houver principal, retorna o advogado que cadastrou
        return db.session.get(User, self.lawyer_id)

    def get_lawyer_by_specialty(self, specialty):
        """Retorna o advogado responsável por determinada especialidade"""
        stmt = (
            db.select(User)
            .join(client_lawyers)
            .where(
                db.and_(
                    client_lawyers.c.client_id == self.id,
                    client_lawyers.c.specialty == specialty,
                )
            )
        )
        return db.session.execute(stmt).scalar()

    def get_lawyer_specialty(self, lawyer_id):
        """Retorna a especialidade do advogado para este cliente"""
        stmt = db.select(client_lawyers.c.specialty).where(
            db.and_(
                client_lawyers.c.client_id == self.id,
                client_lawyers.c.lawyer_id == lawyer_id,
            )
        )
        result = db.session.execute(stmt).scalar()
        return result

    def to_dict(self):
        """Convert client to dictionary for API responses."""
        return {
            "id": self.id,
            "office_id": self.office_id,
            "full_name": self.full_name,
            "email": self.email,
            "cpf_cnpj": self.cpf_cnpj,
            "mobile_phone": self.mobile_phone,
            "landline_phone": self.landline_phone,
            "rg": self.rg,
            "civil_status": self.civil_status,
            "birth_date": self.birth_date.isoformat() if self.birth_date else None,
            "profession": self.profession,
            "nationality": self.nationality,
            "birth_place": self.birth_place,
            "mother_name": self.mother_name,
            "father_name": self.father_name,
            "address_type": self.address_type,
            "cep": self.cep,
            "street": self.street,
            "number": self.number,
            "uf": self.uf,
            "city": self.city,
            "neighborhood": self.neighborhood,
            "complement": self.complement,
            "lgbt_declared": self.lgbt_declared,
            "has_disability": self.has_disability,
            "disability_types": self.disability_types,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def get_effective_office_id(self):
        """
        Retorna o office_id efetivo do cliente.

        Se office_id está definido, usa ele.
        Caso contrário, busca o office_id do advogado que cadastrou.
        """
        if self.office_id:
            return self.office_id

        # Fallback: buscar office do advogado que cadastrou
        lawyer = db.session.get(User, self.lawyer_id)
        if lawyer and lawyer.office_id:
            return lawyer.office_id

        return None


class Dependent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"), nullable=False)

    full_name = db.Column(db.String(200), nullable=False)
    relationship = db.Column(db.String(50), nullable=False)  # filho, cônjuge, etc.
    birth_date = db.Column(db.Date)
    cpf = db.Column(db.String(14))

    def __repr__(self):
        return f"<Dependent {self.full_name}>"


class Estado(db.Model):
    """Brazilian states model."""

    __tablename__ = "estados"

    id = db.Column(db.Integer, primary_key=True)
    sigla = db.Column(db.String(2), unique=True, nullable=False, index=True)
    nome = db.Column(db.String(50), nullable=False)

    # Relationship
    cidades = db.relationship(
        "Cidade", backref="estado", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Estado {self.sigla} - {self.nome}>"

    def to_dict(self):
        """Convert to dictionary."""
        return {"id": self.id, "sigla": self.sigla, "nome": self.nome}


class Cidade(db.Model):
    """Brazilian cities model."""

    __tablename__ = "cidades"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, index=True)
    estado_id = db.Column(
        db.Integer, db.ForeignKey("estados.id"), nullable=False, index=True
    )

    def __repr__(self):
        return f"<Cidade {self.nome} - {self.estado.sigla}>"

    def to_dict(self):
        """Convert to dictionary."""
        return {"id": self.id, "nome": self.nome, "estado_id": self.estado_id}


plan_petition_types = db.Table(
    "plan_petition_types",
    db.Column(
        "plan_id", db.Integer, db.ForeignKey("billing_plans.id"), primary_key=True
    ),
    db.Column(
        "petition_type_id",
        db.Integer,
        db.ForeignKey("petition_types.id"),
        primary_key=True,
    ),
)


class PetitionType(db.Model):
    __tablename__ = "petition_types"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(
        db.String(120), unique=True, nullable=False
    )  # Slug truncado automaticamente
    name = db.Column(
        db.String(500), nullable=False
    )  # Nomes de petições podem ser longos
    description = db.Column(db.Text)
    category = db.Column(db.String(50), default="civel")
    icon = db.Column(db.String(50), default="fa-file-alt")  # Ícone FontAwesome
    color = db.Column(
        db.String(20), default="primary"
    )  # Cor Bootstrap (primary, success, danger, etc.)
    is_implemented = db.Column(db.Boolean, default=False)
    is_billable = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)
    base_price = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))
    active = db.Column(db.Boolean, default=True)
    # Indica se usa o novo sistema dinâmico de seções
    use_dynamic_form = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    plans = db.relationship(
        "BillingPlan",
        secondary=plan_petition_types,
        back_populates="petition_types",
    )
    usages = db.relationship(
        "PetitionUsage",
        backref="petition_type",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<PetitionType {self.slug}>"


class Feature(db.Model):
    """
    Features/Módulos do sistema que podem ser habilitados por plano.
    Exemplos: ai_petitions, portal_cliente, multi_users, api_access
    """

    __tablename__ = "features"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False)  # ex: 'ai_petitions'
    name = db.Column(db.String(120), nullable=False)  # ex: 'Petições com IA'
    description = db.Column(db.Text)

    # Categorização
    module = db.Column(
        db.String(50), nullable=False, default="core"
    )  # core, prazos, documentos, ia, portal, financeiro, avancado

    # Tipo de feature
    feature_type = db.Column(
        db.String(20), default="boolean"
    )  # boolean, limit, credits
    # boolean: habilitado/desabilitado
    # limit: tem um limite numérico (ex: 50 processos)
    # credits: créditos consumíveis (ex: créditos IA mensais)

    # Valores padrão
    default_limit = db.Column(db.Integer)  # Limite padrão se feature_type = 'limit'
    default_enabled = db.Column(
        db.Boolean, default=False
    )  # Se fica habilitado por padrão

    # Para créditos mensais
    is_monthly_renewable = db.Column(db.Boolean, default=False)  # Renova mensalmente?

    # Controle
    is_active = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)  # Ordem de exibição
    icon = db.Column(db.String(50), default="fas fa-check")  # Ícone FontAwesome

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relacionamentos
    plans = db.relationship(
        "BillingPlan",
        secondary=plan_features,
        back_populates="features",
    )

    def __repr__(self):
        return f"<Feature {self.slug}>"

    @classmethod
    def get_by_slug(cls, slug):
        """Busca feature por slug"""
        return cls.query.filter_by(slug=slug, is_active=True).first()

    @classmethod
    def get_all_by_module(cls, module):
        """Busca todas features de um módulo"""
        return (
            cls.query.filter_by(module=module, is_active=True)
            .order_by(cls.display_order)
            .all()
        )

    def to_dict(self):
        return {
            "id": self.id,
            "slug": self.slug,
            "name": self.name,
            "description": self.description,
            "module": self.module,
            "feature_type": self.feature_type,
            "default_limit": self.default_limit,
            "is_monthly_renewable": self.is_monthly_renewable,
            "icon": self.icon,
        }


class BillingPlan(db.Model):
    __tablename__ = "billing_plans"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    plan_type = db.Column(db.String(20), nullable=False, default="per_usage")
    monthly_fee = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))
    monthly_petition_limit = db.Column(db.Integer, default=None)  # None = ilimitado
    description = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Novos campos para períodos flexíveis
    supported_periods = db.Column(
        db.String(10), default="1m"
    )  # Período único suportado
    discount_percentage = db.Column(
        db.Numeric(5, 2), default=Decimal("0.00")
    )  # Desconto único para o período

    # Votação em features
    votes_per_period = db.Column(db.Integer, default=0)  # 0 = sem direito a votar

    petition_types = db.relationship(
        "PetitionType",
        secondary=plan_petition_types,
        back_populates="plans",
    )
    user_plans = db.relationship(
        "UserPlan",
        backref="plan",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    features = db.relationship(
        "Feature",
        secondary=plan_features,
        back_populates="plans",
    )

    def includes_petition(self, petition_type):
        return petition_type in self.petition_types

    def has_feature(self, feature_slug):
        """Verifica se o plano tem uma feature específica"""
        for feature in self.features:
            if feature.slug == feature_slug:
                return True
        return False

    def get_feature_limit(self, feature_slug):
        """Obtém o limite de uma feature para este plano"""
        from sqlalchemy import select

        # Buscar na tabela de associação
        stmt = select(plan_features.c.limit_value).where(
            plan_features.c.plan_id == self.id,
            plan_features.c.feature_id == Feature.id,
            Feature.slug == feature_slug,
        )
        result = db.session.execute(stmt).first()

        if result and result[0] is not None:
            return result[0]

        # Se não tem limite específico, retorna o default da feature
        feature = Feature.get_by_slug(feature_slug)
        return feature.default_limit if feature else None

    def get_feature_config(self, feature_slug):
        """Obtém configuração extra de uma feature para este plano"""
        from sqlalchemy import select

        stmt = select(plan_features.c.config_json).where(
            plan_features.c.plan_id == self.id,
            plan_features.c.feature_id == Feature.id,
            Feature.slug == feature_slug,
        )
        result = db.session.execute(stmt).first()

        if result and result[0]:
            return json.loads(result[0])
        return {}

    def get_all_features_with_limits(self):
        """Retorna todas as features do plano com seus limites"""
        from sqlalchemy import select

        features_data = []
        for feature in self.features:
            stmt = select(
                plan_features.c.limit_value, plan_features.c.config_json
            ).where(
                plan_features.c.plan_id == self.id,
                plan_features.c.feature_id == feature.id,
            )
            result = db.session.execute(stmt).first()

            features_data.append(
                {
                    "feature": feature,
                    "limit": result[0] if result else feature.default_limit,
                    "config": json.loads(result[1]) if result and result[1] else {},
                }
            )

        return features_data

    def get_price_for_period(self, period=None):
        """Calcula o preço para o período do plano com desconto"""
        # Se não especificar período, usa o período do plano
        if period is None:
            period = self.supported_periods

        # Se o período solicitado não é o suportado pelo plano, retorna None
        if period != self.supported_periods:
            return None

        # Converter período para meses
        period_months = self._period_to_months(period)
        base_price = float(self.monthly_fee) * period_months

        # Aplicar desconto se houver
        if self.discount_percentage and self.discount_percentage > 0:
            discount = base_price * (float(self.discount_percentage) / 100)
            return round(base_price - discount, 2)

        return round(base_price, 2)

    def _period_to_months(self, period):
        """Converte período para meses"""
        period_map = {"1m": 1, "3m": 3, "6m": 6, "1y": 12, "2y": 24, "3y": 36}
        return period_map.get(period, 1)

    def get_period_label(self, period):
        """Retorna o rótulo amigável para o período"""
        period_labels = {
            "1m": "1 mês",
            "3m": "3 meses",
            "6m": "6 meses",
            "1y": "1 ano",
            "2y": "2 anos",
            "3y": "3 anos",
        }
        return period_labels.get(period, period)

    @property
    def is_per_usage(self):
        """Check if this is a pay-per-use plan"""
        return self.plan_type == "per_usage"

    @property
    def plan_type_label(self):
        """Get friendly label for plan type"""
        labels = {
            "per_usage": "Por petição",
            "limited": "Mensal limitado",
            "unlimited": "Mensal ilimitado",
            "flat_monthly": "Mensal",
            "monthly": "Mensal",
            "annual": "Anual",
        }
        return labels.get(self.plan_type, self.plan_type.title())

    def __repr__(self):
        return f"<BillingPlan {self.slug}>"


class UserPlan(db.Model):
    __tablename__ = "user_plans"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey("billing_plans.id"), nullable=False)
    status = db.Column(db.String(20), default="active")
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    renewal_date = db.Column(db.DateTime)
    is_current = db.Column(db.Boolean, default=True)

    __table_args__ = (
        db.UniqueConstraint("user_id", "is_current", name="uq_user_current_plan"),
    )

    def __repr__(self):
        return f"<UserPlan user={self.user_id} plan={self.plan_id}>"


class PetitionUsage(db.Model):
    __tablename__ = "petition_usage"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    petition_type_id = db.Column(
        db.Integer, db.ForeignKey("petition_types.id"), nullable=False
    )
    plan_id = db.Column(db.Integer, db.ForeignKey("billing_plans.id"))
    generated_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    billing_cycle = db.Column(db.String(7), index=True)  # YYYY-MM
    billable = db.Column(db.Boolean, default=False)
    amount = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))
    extra_data = db.Column(db.JSON)

    plan = db.relationship("BillingPlan")

    def __repr__(self):
        return f"<PetitionUsage user={self.user_id} petition={self.petition_type_id}>"


class Invoice(db.Model):
    """Faturas/Cobranças para clientes"""

    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"))
    case_id = db.Column(db.Integer)  # Removida FK: tabela cases não existe

    # Compatibilidade com código antigo
    billing_cycle = db.Column(db.String(7))
    amount_due = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))
    amount_paid = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))
    issued_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Detalhes da fatura
    invoice_number = db.Column(db.String(50), unique=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    currency = db.Column(db.String(3), default="BRL")
    description = db.Column(db.Text)
    notes = db.Column(db.Text)

    # Datas
    issue_date = db.Column(db.Date, default=lambda: datetime.now(timezone.utc))
    due_date = db.Column(db.DateTime)
    paid_date = db.Column(db.Date)

    # Status
    status = db.Column(
        db.String(20), default="pending"
    )  # pending, paid, overdue, canceled

    # Recorrência
    is_recurring = db.Column(db.Boolean, default=False)
    recurrence_interval = db.Column(db.String(20))  # 'monthly', 'quarterly', 'yearly'
    next_invoice_date = db.Column(db.Date)

    # Pagamento
    payment_method = db.Column(db.String(50))
    boleto_url = db.Column(db.String(500))
    pix_code = db.Column(db.Text)

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    payments = db.relationship(
        "Payment",
        backref="invoice_rel",
        lazy="dynamic",
        foreign_keys="Payment.invoice_id",
        cascade="all, delete-orphan",
    )
    user = db.relationship("User", backref=db.backref("user_invoices", lazy="dynamic"))
    client = db.relationship(
        "Client", backref=db.backref("client_invoices", lazy="dynamic")
    )

    def __repr__(self):
        if self.invoice_number:
            return f"<Invoice {self.invoice_number} - {self.amount} - {self.status}>"
        return f"<Invoice {self.billing_cycle} user={self.user_id}>"

    def mark_as_paid(self, payment_method=None, paid_date=None):
        """Marca fatura como paga"""
        self.status = "paid"
        self.paid_date = paid_date or datetime.now(timezone.utc).date()
        self.amount_paid = self.amount or self.amount_due
        if payment_method:
            self.payment_method = payment_method

        # Se for recorrente, criar próxima fatura
        if self.is_recurring and self.next_invoice_date:
            self.create_next_invoice()

        db.session.commit()

    def create_next_invoice(self):
        """Cria próxima fatura recorrente"""
        if not self.is_recurring:
            return None

        # Calcular próxima data
        if self.recurrence_interval == "monthly":
            next_due = self.due_date + timedelta(days=30)
            next_invoice_date = self.next_invoice_date + timedelta(days=30)
        elif self.recurrence_interval == "quarterly":
            next_due = self.due_date + timedelta(days=90)
            next_invoice_date = self.next_invoice_date + timedelta(days=90)
        elif self.recurrence_interval == "yearly":
            next_due = self.due_date + timedelta(days=365)
            next_invoice_date = self.next_invoice_date + timedelta(days=365)
        else:
            return None

        # Criar nova fatura
        next_invoice = Invoice(
            user_id=self.user_id,
            client_id=self.client_id,
            case_id=self.case_id,
            invoice_number=(
                f"{self.invoice_number.split('-')[0]}-{datetime.now(timezone.utc).strftime('%Y%m')}"
                if self.invoice_number
                else None
            ),
            amount=self.amount,
            currency=self.currency,
            description=self.description,
            due_date=next_due,
            is_recurring=True,
            recurrence_interval=self.recurrence_interval,
            next_invoice_date=next_invoice_date,
        )
        db.session.add(next_invoice)
        db.session.commit()
        return next_invoice

    def is_overdue(self):
        """Verifica se a fatura está vencida"""
        if hasattr(self.due_date, "date"):
            due = self.due_date.date()
        else:
            due = self.due_date
        return self.status == "pending" and due < datetime.now(timezone.utc).date()

    def to_dict(self):
        return {
            "id": self.id,
            "invoice_number": self.invoice_number,
            "amount": float(self.amount),
            "currency": self.currency,
            "status": self.status,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "paid_date": self.paid_date.isoformat() if self.paid_date else None,
            "is_overdue": self.is_overdue(),
        }


class Payment(db.Model):
    """Pagamentos recebidos (assinaturas, faturas ou one-time)"""

    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"))
    subscription_id = db.Column(db.Integer, db.ForeignKey("subscriptions.id"))

    # Detalhes do pagamento
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default="BRL")
    payment_type = db.Column(
        db.String(20), nullable=False, default="one_time"
    )  # 'subscription', 'invoice', 'one_time'
    payment_method = db.Column(db.String(50))  # 'pix', 'boleto', 'credit_card'
    method = db.Column(db.String(30))  # Alias for compatibility
    reference = db.Column(db.String(120))
    description = db.Column(db.String(500))

    # Status
    status = db.Column(
        db.String(20), default="pending"
    )  # pending, paid, failed, refunded
    payment_status = db.Column(
        db.String(30), default="pending"
    )  # Alias for compatibility
    paid_at = db.Column(db.DateTime)
    failed_at = db.Column(db.DateTime)
    refunded_at = db.Column(db.DateTime)
    webhook_received_at = db.Column(db.DateTime)

    # Gateway info - Generic
    gateway = db.Column(db.String(20))  # 'mercadopago'
    gateway_payment_id = db.Column(db.String(200), unique=True, index=True)
    gateway_charge_id = db.Column(db.String(200))

    # PIX specific (Mercado Pago)
    pix_code = db.Column(db.Text)  # QR code data
    pix_qr_code = db.Column(db.Text)  # Base64 image
    pix_expires_at = db.Column(db.DateTime)

    # Extra data
    extra_data = db.Column(db.Text)  # JSON - renamed to avoid SQLAlchemy conflict
    extra_metadata = db.Column(db.JSON)  # For compatibility

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = db.relationship("User", backref=db.backref("user_payments", lazy="dynamic"))

    def __repr__(self):
        return f"<Payment {self.id} - {self.amount} {self.currency} - {self.status}>"

    def mark_as_paid(self):
        """Marca pagamento como pago"""
        self.status = "paid"
        self.payment_status = "completed"
        self.paid_at = datetime.now(timezone.utc)
        db.session.commit()

    def to_dict(self):
        return {
            "id": self.id,
            "amount": float(self.amount),
            "currency": self.currency,
            "status": self.status,
            "payment_method": self.payment_method,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
        }


class Testimonial(db.Model):
    """Depoimentos de usuários para exibição na página inicial."""

    __tablename__ = "testimonials"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, default=5)  # 1-5 stars

    # Campos para exibição (podem ser diferentes do perfil do usuário)
    display_name = db.Column(db.String(200), nullable=False)
    display_role = db.Column(
        db.String(100)
    )  # Ex: "Advogado", "Sócio do Escritório XYZ"
    display_location = db.Column(db.String(100))  # Ex: "São Paulo, SP"

    # Status de moderação
    status = db.Column(db.String(20), default="pending")  # pending, approved, rejected
    moderated_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    moderated_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Destaque na página inicial
    is_featured = db.Column(db.Boolean, default=False)

    # Relationships
    user = db.relationship("User", foreign_keys=[user_id], backref="testimonials")
    moderator = db.relationship("User", foreign_keys=[moderated_by])

    def __repr__(self):
        return f"<Testimonial id={self.id} by={self.display_name} status={self.status}>"


class PetitionSection(db.Model):
    """
    Define uma seção reutilizável para petições.
    Cada seção contém campos que podem ser usados em diferentes tipos de petição.
    """

    __tablename__ = "petition_sections"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # Ex: "Qualificação das Partes"
    slug = db.Column(
        db.String(100), unique=True, nullable=False
    )  # Ex: "qualificacao-partes"
    description = db.Column(db.String(255))
    icon = db.Column(db.String(50), default="fa-file-alt")  # Ícone FontAwesome
    color = db.Column(db.String(20), default="primary")  # Cor do Bootstrap
    order = db.Column(db.Integer, default=0)  # Ordem de exibição padrão
    is_active = db.Column(db.Boolean, default=True)

    # Campos da seção em formato JSON
    # Estrutura: [{"name": "author_name", "label": "Nome do Autor", "type": "text",
    #              "required": true, "size": "col-md-6", "placeholder": "...", "options": [...]}]
    fields_schema = db.Column(db.JSON, default=list)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def get_fields(self):
        """Retorna os campos da seção."""
        return self.fields_schema or []

    def set_fields(self, fields: list):
        """Define os campos da seção."""
        self.fields_schema = fields

    def __repr__(self):
        return f"<PetitionSection {self.slug}>"


# PetitionTypeSection removed - using only PetitionModelSection
# Kept table in DB for backward compatibility, but no longer used in code


class SavedPetition(db.Model):
    """
    Petições salvas pelo usuário (rascunhos e finalizadas).
    Permite consulta, edição e acompanhamento das petições criadas.
    """

    __tablename__ = "saved_petitions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    petition_type_id = db.Column(
        db.Integer, db.ForeignKey("petition_types.id"), nullable=True
    )
    petition_model_id = db.Column(
        db.Integer, db.ForeignKey("petition_models.id"), nullable=True
    )

    # Identificação
    title = db.Column(
        db.String(300)
    )  # Título da petição (ex: "Ação de Alimentos - João x Maria")
    process_number = db.Column(
        db.String(30), index=True
    )  # Número do processo (se houver)

    # Status: draft (rascunho), completed (finalizada), cancelled (cancelada)
    status = db.Column(db.String(20), default="draft", index=True)

    # Dados do formulário em JSON
    form_data = db.Column(db.JSON, default=dict)

    # Informações de pagamento (Pay per Use)
    is_paid = db.Column(db.Boolean, default=False)  # Se foi paga
    amount_paid = db.Column(db.Numeric(10, 2))  # Valor pago
    paid_at = db.Column(db.DateTime)  # Quando foi paga

    # Metadados
    notes = db.Column(db.Text)  # Anotações internas
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    completed_at = db.Column(db.DateTime)  # Quando foi finalizada
    cancelled_at = db.Column(db.DateTime)  # Quando foi cancelada

    # Relacionamentos
    user = db.relationship(
        "User", backref=db.backref("saved_petitions", lazy="dynamic")
    )
    petition_type = db.relationship(
        "PetitionType", backref=db.backref("saved_petitions", lazy="dynamic")
    )
    petition_model = db.relationship(
        "PetitionModel", backref=db.backref("saved_petitions", lazy="dynamic")
    )

    def get_status_display(self):
        """Retorna o status formatado para exibição."""
        status_map = {
            "draft": ("Rascunho", "warning"),
            "completed": ("Finalizada", "success"),
            "cancelled": ("Cancelada", "danger"),
        }
        return status_map.get(self.status, ("Desconhecido", "secondary"))

    def get_author_name(self):
        """Extrai o nome do autor dos dados do formulário."""
        if self.form_data:
            return self.form_data.get("autor_nome") or self.form_data.get(
                "requerente_nome", ""
            )
        return ""

    def get_defendant_name(self):
        """Extrai o nome do réu dos dados do formulário."""
        if self.form_data:
            return self.form_data.get("reu_nome") or self.form_data.get(
                "requerido_nome", ""
            )
        return ""

    def get_locked_fields(self):
        """
        Retorna lista de campos que devem ficar bloqueados na edição.
        Campos de partes (autor/réu) ficam bloqueados após pagamento
        para garantir integridade do processo.
        """
        if not self.is_paid:
            return []

        # Campos que identificam as partes - não podem ser alterados
        locked_prefixes = [
            "autor_",
            "reu_",
            "requerente_",
            "requerido_",
            "rep_autor_",
            "rep_reu_",
            "rep_terceiro_",
            "terceiro_",
        ]

        locked = []
        if self.form_data:
            for key in self.form_data.keys():
                for prefix in locked_prefixes:
                    if key.startswith(prefix):
                        locked.append(key)
                        break

        return locked

    def can_edit_field(self, field_name: str) -> bool:
        """Verifica se um campo específico pode ser editado."""
        if not self.is_paid:
            return True
        return field_name not in self.get_locked_fields()

    def __repr__(self):
        return f"<SavedPetition {self.id} - {self.status}>"


class PetitionAttachment(db.Model):
    """
    Anexos/Provas das petições salvas.
    Permite upload de documentos relacionados ao caso.
    """

    __tablename__ = "petition_attachments"

    id = db.Column(db.Integer, primary_key=True)
    saved_petition_id = db.Column(
        db.Integer, db.ForeignKey("saved_petitions.id"), nullable=False
    )

    # Informações do arquivo
    filename = db.Column(db.String(255), nullable=False)  # Nome original do arquivo
    stored_filename = db.Column(db.String(255), nullable=False)  # Nome no storage
    file_type = db.Column(db.String(100))  # MIME type
    file_size = db.Column(db.Integer)  # Tamanho em bytes

    # Categorização
    category = db.Column(
        db.String(50), default="prova"
    )  # prova, documento, procuracao, etc.
    description = db.Column(db.String(500))  # Descrição do anexo

    # Metadados
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    # Relacionamentos
    saved_petition = db.relationship(
        "SavedPetition",
        backref=db.backref("attachments", lazy="dynamic", cascade="all, delete-orphan"),
    )
    uploaded_by = db.relationship("User")

    def get_file_size_display(self):
        """Retorna o tamanho formatado (KB, MB)."""
        if not self.file_size:
            return "0 KB"
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        else:
            return f"{self.file_size / (1024 * 1024):.1f} MB"

    def get_icon(self):
        """Retorna o ícone baseado no tipo de arquivo."""
        icons = {
            "application/pdf": "fa-file-pdf text-danger",
            "image/jpeg": "fa-file-image text-info",
            "image/png": "fa-file-image text-info",
            "image/gif": "fa-file-image text-info",
            "application/msword": "fa-file-word text-primary",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "fa-file-word text-primary",
            "application/vnd.ms-excel": "fa-file-excel text-success",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "fa-file-excel text-success",
            "text/plain": "fa-file-alt text-secondary",
        }
        return icons.get(self.file_type, "fa-file text-secondary")

    def __repr__(self):
        return f"<PetitionAttachment {self.filename}>"


# =============================================================================
# SISTEMA DE SALDO PARA PETIÇÕES (PAY PER USE)
# =============================================================================


class UserPetitionBalance(db.Model):
    """
    Saldo em R$ do usuário para gerar petições no modelo Pay per Use.
    Diferente de créditos de IA - aqui é valor monetário.
    """

    __tablename__ = "user_petition_balance"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True
    )
    balance = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))  # Saldo em R$
    total_deposited = db.Column(
        db.Numeric(10, 2), default=Decimal("0.00")
    )  # Total depositado
    total_spent = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))  # Total gasto
    total_bonus = db.Column(
        db.Numeric(10, 2), default=Decimal("0.00")
    )  # Total de bônus
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relacionamento
    user = db.relationship(
        "User", backref=db.backref("petition_balance", uselist=False, lazy=True)
    )

    def add_balance(self, amount, source="deposit"):
        """Adiciona saldo (depósito ou bônus)"""
        amount = Decimal(str(amount))
        self.balance += amount
        if source == "deposit":
            self.total_deposited += amount
        elif source == "bonus":
            self.total_bonus += amount
        self.updated_at = datetime.now(timezone.utc)
        return self.balance

    def charge(self, amount):
        """
        Cobra valor do saldo.
        Retorna True se teve saldo suficiente, False caso contrário.
        """
        amount = Decimal(str(amount))
        if self.balance >= amount:
            self.balance -= amount
            self.total_spent += amount
            self.updated_at = datetime.now(timezone.utc)
            return True
        return False

    def has_balance(self, amount):
        """Verifica se tem saldo suficiente"""
        return self.balance >= Decimal(str(amount))

    @staticmethod
    def get_or_create(user_id):
        """Obtém ou cria registro de saldo para o usuário"""
        balance = UserPetitionBalance.query.filter_by(user_id=user_id).first()
        if not balance:
            balance = UserPetitionBalance(user_id=user_id, balance=Decimal("0.00"))
            db.session.add(balance)
            db.session.commit()
        return balance

    def __repr__(self):
        return f"<UserPetitionBalance user={self.user_id} balance=R${self.balance}>"


class PetitionBalanceTransaction(db.Model):
    """
    Histórico de transações do saldo de petições.
    Registra depósitos, gastos com petições, reembolsos, etc.
    """

    __tablename__ = "petition_balance_transactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    transaction_type = db.Column(
        db.String(20), nullable=False
    )  # 'deposit', 'charge', 'refund', 'bonus'
    amount = db.Column(
        db.Numeric(10, 2), nullable=False
    )  # Positivo = entrada, Negativo = saída
    balance_after = db.Column(db.Numeric(10, 2), nullable=False)  # Saldo após transação

    # Detalhes
    description = db.Column(db.String(255))
    petition_id = db.Column(
        db.Integer, db.ForeignKey("saved_petitions.id"), nullable=True
    )
    petition_type_id = db.Column(
        db.Integer, db.ForeignKey("petition_types.id"), nullable=True
    )
    payment_id = db.Column(
        db.Integer, db.ForeignKey("payments.id"), nullable=True
    )  # Referência ao pagamento

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relacionamentos
    user = db.relationship(
        "User", backref=db.backref("petition_balance_transactions", lazy="dynamic")
    )
    petition = db.relationship("SavedPetition", backref="balance_transactions")
    petition_type = db.relationship("PetitionType", backref="balance_transactions")

    def __repr__(self):
        return f"<PetitionBalanceTransaction {self.transaction_type}: R${self.amount}>"


# =============================================================================
# SISTEMA DE CRÉDITOS DE IA
# =============================================================================


class CreditPackage(db.Model):
    """Pacotes de créditos disponíveis para compra"""

    __tablename__ = "credit_packages"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    credits = db.Column(db.Integer, nullable=False)
    bonus_credits = db.Column(db.Integer, default=0)  # Créditos bônus
    price = db.Column(db.Numeric(10, 2), nullable=False)  # Em reais
    original_price = db.Column(db.Numeric(10, 2))  # Preço original (se tiver desconto)
    currency = db.Column(db.String(3), default="BRL")
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)  # Destacado na UI
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    @property
    def total_credits(self):
        """Total de créditos (base + bônus)"""
        return self.credits + (self.bonus_credits or 0)

    @property
    def price_per_credit(self):
        """Preço por crédito"""
        if self.total_credits and self.total_credits > 0:
            return float(self.price) / self.total_credits
        return 0

    def __repr__(self):
        return f"<CreditPackage {self.name}: {self.credits} créditos>"


class UserCredits(db.Model):
    """Saldo de créditos de IA do usuário"""

    __tablename__ = "user_credits"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True
    )
    balance = db.Column(db.Integer, default=0)  # Créditos disponíveis
    total_purchased = db.Column(db.Integer, default=0)  # Total já comprado
    total_used = db.Column(db.Integer, default=0)  # Total já usado
    total_bonus = db.Column(db.Integer, default=0)  # Total de bônus recebido
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relacionamento
    user = db.relationship(
        "User", backref=db.backref("credits", uselist=False, lazy=True)
    )

    def add_credits(self, amount, source="purchase"):
        """Adiciona créditos ao saldo"""
        self.balance += amount
        if source == "purchase":
            self.total_purchased += amount
        elif source == "bonus":
            self.total_bonus += amount
        self.updated_at = datetime.now(timezone.utc)
        return self.balance

    def use_credits(self, amount):
        """Usa créditos (retorna True se teve saldo suficiente)"""
        if self.balance >= amount:
            self.balance -= amount
            self.total_used += amount
            self.updated_at = datetime.now(timezone.utc)

            # Criar notificação se créditos ficarem baixos (≤ 10)
            if self.balance <= 10 and self.balance > 0:
                from app.billing.utils import create_credit_low_notification

                try:
                    create_credit_low_notification(
                        self.user, self.balance, threshold=10
                    )
                except Exception as e:
                    # Não falhar a operação se notificação falhar
                    print(f"Erro ao criar notificação de créditos baixos: {e}")

            return True
        return False

    def has_credits(self, amount=1):
        """Verifica se tem créditos suficientes"""
        return self.balance >= amount

    @staticmethod
    def get_or_create(user_id):
        """Obtém ou cria registro de créditos para o usuário"""
        credits = UserCredits.query.filter_by(user_id=user_id).first()
        if not credits:
            credits = UserCredits(user_id=user_id, balance=0)
            db.session.add(credits)
            db.session.commit()
        return credits

    def __repr__(self):
        return f"<UserCredits user={self.user_id} balance={self.balance}>"


class CreditTransaction(db.Model):
    """Histórico de transações de créditos"""

    __tablename__ = "credit_transactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    transaction_type = db.Column(
        db.String(20), nullable=False
    )  # 'purchase', 'usage', 'refund', 'bonus'
    amount = db.Column(
        db.Integer, nullable=False
    )  # Positivo = crédito, Negativo = débito
    balance_after = db.Column(db.Integer, nullable=False)  # Saldo após transação

    # Detalhes
    description = db.Column(db.String(255))
    package_id = db.Column(
        db.Integer, db.ForeignKey("credit_packages.id"), nullable=True
    )
    generation_id = db.Column(
        db.Integer, db.ForeignKey("ai_generations.id"), nullable=True
    )

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relacionamentos
    user = db.relationship(
        "User", backref=db.backref("credit_transactions", lazy="dynamic")
    )
    package = db.relationship("CreditPackage", backref="transactions")

    def __repr__(self):
        return f"<CreditTransaction {self.transaction_type}: {self.amount}>"


class AIGeneration(db.Model):
    """Registro de cada geração de conteúdo por IA"""

    __tablename__ = "ai_generations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # Tipo de geração
    generation_type = db.Column(
        db.String(50), nullable=False
    )  # 'section', 'full_petition', 'improve', 'analyze'
    petition_type_slug = db.Column(db.String(100))  # Tipo de petição
    section_name = db.Column(db.String(100))  # Nome da seção (se aplicável)

    # Custos
    credits_used = db.Column(db.Integer, nullable=False, default=1)
    model_used = db.Column(db.String(50), default="gpt-4o-mini")  # Modelo usado
    tokens_input = db.Column(db.Integer)
    tokens_output = db.Column(db.Integer)
    tokens_total = db.Column(db.Integer)
    cost_usd = db.Column(db.Numeric(10, 6))  # Custo real em USD

    # Entrada/Saída
    prompt_summary = db.Column(
        db.String(500)
    )  # Resumo do prompt (não o completo por privacidade)
    input_data = db.Column(db.Text)  # Dados de entrada (JSON)
    output_content = db.Column(db.Text)  # Conteúdo gerado

    # Status
    status = db.Column(
        db.String(20), default="completed"
    )  # 'completed', 'failed', 'cancelled'
    error_message = db.Column(db.Text)

    # Feedback
    user_rating = db.Column(db.Integer)  # 1-5 estrelas
    was_used = db.Column(db.Boolean, default=False)  # Se o usuário usou o conteúdo

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime)
    response_time_ms = db.Column(db.Integer)  # Tempo de resposta em ms

    # Relacionamentos
    user = db.relationship("User", backref=db.backref("ai_generations", lazy="dynamic"))
    transaction = db.relationship(
        "CreditTransaction", backref="generation", uselist=False
    )

    def calculate_cost(self):
        """Calcula o custo estimado em USD baseado nos tokens"""
        if not self.tokens_input or not self.tokens_output:
            return 0

        # Preços por 1M tokens (Dezembro 2024)
        prices = {
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "gpt-4o": {"input": 2.50, "output": 10.00},
            "gpt-4-turbo": {"input": 10.00, "output": 30.00},
        }

        model_prices = prices.get(self.model_used, prices["gpt-4o-mini"])
        input_cost = (self.tokens_input / 1_000_000) * model_prices["input"]
        output_cost = (self.tokens_output / 1_000_000) * model_prices["output"]

        self.cost_usd = input_cost + output_cost
        return self.cost_usd

    def __repr__(self):
        return f"<AIGeneration {self.generation_type} - {self.status}>"


class Notification(db.Model):
    """
    Notificações para usuários sobre eventos importantes do sistema.
    """

    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    type = db.Column(
        db.String(50), nullable=False
    )  # 'petition_ready', 'credit_low', 'payment_due', 'password_expiring', 'ai_limit', 'system'
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(500))  # URL para ação relacionada
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    read_at = db.Column(db.DateTime)

    # Relacionamento
    user = db.relationship(
        "User",
        backref=db.backref(
            "notifications", lazy="dynamic", cascade="all, delete-orphan"
        ),
    )

    def mark_as_read(self):
        """Marca a notificação como lida"""
        self.read = True
        self.read_at = datetime.now(timezone.utc)
        db.session.commit()

    @staticmethod
    def create_notification(user_id, notification_type, title, message, link=None):
        """
        Cria uma nova notificação para o usuário.

        Args:
            user_id: ID do usuário
            notification_type: Tipo da notificação
            title: Título da notificação
            message: Mensagem detalhada
            link: URL opcional para ação relacionada

        Returns:
            Notification: Objeto da notificação criada
        """
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            link=link,
        )
        db.session.add(notification)
        db.session.commit()
        return notification

    @staticmethod
    def get_unread_count(user_id):
        """Retorna contagem de notificações não lidas do usuário"""
        return Notification.query.filter_by(user_id=user_id, read=False).count()

    @staticmethod
    def get_recent(user_id, limit=10):
        """Retorna notificações recentes do usuário"""
        return (
            Notification.query.filter_by(user_id=user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
            .all()
        )

    def __repr__(self):
        return f"<Notification {self.type} - User {self.user_id}>"


class NotificationPreferences(db.Model):
    """
    Preferências de notificação por usuário.
    Permite controlar canais, tipos e horários de notificações.
    """

    __tablename__ = "notification_preferences"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True
    )

    # === Canais de Notificação ===
    email_enabled = db.Column(db.Boolean, default=True)
    push_enabled = db.Column(db.Boolean, default=True)
    in_app_enabled = db.Column(db.Boolean, default=True)

    # === Tipos de Notificação (por canal) ===
    # Prazos
    deadline_email = db.Column(db.Boolean, default=True)
    deadline_push = db.Column(db.Boolean, default=True)
    deadline_in_app = db.Column(db.Boolean, default=True)

    # Movimentações processuais
    movement_email = db.Column(db.Boolean, default=True)
    movement_push = db.Column(db.Boolean, default=False)
    movement_in_app = db.Column(db.Boolean, default=True)

    # Pagamentos/Financeiro
    payment_email = db.Column(db.Boolean, default=True)
    payment_push = db.Column(db.Boolean, default=True)
    payment_in_app = db.Column(db.Boolean, default=True)

    # Petições/IA
    petition_email = db.Column(db.Boolean, default=True)
    petition_push = db.Column(db.Boolean, default=False)
    petition_in_app = db.Column(db.Boolean, default=True)

    # Sistema (atualizações, manutenção)
    system_email = db.Column(db.Boolean, default=True)
    system_push = db.Column(db.Boolean, default=False)
    system_in_app = db.Column(db.Boolean, default=True)

    # === Horário de Silêncio (Quiet Hours) ===
    quiet_hours_enabled = db.Column(db.Boolean, default=False)
    quiet_hours_start = db.Column(db.Time, default=None)  # Ex: 22:00
    quiet_hours_end = db.Column(db.Time, default=None)  # Ex: 08:00
    quiet_hours_weekends = db.Column(
        db.Boolean, default=True
    )  # Silenciar finais de semana

    # === Digest/Resumo ===
    digest_enabled = db.Column(db.Boolean, default=False)
    digest_frequency = db.Column(
        db.String(20), default="daily"
    )  # 'daily', 'weekly', 'none'
    digest_time = db.Column(db.Time, default=None)  # Horário de envio do digest
    last_digest_sent = db.Column(db.DateTime)

    # === Prioridade Mínima ===
    # Só notifica se prioridade >= este valor (1=baixa, 2=média, 3=alta, 4=urgente)
    min_priority_email = db.Column(db.Integer, default=1)
    min_priority_push = db.Column(db.Integer, default=2)

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relacionamento
    user = db.relationship(
        "User",
        backref=db.backref("notification_preferences", uselist=False),
    )

    @staticmethod
    def get_or_create(user_id):
        """Obtém ou cria preferências para um usuário."""
        prefs = NotificationPreferences.query.filter_by(user_id=user_id).first()
        if not prefs:
            prefs = NotificationPreferences(user_id=user_id)
            db.session.add(prefs)
            db.session.commit()
        return prefs

    def is_quiet_time(self):
        """Verifica se está no horário de silêncio."""
        if not self.quiet_hours_enabled:
            return False

        now = datetime.now(timezone.utc)
        current_time = now.time()

        # Verificar fim de semana
        if self.quiet_hours_weekends and now.weekday() >= 5:
            return True

        # Verificar horário
        if self.quiet_hours_start and self.quiet_hours_end:
            # Caso normal: início < fim (ex: 22:00 - 08:00)
            if self.quiet_hours_start > self.quiet_hours_end:
                # Horário atravessa meia-noite
                return (
                    current_time >= self.quiet_hours_start
                    or current_time <= self.quiet_hours_end
                )
            else:
                return self.quiet_hours_start <= current_time <= self.quiet_hours_end

        return False

    def should_notify(self, notification_type, channel, priority=2):
        """
        Determina se deve enviar notificação baseado nas preferências.

        Args:
            notification_type: 'deadline', 'movement', 'payment', 'petition', 'system'
            channel: 'email', 'push', 'in_app'
            priority: 1-4 (1=baixa, 4=urgente)

        Returns:
            bool: True se deve notificar
        """
        # Verificar canal global
        if channel == "email" and not self.email_enabled:
            return False
        if channel == "push" and not self.push_enabled:
            return False
        if channel == "in_app" and not self.in_app_enabled:
            return False

        # Verificar tipo específico por canal
        type_field = f"{notification_type}_{channel}"
        if hasattr(self, type_field) and not getattr(self, type_field):
            return False

        # Verificar prioridade mínima (exceto in_app)
        if channel == "email" and priority < self.min_priority_email:
            return False
        if channel == "push" and priority < self.min_priority_push:
            return False

        # Verificar horário de silêncio (urgentes sempre passam)
        if priority < 4 and self.is_quiet_time():
            # Se digest está ativo, adicionar à fila do digest
            if self.digest_enabled and channel == "email":
                return False  # Será enviado no digest
            elif channel != "in_app":  # in_app sempre passa (silencioso)
                return False

        return True

    def __repr__(self):
        return f"<NotificationPreferences User {self.user_id}>"


class NotificationQueue(db.Model):
    """
    Fila de notificações pendentes (para digest e retry).
    """

    __tablename__ = "notification_queue"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)
    channel = db.Column(db.String(20), nullable=False)  # 'email', 'push'
    priority = db.Column(db.Integer, default=2)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(500))
    data = db.Column(db.Text)  # JSON com dados extras

    # Status
    status = db.Column(
        db.String(20), default="pending"
    )  # 'pending', 'sent', 'failed', 'digest'
    retry_count = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text)

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    scheduled_for = db.Column(db.DateTime)  # Para envio agendado
    sent_at = db.Column(db.DateTime)

    # Relacionamento
    user = db.relationship(
        "User", backref=db.backref("notification_queue", lazy="dynamic")
    )

    @staticmethod
    def add_to_queue(
        user_id,
        notification_type,
        channel,
        title,
        message,
        priority=2,
        link=None,
        data=None,
    ):
        """Adiciona notificação à fila."""
        item = NotificationQueue(
            user_id=user_id,
            notification_type=notification_type,
            channel=channel,
            priority=priority,
            title=title,
            message=message,
            link=link,
            data=json.dumps(data) if data else None,
        )
        db.session.add(item)
        db.session.commit()
        return item

    @staticmethod
    def get_pending_digest(user_id):
        """Retorna notificações pendentes para digest."""
        return (
            NotificationQueue.query.filter_by(user_id=user_id, status="digest")
            .order_by(NotificationQueue.created_at.desc())
            .all()
        )

    def __repr__(self):
        return f"<NotificationQueue {self.notification_type} - {self.status}>"


# =============================================================================
# PAYMENT MODELS - Sistema de Pagamentos
# =============================================================================


class Subscription(db.Model):
    """Assinaturas de usuários (planos mensais/anuais)"""

    __tablename__ = "subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # Plano
    plan_type = db.Column(
        db.String(50), nullable=False
    )  # 'basic', 'professional', 'enterprise'
    billing_period = db.Column(
        db.String(20), nullable=False
    )  # '1m', '3m', '6m', '1y', '2y', '3y'
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default="BRL")

    # Status
    status = db.Column(
        db.String(20), default="active"
    )  # active, canceled, past_due, trialing
    trial_ends_at = db.Column(db.DateTime)
    current_period_start = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    current_period_end = db.Column(db.DateTime)
    cancel_at_period_end = db.Column(db.Boolean, default=False)
    canceled_at = db.Column(db.DateTime)

    # Política de reembolso
    refund_policy = db.Column(
        db.String(20), default="no_refund"
    )  # 'no_refund', 'proportional', 'credit'
    refund_amount = db.Column(db.Numeric(10, 2))  # Valor a reembolsar (se aplicável)
    refund_processed_at = db.Column(db.DateTime)

    # Gateway info
    gateway = db.Column(db.String(20))  # 'mercadopago'
    gateway_subscription_id = db.Column(db.String(200), unique=True)
    gateway_customer_id = db.Column(db.String(200))

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = db.relationship("User", backref=db.backref("subscriptions", lazy="dynamic"))
    payments = db.relationship(
        "Payment", backref="subscription", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Subscription {self.id} - User {self.user_id} - {self.plan_type}>"

    def is_active(self):
        """Verifica se a assinatura está ativa"""
        return self.status == "active" and (
            not self.current_period_end
            or self.current_period_end > datetime.now(timezone.utc)
        )

    def cancel(self, immediate=False):
        """Cancela a assinatura - LEGACY: use cancel_with_policy"""
        return self.cancel_with_policy(immediate=immediate)

    def cancel_with_policy(self, immediate=False, refund_policy="no_refund"):
        """
        Cancela assinatura seguindo política padrão.

        Política padrão: Cancelamento ao fim do período, sem reembolso.
        Para planos com desconto, mantém acesso até o fim do período pago.
        """
        # Política padrão: sempre cancelar ao fim do período para planos com desconto
        if self.billing_period != "1m":
            # Planos maiores (3m, 6m, 1y, etc.) sempre cancelam ao fim do período
            self.cancel_at_period_end = True
            self.refund_policy = "no_refund"
            print(
                f"✅ Plano {self.billing_period} cancelado ao fim do período (política padrão)"
            )
        else:
            # Planos mensais podem cancelar imediatamente se solicitado
            if immediate:
                self.status = "canceled"
                self.canceled_at = datetime.now(timezone.utc)
                self.refund_policy = refund_policy
            else:
                self.cancel_at_period_end = True
                self.refund_policy = "no_refund"

        db.session.commit()
        return True


class Expense(db.Model):
    """Despesas e custos operacionais"""

    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    case_id = db.Column(db.Integer)  # Removida FK: tabela cases não existe

    # Detalhes da despesa
    description = db.Column(db.String(500), nullable=False)
    category = db.Column(
        db.String(100)
    )  # 'custas', 'honorarios_perito', 'transporte', etc
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default="BRL")

    # Data e pagamento
    expense_date = db.Column(db.Date, default=lambda: datetime.now(timezone.utc))
    payment_method = db.Column(db.String(50))

    # Reembolso
    reimbursable = db.Column(db.Boolean, default=False)
    reimbursed = db.Column(db.Boolean, default=False)
    reimbursed_date = db.Column(db.Date)

    # Comprovante
    receipt_filename = db.Column(db.String(500))
    receipt_url = db.Column(db.String(500))

    # Metadata
    notes = db.Column(db.Text)

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = db.relationship("User", backref=db.backref("expenses", lazy="dynamic"))

    def __repr__(self):
        return f"<Expense {self.id} - {self.description} - {self.amount}>"

    def to_dict(self):
        return {
            "id": self.id,
            "description": self.description,
            "category": self.category,
            "amount": float(self.amount),
            "expense_date": self.expense_date.isoformat(),
            "reimbursable": self.reimbursable,
            "reimbursed": self.reimbursed,
        }


# =============================================================================
# DEADLINE MODELS - Sistema de Prazos
# =============================================================================


class Deadline(db.Model):
    """Prazos processuais e audiências"""

    __tablename__ = "deadlines"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    case_id = db.Column(db.Integer)  # Removida FK: tabela cases não existe
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"))

    # Detalhes do prazo
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    deadline_type = db.Column(
        db.String(50)
    )  # 'audiencia', 'recurso', 'contestacao', 'peticao'
    deadline_date = db.Column(db.DateTime, nullable=False)

    # Alertas
    alert_days_before = db.Column(db.Integer, default=7)
    alert_sent = db.Column(db.Boolean, default=False)
    alert_sent_at = db.Column(db.DateTime)

    # Status
    status = db.Column(db.String(20), default="pending")  # pending, completed, canceled
    completed_at = db.Column(db.DateTime)
    completion_notes = db.Column(db.Text)

    # Recorrência
    is_recurring = db.Column(db.Boolean, default=False)
    recurrence_pattern = db.Column(db.String(50))  # 'daily', 'weekly', 'monthly'
    recurrence_end_date = db.Column(db.Date)

    # Dias úteis
    count_business_days = db.Column(db.Boolean, default=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = db.relationship("User", backref=db.backref("deadlines", lazy="dynamic"))
    client = db.relationship("Client", backref=db.backref("deadlines", lazy="dynamic"))

    def __repr__(self):
        return f"<Deadline {self.id} - {self.title} - {self.deadline_date}>"

    def days_until(self, use_business_days=None):
        """Calcula dias até o prazo"""
        if use_business_days is None:
            use_business_days = self.count_business_days

        if self.status != "pending":
            return 0

        today = datetime.now(timezone.utc)
        if self.deadline_date <= today:
            return 0

        if use_business_days:
            # Calcular dias úteis (aproximação simples)
            days = (self.deadline_date - today).days
            # Remove aproximadamente 2 dias de fim de semana por semana
            weeks = days // 7
            business_days = days - (weeks * 2)
            return max(0, business_days)
        else:
            return (self.deadline_date - today).days

    def is_urgent(self, days_threshold=3):
        """Verifica se o prazo é urgente"""
        return self.status == "pending" and self.days_until() <= days_threshold

    def is_overdue(self):
        """Verifica se o prazo está vencido"""
        return self.status == "pending" and self.deadline_date < datetime.now(
            timezone.utc
        )

    def mark_completed(self, notes=None):
        """Marca prazo como cumprido"""
        self.status = "completed"
        self.completed_at = datetime.now(timezone.utc)
        if notes:
            self.completion_notes = notes
        db.session.commit()

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "deadline_type": self.deadline_type,
            "deadline_date": self.deadline_date.isoformat(),
            "days_until": self.days_until(),
            "is_urgent": self.is_urgent(),
            "status": self.status,
        }


class Message(db.Model):
    """Mensagens do chat entre advogado e cliente"""

    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    client_id = db.Column(
        db.Integer, db.ForeignKey("client.id")
    )  # Opcional: associar a cliente específico

    # Conteúdo
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default="text")  # text, file, image, system

    # Arquivo anexo
    attachment_filename = db.Column(db.String(500))
    attachment_path = db.Column(db.String(500))
    attachment_size = db.Column(db.Integer)  # Em bytes
    attachment_type = db.Column(db.String(100))  # MIME type

    # Status
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)
    is_deleted_by_sender = db.Column(db.Boolean, default=False)
    is_deleted_by_recipient = db.Column(db.Boolean, default=False)

    # Timestamps
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    sender = db.relationship(
        "User",
        foreign_keys=[sender_id],
        backref=db.backref("sent_messages", lazy="dynamic"),
    )
    recipient = db.relationship(
        "User",
        foreign_keys=[recipient_id],
        backref=db.backref("received_messages", lazy="dynamic"),
    )
    client = db.relationship("Client", backref=db.backref("messages", lazy="dynamic"))

    def __repr__(self):
        return f"<Message {self.id} from {self.sender_id} to {self.recipient_id}>"

    def mark_as_read(self):
        """Marca mensagem como lida"""
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.now(timezone.utc)
            db.session.commit()

    def to_dict(self):
        """Serializa para JSON"""
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "sender_name": self.sender.name if self.sender else None,
            "recipient_id": self.recipient_id,
            "recipient_name": self.recipient.name if self.recipient else None,
            "client_id": self.client_id,
            "content": self.content,
            "message_type": self.message_type,
            "attachment": (
                {
                    "filename": self.attachment_filename,
                    "size": self.attachment_size,
                    "type": self.attachment_type,
                }
                if self.attachment_filename
                else None
            ),
            "is_read": self.is_read,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class ChatRoom(db.Model):
    """Salas de chat entre advogado e cliente"""

    __tablename__ = "chat_rooms"

    id = db.Column(db.Integer, primary_key=True)
    lawyer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"), nullable=False)

    # Metadata
    title = db.Column(db.String(200))  # Opcional: assunto do chat
    is_active = db.Column(db.Boolean, default=True)

    # Última atividade
    last_message_at = db.Column(db.DateTime)
    last_message_preview = db.Column(db.String(200))
    unread_count_lawyer = db.Column(db.Integer, default=0)
    unread_count_client = db.Column(db.Integer, default=0)

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    lawyer = db.relationship(
        "User", backref=db.backref("chat_rooms_as_lawyer", lazy="dynamic")
    )
    client = db.relationship("Client", backref=db.backref("chat_rooms", lazy="dynamic"))

    # Índice único para evitar duplicação
    __table_args__ = (
        db.UniqueConstraint("lawyer_id", "client_id", name="unique_chat_room"),
    )

    def __repr__(self):
        return (
            f"<ChatRoom {self.id} - Lawyer {self.lawyer_id} & Client {self.client_id}>"
        )

    def update_last_message(self, message):
        """Atualiza informações da última mensagem"""
        self.last_message_at = message.created_at
        self.last_message_preview = (
            message.content[:200] if len(message.content) > 200 else message.content
        )

        # Incrementar contador de não lidas
        if message.sender_id == self.lawyer_id:
            self.unread_count_client += 1
        else:
            self.unread_count_lawyer += 1

        db.session.commit()

    def mark_as_read_by(self, user_id):
        """Marca todas mensagens como lidas por um usuário"""
        if user_id == self.lawyer_id:
            self.unread_count_lawyer = 0
        else:
            self.unread_count_client = 0
        db.session.commit()

    def to_dict(self):
        """Serializa para JSON"""
        return {
            "id": self.id,
            "lawyer_id": self.lawyer_id,
            "lawyer_name": self.lawyer.name if self.lawyer else None,
            "client_id": self.client_id,
            "client_name": self.client.name if self.client else None,
            "title": self.title,
            "is_active": self.is_active,
            "last_message_at": self.last_message_at.isoformat()
            if self.last_message_at
            else None,
            "last_message_preview": self.last_message_preview,
            "unread_count_lawyer": self.unread_count_lawyer,
            "unread_count_client": self.unread_count_client,
            "created_at": self.created_at.isoformat(),
        }


class Document(db.Model):
    """Documentos e arquivos dos clientes"""

    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"), nullable=False)

    # Informações do documento
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    document_type = db.Column(
        db.String(50)
    )  # 'contrato', 'peticao', 'procuracao', 'comprovante', 'rg', 'cpf', etc
    category = db.Column(db.String(100))  # Categoria adicional

    # Arquivo
    filename = db.Column(db.String(500), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)  # Em bytes
    file_type = db.Column(db.String(100))  # MIME type
    file_extension = db.Column(db.String(10))  # .pdf, .docx, etc

    # Controle de versão
    version = db.Column(db.Integer, default=1)
    parent_document_id = db.Column(
        db.Integer, db.ForeignKey("documents.id")
    )  # Para versões
    is_latest_version = db.Column(db.Boolean, default=True)

    # Visibilidade
    is_visible_to_client = db.Column(db.Boolean, default=True)
    is_confidential = db.Column(db.Boolean, default=False)

    # Status
    status = db.Column(db.String(20), default="active")  # active, archived, deleted

    # Metadata
    tags = db.Column(db.String(500))  # Tags separadas por vírgula
    notes = db.Column(db.Text)  # Notas internas

    # Timestamps
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    last_accessed_at = db.Column(db.DateTime)

    # Relationships
    user = db.relationship("User", backref=db.backref("documents", lazy="dynamic"))
    client = db.relationship("Client", backref=db.backref("documents", lazy="dynamic"))
    versions = db.relationship(
        "Document",
        backref=db.backref("parent_document", remote_side=[id]),
        lazy="dynamic",
    )

    def __repr__(self):
        return f"<Document {self.id} - {self.title}>"

    def get_size_formatted(self):
        """Retorna tamanho formatado do arquivo"""
        if not self.file_size:
            return "N/A"

        size = self.file_size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def mark_accessed(self):
        """Marca documento como acessado"""
        self.last_accessed_at = datetime.now(timezone.utc)
        db.session.commit()

    def create_new_version(
        self, new_file_path, new_filename, new_file_size, uploaded_by_user_id
    ):
        """Cria nova versão do documento"""
        # Marcar versão atual como não sendo a mais recente
        self.is_latest_version = False

        # Criar nova versão
        new_version = Document(
            user_id=uploaded_by_user_id,
            client_id=self.client_id,
            title=self.title,
            description=self.description,
            document_type=self.document_type,
            category=self.category,
            filename=new_filename,
            file_path=new_file_path,
            file_size=new_file_size,
            file_type=self.file_type,
            file_extension=self.file_extension,
            version=self.version + 1,
            parent_document_id=self.id,
            is_latest_version=True,
            is_visible_to_client=self.is_visible_to_client,
            is_confidential=self.is_confidential,
            tags=self.tags,
        )

        db.session.add(new_version)
        db.session.commit()
        return new_version

    def archive(self):
        """Arquivar documento"""
        self.status = "archived"
        db.session.commit()

    def delete_document(self):
        """Marcar como deletado (soft delete)"""
        self.status = "deleted"
        db.session.commit()

    def to_dict(self):
        """Serializa para JSON"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "document_type": self.document_type,
            "category": self.category,
            "filename": self.filename,
            "file_size": self.file_size,
            "file_size_formatted": self.get_size_formatted(),
            "file_type": self.file_type,
            "file_extension": self.file_extension,
            "version": self.version,
            "is_latest_version": self.is_latest_version,
            "is_visible_to_client": self.is_visible_to_client,
            "is_confidential": self.is_confidential,
            "status": self.status,
            "tags": self.tags.split(",") if self.tags else [],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_accessed_at": (
                self.last_accessed_at.isoformat() if self.last_accessed_at else None
            ),
            "client": {"id": self.client.id, "name": self.client.name}
            if self.client
            else None,
        }


# =============================================================================
# ROADMAP MODELS - Sistema de Roadmap e Sugestões
# =============================================================================


class RoadmapCategory(db.Model):
    """Categorias para organizar itens do roadmap"""

    __tablename__ = "roadmap_categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50), default="fa-lightbulb")  # Ícone FontAwesome
    color = db.Column(db.String(20), default="primary")  # Cor Bootstrap
    order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relacionamento
    items = db.relationship(
        "RoadmapItem",
        backref="category",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="RoadmapItem.priority.desc()",
    )

    def __repr__(self):
        return f"<RoadmapCategory {self.name}>"


class RoadmapItem(db.Model):
    """Itens do roadmap com sugestões de implementação"""

    __tablename__ = "roadmap_items"

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(
        db.Integer, db.ForeignKey("roadmap_categories.id"), nullable=False
    )

    # Informações básicas
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    detailed_description = db.Column(db.Text)  # Descrição mais detalhada

    # Status e prioridade
    status = db.Column(
        db.String(20), default="planned"
    )  # planned, in_progress, completed, cancelled, on_hold
    priority = db.Column(db.String(20), default="medium")  # low, medium, high, critical
    estimated_effort = db.Column(
        db.String(20), default="medium"
    )  # small, medium, large, xlarge

    # Visibilidade
    visible_to_users = db.Column(
        db.Boolean, default=False
    )  # Aparece para usuários normais?
    internal_only = db.Column(db.Boolean, default=False)  # Apenas para uso interno?
    show_new_badge = db.Column(
        db.Boolean, default=False
    )  # Mostrar badge "Novo" no roadmap público

    # Timeline
    planned_start_date = db.Column(db.Date)
    planned_completion_date = db.Column(db.Date)
    actual_start_date = db.Column(db.Date)
    actual_completion_date = db.Column(db.Date)
    implemented_at = db.Column(db.DateTime)  # Data efetiva de implementação

    # Benefícios e impacto
    business_value = db.Column(db.Text)  # Valor para o negócio
    technical_complexity = db.Column(
        db.String(20), default="medium"
    )  # low, medium, high
    user_impact = db.Column(db.String(20), default="medium")  # low, medium, high

    # Matriz de Priorização (1-5 escala)
    impact_score = db.Column(
        db.Integer, default=3
    )  # 1=baixo, 5=crítico. Para admin visualizar prioridade
    effort_score = db.Column(
        db.Integer, default=3
    )  # 1=fácil, 5=muito complexo. Para admin calcular ROI

    # Dependências
    dependencies = db.Column(db.Text)  # IDs de outros itens separados por vírgula
    blockers = db.Column(db.Text)  # Bloqueadores conhecidos

    # Metadata
    tags = db.Column(db.String(500))  # Tags separadas por vírgula
    notes = db.Column(db.Text)  # Notas internas

    # Controle
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    assigned_to = db.Column(db.Integer, db.ForeignKey("user.id"))
    last_updated_by = db.Column(db.Integer, db.ForeignKey("user.id"))

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relacionamentos
    creator = db.relationship("User", foreign_keys=[created_by])
    assignee = db.relationship("User", foreign_keys=[assigned_to])
    updater = db.relationship("User", foreign_keys=[last_updated_by])

    def __repr__(self):
        return f"<RoadmapItem {self.title} - {self.status}>"

    def get_status_display(self):
        """Retorna o status formatado com cores Bootstrap vibrantes"""
        status_map = {
            "planned": ("Planejado", "secondary"),  # Cinza - futuro
            "in_progress": ("Em Andamento", "primary"),  # Azul - ativo
            "completed": ("Concluído", "success"),  # Verde - pronto
            "cancelled": ("Cancelado", "danger"),  # Vermelho - bloqueado
            "on_hold": ("Em Espera", "warning"),  # Amarelo - pausado
        }
        return status_map.get(self.status, ("Desconhecido", "secondary"))

    def get_priority_display(self):
        """Retorna a prioridade formatada com cores Bootstrap vibrantes"""
        priority_map = {
            "low": ("Baixa", "success"),  # Verde - tranquilo
            "medium": ("Média", "info"),  # Azul - moderado
            "high": ("Alta", "warning"),  # Amarelo/Laranja - atração
            "critical": ("Crítica", "danger"),  # Vermelho - urgente
        }
        return priority_map.get(self.priority, ("Média", "info"))

    def get_effort_display(self):
        """Retorna o esforço estimado formatado"""
        effort_map = {
            "small": ("Pequeno", "1-2 dias"),
            "medium": ("Médio", "1-2 semanas"),
            "large": ("Grande", "1-2 meses"),
            "xlarge": ("Muito Grande", "3+ meses"),
        }
        return effort_map.get(self.estimated_effort, ("Médio", "1-2 semanas"))

    def get_tags_list(self):
        """Retorna lista de tags"""
        return [tag.strip() for tag in self.tags.split(",")] if self.tags else []

    def get_dependencies_list(self):
        """Retorna lista de dependências"""
        return (
            [dep.strip() for dep in self.dependencies.split(",")]
            if self.dependencies
            else []
        )

    def is_overdue(self):
        """Verifica se está atrasado"""
        if self.status in ["completed", "cancelled"]:
            return False
        if self.planned_completion_date:
            return datetime.now(timezone.utc).date() > self.planned_completion_date
        return False

    def get_progress_percentage(self):
        """Retorna porcentagem de progresso baseada no status"""
        progress_map = {
            "planned": 0,
            "in_progress": 50,
            "completed": 100,
            "cancelled": 0,
            "on_hold": 25,
        }
        return progress_map.get(self.status, 0)

    def to_dict(self):
        """Serializa para JSON"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "status_display": self.get_status_display(),
            "priority": self.priority,
            "priority_display": self.get_priority_display(),
            "estimated_effort": self.estimated_effort,
            "effort_display": self.get_effort_display(),
            "visible_to_users": self.visible_to_users,
            "internal_only": self.internal_only,
            "show_new_badge": self.show_new_badge,
            "planned_start_date": (
                self.planned_start_date.isoformat() if self.planned_start_date else None
            ),
            "planned_completion_date": (
                self.planned_completion_date.isoformat()
                if self.planned_completion_date
                else None
            ),
            "actual_start_date": (
                self.actual_start_date.isoformat() if self.actual_start_date else None
            ),
            "actual_completion_date": (
                self.actual_completion_date.isoformat()
                if self.actual_completion_date
                else None
            ),
            "implemented_at": self.implemented_at.isoformat()
            if self.implemented_at
            else None,
            "business_value": self.business_value,
            "technical_complexity": self.technical_complexity,
            "user_impact": self.user_impact,
            "tags": self.get_tags_list(),
            "is_overdue": self.is_overdue(),
            "progress_percentage": self.get_progress_percentage(),
            "category": (
                {
                    "id": self.category.id,
                    "name": self.category.name,
                    "slug": self.category.slug,
                    "color": self.category.color,
                    "icon": self.category.icon,
                }
                if self.category
                else None
            ),
        }


class RoadmapFeedback(db.Model):
    """Feedback dos usuários sobre funcionalidades implementadas"""

    __tablename__ = "roadmap_feedback"

    id = db.Column(db.Integer, primary_key=True)
    roadmap_item_id = db.Column(
        db.Integer, db.ForeignKey("roadmap_items.id"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # Avaliação
    rating = db.Column(db.Integer, nullable=False)  # 1-5 estrelas
    rating_category = db.Column(
        db.String(50)
    )  # 'usabilidade', 'funcionalidade', 'performance', 'design', 'geral'

    # Feedback detalhado
    title = db.Column(db.String(200))  # Título opcional do feedback
    comment = db.Column(db.Text)  # Comentário detalhado
    pros = db.Column(db.Text)  # Pontos positivos
    cons = db.Column(db.Text)  # Pontos de melhoria
    suggestions = db.Column(db.Text)  # Sugestões específicas

    # Contexto de uso
    usage_frequency = db.Column(
        db.String(20)
    )  # 'daily', 'weekly', 'monthly', 'rarely', 'first_time'
    ease_of_use = db.Column(
        db.String(20)
    )  # 'very_easy', 'easy', 'neutral', 'difficult', 'very_difficult'

    # Metadata
    user_agent = db.Column(db.String(500))  # Browser/dispositivo usado
    ip_address = db.Column(db.String(45))  # IPv4/IPv6
    session_id = db.Column(db.String(100))  # Para agrupar feedback da mesma sessão

    # Status
    is_anonymous = db.Column(db.Boolean, default=False)  # Feedback anônimo?
    is_featured = db.Column(db.Boolean, default=False)  # Destacar no admin?
    status = db.Column(
        db.String(20), default="pending"
    )  # pending, reviewed, addressed, dismissed

    # Resposta do admin
    admin_response = db.Column(db.Text)  # Resposta da equipe
    responded_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    responded_at = db.Column(db.DateTime)

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relacionamentos
    roadmap_item = db.relationship(
        "RoadmapItem",
        backref=db.backref("feedback", lazy="dynamic", cascade="all, delete-orphan"),
    )
    user = db.relationship("User", foreign_keys=[user_id])
    responder = db.relationship("User", foreign_keys=[responded_by])

    def __repr__(self):
        return f"<RoadmapFeedback {self.id} - Item {self.roadmap_item_id} - {self.rating}⭐>"

    def get_rating_display(self):
        """Retorna representação visual da avaliação"""
        stars = "⭐" * self.rating
        return f"{self.rating}/5 {stars}"

    def get_rating_category_display(self):
        """Retorna categoria formatada"""
        categories = {
            "usabilidade": "Usabilidade",
            "funcionalidade": "Funcionalidade",
            "performance": "Performance",
            "design": "Design",
            "geral": "Avaliação Geral",
        }
        return categories.get(self.rating_category, self.rating_category.title())

    def get_usage_frequency_display(self):
        """Retorna frequência de uso formatada"""
        frequencies = {
            "daily": "Diariamente",
            "weekly": "Semanalmente",
            "monthly": "Mensalmente",
            "rarely": "Raramente",
            "first_time": "Primeira vez",
        }
        return frequencies.get(self.usage_frequency, self.usage_frequency.title())

    def get_ease_of_use_display(self):
        """Retorna facilidade de uso formatada"""
        ease_levels = {
            "very_easy": "Muito fácil",
            "easy": "Fácil",
            "neutral": "Neutro",
            "difficult": "Difícil",
            "very_difficult": "Muito difícil",
        }
        return ease_levels.get(self.ease_of_use, self.ease_of_use.title())

    def get_status_display(self):
        """Retorna status formatado"""
        status_map = {
            "pending": ("Pendente", "warning"),
            "reviewed": ("Revisado", "info"),
            "addressed": ("Tratado", "success"),
            "dismissed": ("Descartado", "secondary"),
        }
        return status_map.get(self.status, ("Desconhecido", "secondary"))

    def mark_as_reviewed(self, admin_user=None):
        """Marca feedback como revisado"""
        self.status = "reviewed"
        if admin_user:
            self.responded_by = admin_user.id
            self.responded_at = datetime.now(timezone.utc)
        db.session.commit()

    def add_response(self, response_text, admin_user):
        """Adiciona resposta do admin"""
        self.admin_response = response_text
        self.responded_by = admin_user.id
        self.responded_at = datetime.now(timezone.utc)
        self.status = "addressed"
        db.session.commit()

    def to_dict(self):
        """Serializa para JSON"""
        return {
            "id": self.id,
            "roadmap_item_id": self.roadmap_item_id,
            "user_id": self.user_id,
            "rating": self.rating,
            "rating_display": self.get_rating_display(),
            "rating_category": self.rating_category,
            "rating_category_display": self.get_rating_category_display(),
            "title": self.title,
            "comment": self.comment,
            "pros": self.pros,
            "cons": self.cons,
            "suggestions": self.suggestions,
            "usage_frequency": self.usage_frequency,
            "usage_frequency_display": self.get_usage_frequency_display(),
            "ease_of_use": self.ease_of_use,
            "ease_of_use_display": self.get_ease_of_use_display(),
            "is_anonymous": self.is_anonymous,
            "is_featured": self.is_featured,
            "status": self.status,
            "status_display": self.get_status_display(),
            "admin_response": self.admin_response,
            "responded_at": self.responded_at.isoformat()
            if self.responded_at
            else None,
            "created_at": self.created_at.isoformat(),
            "user": (
                {
                    "id": self.user.id,
                    "name": self.user.name,
                    "email": self.user.email,
                }
                if not self.is_anonymous and self.user
                else None
            ),
            "responder": (
                {
                    "id": self.responder.id,
                    "name": self.responder.name,
                }
                if self.responder
                else None
            ),
        }


# =============================================================================
# Table Preferences - Per-user table configuration persistence
# =============================================================================


class TablePreference(db.Model):
    """Preferences for table views stored per-user and per-view.

    Example preferences JSON structure:
    {
        "columns": ["id", "title", "category"],
        "order": [[0, "asc"]],
        "length": 25,
        "search": {"value": "", "regex": false}
    }
    """

    __tablename__ = "table_preferences"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    view_key = db.Column(db.String(200), nullable=False)
    preferences = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (db.UniqueConstraint("user_id", "view_key", name="uq_user_view"),)

    # Relationship
    user = db.relationship(
        "User", backref=db.backref("table_preferences", lazy="dynamic")
    )

    def __repr__(self):
        return f"<TablePreference user={self.user_id} view={self.view_key}>"

    @classmethod
    def get_for_user(cls, user_id, view_key):
        pref = cls.query.filter_by(user_id=user_id, view_key=view_key).first()
        return pref.preferences if pref else None

    @classmethod
    def set_for_user(cls, user_id, view_key, preferences):
        pref = cls.query.filter_by(user_id=user_id, view_key=view_key).first()
        if not pref:
            pref = cls(user_id=user_id, view_key=view_key, preferences=preferences)
            db.session.add(pref)
        else:
            pref.preferences = preferences
        db.session.commit()


# =============================================================================
# LGPD COMPLIANCE MODELS
# =============================================================================


class DataConsent(db.Model):
    """Registro de consentimentos para tratamento de dados pessoais"""

    __tablename__ = "data_consents"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # Tipo de consentimento
    consent_type = db.Column(
        db.String(50), nullable=False
    )  # 'marketing', 'analytics', 'processing'
    consent_purpose = db.Column(db.Text, nullable=False)  # Descrição do propósito

    # Status do consentimento
    consented = db.Column(db.Boolean, default=True)
    consent_version = db.Column(db.String(20), default="1.0")  # Versão da política

    # Datas
    consented_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    withdrawn_at = db.Column(db.DateTime, nullable=True)  # Quando retirou consentimento
    expires_at = db.Column(db.DateTime, nullable=True)  # Expiração do consentimento

    # Metadados
    ip_address = db.Column(db.String(45))  # IPv4/IPv6
    user_agent = db.Column(db.Text)
    consent_method = db.Column(db.String(50))  # 'web_form', 'api', 'admin'

    # Relacionamentos
    user = db.relationship("User", backref=db.backref("data_consents", lazy="dynamic"))

    def __repr__(self):
        return f"<DataConsent user={self.user_id} type={self.consent_type} consented={self.consented}>"

    def withdraw_consent(self):
        """Retira o consentimento"""
        self.consented = False
        self.withdrawn_at = datetime.now(timezone.utc)
        db.session.commit()

    def is_valid(self):
        """Verifica se o consentimento é válido"""
        if not self.consented:
            return False
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True


class DataProcessingLog(db.Model):
    """Log de processamento de dados pessoais (LGPD Art. 37)"""

    __tablename__ = "data_processing_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # Dados do processamento
    action = db.Column(
        db.String(50), nullable=False
    )  # 'collect', 'process', 'share', 'delete'
    data_category = db.Column(
        db.String(100), nullable=False
    )  # 'personal', 'financial', 'health'
    data_fields = db.Column(db.Text)  # JSON dos campos processados
    purpose = db.Column(db.Text, nullable=False)

    # Contexto
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    endpoint = db.Column(db.String(200))  # Rota/endpoint onde ocorreu
    request_id = db.Column(db.String(100))  # ID único da requisição

    # Legal
    legal_basis = db.Column(db.String(100))  # Base legal (consent, contract, etc.)
    consent_id = db.Column(db.Integer, db.ForeignKey("data_consents.id"), nullable=True)

    # Timestamps
    processed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relacionamentos
    user = db.relationship(
        "User", backref=db.backref("data_processing_logs", lazy="dynamic")
    )
    consent = db.relationship(
        "DataConsent", backref=db.backref("processing_logs", lazy="dynamic")
    )

    def __repr__(self):
        return f"<DataProcessingLog user={self.user_id} action={self.action}>"


class AnonymizationRequest(db.Model):
    """Solicitações de anonimização de dados"""

    __tablename__ = "anonymization_requests"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # Status da solicitação
    status = db.Column(
        db.String(20), default="pending"
    )  # 'pending', 'processing', 'completed', 'failed'
    request_reason = db.Column(db.Text, nullable=False)

    # Dados a anonimizar
    data_categories = db.Column(db.Text)  # JSON: ['personal', 'financial', 'documents']
    anonymization_method = db.Column(
        db.String(50), default="pseudonymization"
    )  # 'pseudonymization', 'deletion'

    # Processo
    requested_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    processed_at = db.Column(db.DateTime, nullable=True)
    processed_by = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=True
    )  # Admin que processou

    # Resultado
    anonymized_data = db.Column(db.Text)  # JSON com dados antes/depois
    notes = db.Column(db.Text)  # Notas do processamento

    # Relacionamentos
    user = db.relationship(
        "User",
        foreign_keys=[user_id],
        backref=db.backref("anonymization_requests", lazy="dynamic"),
    )
    processor = db.relationship(
        "User",
        foreign_keys=[processed_by],
        backref=db.backref("processed_anonymizations", lazy="dynamic"),
    )

    def __repr__(self):
        return f"<AnonymizationRequest user={self.user_id} status={self.status}>"

    def mark_completed(self, processor_id, notes=None):
        """Marca a solicitação como concluída"""
        self.status = "completed"
        self.processed_at = datetime.now(timezone.utc)
        self.processed_by = processor_id
        if notes:
            self.notes = notes
        db.session.commit()

    def mark_failed(self, processor_id, notes=None):
        """Marca a solicitação como falhada"""
        self.status = "failed"
        self.processed_at = datetime.now(timezone.utc)
        self.processed_by = processor_id
        if notes:
            self.notes = notes
        db.session.commit()


class DeletionRequest(db.Model):
    """Solicitações de exclusão de dados (Direito ao Esquecimento - LGPD Art. 18)"""

    __tablename__ = "deletion_requests"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # Status da solicitação
    status = db.Column(
        db.String(20), default="pending"
    )  # 'pending', 'processing', 'completed', 'rejected'
    request_reason = db.Column(db.Text, nullable=False)

    # Escopo da exclusão
    deletion_scope = db.Column(
        db.Text
    )  # JSON: ['account', 'data', 'documents', 'logs']
    retention_reason = db.Column(
        db.Text, nullable=True
    )  # Motivo para manter alguns dados

    # Processo legal
    legal_basis = db.Column(
        db.Text, nullable=True
    )  # Base legal para rejeição/manutenção
    appeal_deadline = db.Column(db.DateTime, nullable=True)  # Prazo para recurso

    # Processo
    requested_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    processed_at = db.Column(db.DateTime, nullable=True)
    processed_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    # Resultado
    deletion_summary = db.Column(db.Text)  # JSON com resumo do que foi excluído
    rejection_reason = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text)

    # Relacionamentos
    user = db.relationship(
        "User",
        foreign_keys=[user_id],
        backref=db.backref("deletion_requests", lazy="dynamic"),
    )
    processor = db.relationship(
        "User",
        foreign_keys=[processed_by],
        backref=db.backref("processed_deletions", lazy="dynamic"),
    )

    def __repr__(self):
        return f"<DeletionRequest user={self.user_id} status={self.status}>"

    def approve_deletion(self, processor_id, summary, notes=None):
        """Aprova a solicitação de exclusão"""
        self.status = "completed"
        self.processed_at = datetime.now(timezone.utc)
        self.processed_by = processor_id
        self.deletion_summary = summary
        if notes:
            self.notes = notes
        db.session.commit()

    def reject_deletion(self, processor_id, reason, legal_basis=None, notes=None):
        """Rejeita a solicitação de exclusão"""
        self.status = "rejected"
        self.processed_at = datetime.now(timezone.utc)
        self.processed_by = processor_id
        self.rejection_reason = reason
        self.legal_basis = legal_basis
        if notes:
            self.notes = notes
        db.session.commit()


class PetitionModel(db.Model):
    """
    Modelo de Petição - Define a configuração completa de um tipo de petição.
    Separa a classificação (PetitionType) da configuração (PetitionModel).
    """

    __tablename__ = "petition_models"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(
        db.String(500), nullable=False
    )  # Nomes de petições podem ser longos
    slug = db.Column(
        db.String(120), unique=True, nullable=False
    )  # Slug truncado automaticamente
    description = db.Column(db.Text)

    # Relacionamento com o tipo de petição (classificação)
    petition_type_id = db.Column(
        db.Integer, db.ForeignKey("petition_types.id"), nullable=False
    )

    # Status
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Configurações do modelo
    use_dynamic_form = db.Column(db.Boolean, default=True)

    # Template personalizado do modelo (conteúdo Jinja2)
    template_content = db.Column(db.Text)

    # Quem criou
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    # Relacionamentos
    petition_type = db.relationship("PetitionType", backref="models")
    creator = db.relationship("User", foreign_keys=[created_by])

    def get_sections_ordered(self):
        """Retorna as seções deste modelo ordenadas."""
        return self.model_sections.order_by(PetitionModelSection.order).all()

    def __repr__(self):
        return f"<PetitionModel {self.slug}>"


class PetitionModelSection(db.Model):
    """
    Relaciona modelos de petição com suas seções (muitos para muitos com metadados).
    This is the PRIMARY way to manage sections for petitions.
    """

    __tablename__ = "petition_model_sections"

    id = db.Column(db.Integer, primary_key=True)
    petition_model_id = db.Column(
        db.Integer, db.ForeignKey("petition_models.id"), nullable=False
    )
    section_id = db.Column(
        db.Integer, db.ForeignKey("petition_sections.id"), nullable=False
    )
    order = db.Column(db.Integer, default=0)  # Ordem desta seção neste modelo
    is_required = db.Column(db.Boolean, default=False)  # Seção obrigatória?
    is_expanded = db.Column(db.Boolean, default=True)  # Começa expandida?

    # Sobrescrever campos específicos para este modelo (opcional)
    # Ex: {"author_name": {"label": "Nome do Requerente"}} - muda apenas o label
    field_overrides = db.Column(db.JSON, default=dict)

    # Relacionamentos
    petition_model = db.relationship(
        "PetitionModel",
        backref=db.backref(
            "model_sections", lazy="dynamic", order_by="PetitionModelSection.order"
        ),
    )
    section = db.relationship(
        "PetitionSection", backref=db.backref("model_sections", lazy="dynamic")
    )

    def get_fields(self):
        """Retorna os campos da seção com overrides aplicados para este modelo."""
        import copy

        fields = copy.deepcopy(self.section.get_fields()) if self.section else []
        overrides = self.field_overrides or {}

        for field in fields:
            field_name = field.get("name")
            if field_name in overrides:
                field.update(overrides[field_name])

        return fields

    def __repr__(self):
        return f"<PetitionModelSection model={self.petition_model_id} section={self.section_id}>"


class Process(db.Model):
    """
    Modelo para acompanhamento de processos judiciais.
    Centraliza informações sobre processos em andamento.
    """

    __tablename__ = "processes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # Identificação do processo
    process_number = db.Column(
        db.String(30), unique=True, index=True
    )  # Número oficial do processo
    title = db.Column(db.String(300), nullable=False)  # Título descritivo

    # Informações judiciais
    court = db.Column(
        db.String(100)
    )  # Tribunal/Justiça (Federal, Estadual, Trabalhista, etc.)
    court_instance = db.Column(db.String(100))  # Instância (1ª, 2ª, etc.)
    jurisdiction = db.Column(db.String(100))  # Vara/Órgão julgador
    district = db.Column(db.String(100))  # Comarca/Foro
    judge = db.Column(db.String(200))  # Juiz/Relator

    # Partes envolvidas
    plaintiff = db.Column(db.String(300))  # Autor/Requerente
    defendant = db.Column(db.String(300))  # Réu/Requerido

    # Status e andamento
    status = db.Column(db.String(50), default="pending_distribution", index=True)
    # Status possíveis: pending_distribution, distributed, ongoing, suspended, archived, finished

    # Datas importantes
    distribution_date = db.Column(db.Date)  # Data de distribuição
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relacionamentos
    user = db.relationship("User", backref=db.backref("processes", lazy="dynamic"))

    # Petições relacionadas (muitos-para-muitos)
    petitions = db.relationship(
        "SavedPetition",
        secondary="process_petitions",
        backref=db.backref("processes", lazy="dynamic"),
    )

    # Cliente relacionado
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"))
    client = db.relationship("Client", backref=db.backref("processes", lazy="dynamic"))

    # Controle de prazos
    next_deadline = db.Column(db.Date)  # Próximo prazo processual
    deadline_description = db.Column(db.String(300))  # Descrição do prazo
    priority = db.Column(db.String(20), default="normal")  # low, normal, high, urgent

    def get_status_display(self):
        """Retorna o status formatado para exibição."""
        status_map = {
            "pending_distribution": ("Aguardando Distribuição", "warning"),
            "distributed": ("Distribuído", "info"),
            "ongoing": ("Em Andamento", "primary"),
            "suspended": ("Suspenso", "secondary"),
            "archived": ("Arquivado", "dark"),
            "finished": ("Finalizado", "success"),
        }
        return status_map.get(self.status, ("Desconhecido", "secondary"))

    def get_status_color(self):
        """Retorna apenas a cor do status."""
        return self.get_status_display()[1]

    def get_status_text(self):
        """Retorna apenas o texto do status."""
        return self.get_status_display()[0]

    def get_priority_display(self):
        """Retorna a prioridade formatada."""
        priority_map = {
            "low": ("Baixa", "secondary"),
            "normal": ("Normal", "info"),
            "high": ("Alta", "warning"),
            "urgent": ("Urgente", "danger"),
        }
        return priority_map.get(self.priority, ("Normal", "info"))

    def is_overdue(self):
        """Verifica se há prazo vencido."""
        if self.next_deadline:
            from datetime import date

            return self.next_deadline < date.today()
        return False

    def days_until_deadline(self):
        """Retorna dias até o próximo prazo."""
        if self.next_deadline:
            from datetime import date

            return (self.next_deadline - date.today()).days
        return None

    def __repr__(self):
        return f"<Process {self.process_number or 'Sem número'} - {self.title}>"


# Modelo para notificações de processos
class ProcessNotification(db.Model):
    """
    Notificações relacionadas a processos judiciais.
    """

    __tablename__ = "process_notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    process_id = db.Column(db.Integer, db.ForeignKey("processes.id"), nullable=True)

    # Tipo de notificação
    notification_type = db.Column(
        db.String(50), nullable=False
    )  # deadline, status_change, new_document, etc.

    # Conteúdo
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)

    # Status
    read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)

    # Metadados
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    sent_at = db.Column(db.DateTime)  # Quando foi enviada por email/SMS

    # Dados adicionais em JSON
    extra_data = db.Column(db.JSON, default=dict)

    # Relacionamentos
    user = db.relationship(
        "User", backref=db.backref("process_notifications", lazy="dynamic")
    )
    process = db.relationship(
        "Process", backref=db.backref("notifications", lazy="dynamic")
    )

    def mark_as_read(self):
        """Marca a notificação como lida."""
        self.read = True
        self.read_at = datetime.now(timezone.utc)

    def __repr__(self):
        return f"<ProcessNotification {self.notification_type} - {self.title}>"


# Tabela de associação para relação muitos-para-muitos entre processos e petições
process_petitions = db.Table(
    "process_petitions",
    db.Column(
        "process_id", db.Integer, db.ForeignKey("processes.id"), primary_key=True
    ),
    db.Column(
        "petition_id", db.Integer, db.ForeignKey("saved_petitions.id"), primary_key=True
    ),
    db.Column("created_at", db.DateTime, default=lambda: datetime.now(timezone.utc)),
    db.Column(
        "relation_type", db.String(50), default="related"
    ),  # initial, contestation, appeal, etc.
)


class ProcessMovement(db.Model):
    """
    Histórico de andamentos/movimentações processuais.
    Registra todas as movimentações do processo no tribunal.
    """

    __tablename__ = "process_movements"

    id = db.Column(db.Integer, primary_key=True)
    process_id = db.Column(db.Integer, db.ForeignKey("processes.id"), nullable=False)

    # Data e descrição
    movement_date = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.Text, nullable=False)

    # Tipo de andamento
    movement_type = db.Column(
        db.String(100)
    )  # 'distribuicao', 'audiencia', 'decisao', 'recurso', etc.

    # Detalhes adicionais
    court_decision = db.Column(db.Text)  # Decisão do juiz/relator
    deadline_extension = db.Column(db.Date)  # Novo prazo se aplicável
    responsible_party = db.Column(db.String(200))  # Parte responsável pela movimentação

    # Documentos relacionados
    document_url = db.Column(db.String(500))  # Link para documento no sistema judicial
    internal_notes = db.Column(db.Text)  # Anotações internas do advogado

    # Status da movimentação
    is_important = db.Column(
        db.Boolean, default=False
    )  # Marca movimentações importantes
    requires_action = db.Column(db.Boolean, default=False)  # Requer ação do advogado

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relacionamentos
    process = db.relationship(
        "Process",
        backref=db.backref(
            "movements", lazy="dynamic", order_by="ProcessMovement.movement_date.desc()"
        ),
    )

    def __repr__(self):
        return f"<ProcessMovement {self.process_id} - {self.movement_date} - {self.description[:50]}>"


class ProcessCost(db.Model):
    """
    Controle de custas judiciais e honorários.
    Registra todos os custos relacionados ao processo.
    """

    __tablename__ = "process_costs"

    id = db.Column(db.Integer, primary_key=True)
    process_id = db.Column(db.Integer, db.ForeignKey("processes.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # Tipo de custo
    cost_type = db.Column(
        db.String(50), nullable=False
    )  # 'custas', 'honorarios', 'taxas', 'despesas'
    description = db.Column(db.String(300), nullable=False)

    # Valores
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default="BRL")  # BRL, USD, EUR

    # Status do pagamento
    payment_status = db.Column(
        db.String(20), default="pending"
    )  # pending, paid, overdue, cancelled

    # Datas
    due_date = db.Column(db.Date)
    payment_date = db.Column(db.Date)

    # Detalhes específicos
    court_fee_type = db.Column(
        db.String(100)
    )  # Para custas: 'distribuicao', 'taxa_judiciaria', etc.
    attorney_fee_type = db.Column(
        db.String(100)
    )  # Para honorários: 'inicial', 'audiencia', 'sustentacao', etc.

    # Documentos comprobatórios
    receipt_url = db.Column(db.String(500))  # Link para recibo/comprovante
    invoice_number = db.Column(db.String(100))  # Número da nota fiscal

    # Observações
    notes = db.Column(db.Text)

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relacionamentos
    process = db.relationship("Process", backref=db.backref("costs", lazy="dynamic"))
    user = db.relationship("User", backref=db.backref("process_costs", lazy="dynamic"))

    def get_status_display(self):
        """Retorna o status formatado para exibição."""
        status_map = {
            "pending": ("Pendente", "warning"),
            "paid": ("Pago", "success"),
            "overdue": ("Vencido", "danger"),
            "cancelled": ("Cancelado", "secondary"),
        }
        return status_map.get(self.status, ("Desconhecido", "secondary"))

    def get_type_display(self):
        """Retorna o tipo formatado."""
        type_map = {
            "custas": "Custas Judiciais",
            "honorarios": "Honorários",
            "taxas": "Taxas",
            "despesas": "Despesas",
        }
        return type_map.get(self.cost_type, self.cost_type.title())

    def is_overdue(self):
        """Verifica se o custo está vencido."""
        if self.payment_status == "pending" and self.due_date:
            from datetime import date

            return self.due_date < date.today()
        return False

    def __repr__(self):
        return f"<ProcessCost {self.process_id} - {self.cost_type} - R$ {self.amount}>"


class ProcessAttachment(db.Model):
    """
    Anexos específicos para processos judiciais.
    Documentos relacionados diretamente ao processo.
    """

    __tablename__ = "process_attachments"

    id = db.Column(db.Integer, primary_key=True)
    process_id = db.Column(db.Integer, db.ForeignKey("processes.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # Informações do arquivo
    filename = db.Column(db.String(500), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    file_type = db.Column(db.String(100))  # MIME type
    file_extension = db.Column(db.String(10))

    # Metadados
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    document_type = db.Column(
        db.String(100)
    )  # 'peticao', 'decisao', 'prova', 'contrato', etc.

    # Relacionamento com movimentação (opcional)
    movement_id = db.Column(db.Integer, db.ForeignKey("process_movements.id"))

    # Controle de versão
    version = db.Column(db.Integer, default=1)
    parent_attachment_id = db.Column(
        db.Integer, db.ForeignKey("process_attachments.id")
    )
    is_latest_version = db.Column(db.Boolean, default=True)

    # Visibilidade
    is_confidential = db.Column(db.Boolean, default=False)
    is_visible_to_client = db.Column(db.Boolean, default=False)

    # Status
    status = db.Column(db.String(20), default="active")  # active, archived, deleted

    # Tags para busca
    tags = db.Column(db.String(500))  # Separadas por vírgula

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    last_accessed_at = db.Column(db.DateTime)

    # Relacionamentos
    process = db.relationship(
        "Process", backref=db.backref("attachments", lazy="dynamic")
    )
    user = db.relationship(
        "User", backref=db.backref("process_attachments", lazy="dynamic")
    )
    movement = db.relationship(
        "ProcessMovement", backref=db.backref("attachments", lazy="dynamic")
    )
    versions = db.relationship(
        "ProcessAttachment",
        backref=db.backref("parent_attachment", remote_side=[id]),
        lazy="dynamic",
    )

    def get_size_formatted(self):
        """Retorna tamanho formatado do arquivo."""
        if not self.file_size:
            return "N/A"

        size = self.file_size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def mark_accessed(self):
        """Marca anexo como acessado."""
        self.last_accessed_at = datetime.now(timezone.utc)
        db.session.commit()

    def create_new_version(self, new_path, new_size=None):
        """Cria nova versão do anexo."""
        # Marcar versão atual como não mais recente
        self.is_latest_version = False
        db.session.commit()

        # Criar nova versão
        new_version = ProcessAttachment(
            process_id=self.process_id,
            user_id=self.user_id,
            filename=self.filename,
            file_path=new_path,
            file_size=new_size or self.file_size,
            file_type=self.file_type,
            file_extension=self.file_extension,
            title=self.title,
            description=self.description,
            document_type=self.document_type,
            movement_id=self.movement_id,
            version=self.version + 1,
            parent_attachment_id=self.id,
            is_latest_version=True,
            is_confidential=self.is_confidential,
            is_visible_to_client=self.is_visible_to_client,
            tags=self.tags,
        )
        db.session.add(new_version)
        db.session.commit()
        return new_version

    def __repr__(self):
        return f"<ProcessAttachment {self.process_id} - {self.title}>"


class CalendarEvent(db.Model):
    """
    Eventos do calendário jurídico.
    Inclui audiências, prazos, reuniões e compromissos relacionados aos processos.
    """

    __tablename__ = "calendar_events"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # Título e descrição
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)

    # Data e hora
    start_datetime = db.Column(db.DateTime, nullable=False)
    end_datetime = db.Column(db.DateTime, nullable=False)
    all_day = db.Column(db.Boolean, default=False)

    # Localização
    location = db.Column(db.String(300))  # Endereço físico ou virtual
    virtual_link = db.Column(db.String(500))  # Link para reunião virtual

    # Tipo de evento
    event_type = db.Column(
        db.String(50), nullable=False
    )  # 'audiencia', 'prazo', 'reuniao', 'compromisso'
    priority = db.Column(
        db.String(20), default="normal"
    )  # 'low', 'normal', 'high', 'urgent'

    # Relacionamento com processo (opcional)
    process_id = db.Column(db.Integer, db.ForeignKey("processes.id"))
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"))

    # Status
    status = db.Column(
        db.String(20), default="scheduled"
    )  # 'scheduled', 'confirmed', 'completed', 'cancelled'
    reminder_sent = db.Column(db.Boolean, default=False)
    reminder_minutes_before = db.Column(
        db.Integer, default=60
    )  # Minutos antes do lembrete

    # Recorrência (para eventos recorrentes)
    is_recurring = db.Column(db.Boolean, default=False)
    recurrence_rule = db.Column(db.String(200))  # RRULE do iCalendar
    recurrence_end_date = db.Column(db.Date)

    # Participantes
    participants = db.Column(db.Text)  # JSON com lista de participantes
    attendees = db.Column(db.Text)  # JSON com confirmações de presença

    # Notas e observações
    notes = db.Column(db.Text)
    outcome = db.Column(db.Text)  # Resultado/ata da reunião

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relacionamentos
    user = db.relationship(
        "User", backref=db.backref("calendar_events", lazy="dynamic")
    )
    process = db.relationship(
        "Process", backref=db.backref("calendar_events", lazy="dynamic")
    )
    client = db.relationship(
        "Client", backref=db.backref("calendar_events", lazy="dynamic")
    )

    def get_event_type_display(self):
        """Retorna o tipo de evento formatado."""
        type_map = {
            "audiencia": ("Audiência", "court"),
            "prazo": ("Prazo Processual", "clock"),
            "reuniao": ("Reunião", "users"),
            "compromisso": ("Compromisso", "calendar"),
        }
        return type_map.get(self.event_type, (self.event_type.title(), "calendar"))

    def get_priority_display(self):
        """Retorna a prioridade formatada."""
        priority_map = {
            "low": ("Baixa", "secondary"),
            "normal": ("Normal", "info"),
            "high": ("Alta", "warning"),
            "urgent": ("Urgente", "danger"),
        }
        return priority_map.get(self.priority, ("Normal", "info"))

    def get_status_display(self):
        """Retorna o status formatado."""
        status_map = {
            "scheduled": ("Agendado", "primary"),
            "confirmed": ("Confirmado", "success"),
            "completed": ("Concluído", "secondary"),
            "cancelled": ("Cancelado", "danger"),
        }
        return status_map.get(self.status, ("Desconhecido", "secondary"))

    def is_upcoming(self, hours=24):
        """Verifica se o evento é nos próximos X horas."""
        now = datetime.now(timezone.utc)
        time_diff = self.start_datetime - now
        return time_diff.total_seconds() > 0 and time_diff.total_seconds() <= (
            hours * 3600
        )

    def needs_reminder(self):
        """Verifica se precisa enviar lembrete."""
        if self.reminder_sent or self.status in ["completed", "cancelled"]:
            return False

        now = datetime.now(timezone.utc)
        reminder_time = self.start_datetime - timedelta(
            minutes=self.reminder_minutes_before
        )
        return now >= reminder_time

    def to_dict(self):
        """Serializa para JSON."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "start_datetime": self.start_datetime.isoformat(),
            "end_datetime": self.end_datetime.isoformat(),
            "all_day": self.all_day,
            "location": self.location,
            "virtual_link": self.virtual_link,
            "event_type": self.event_type,
            "event_type_display": self.get_event_type_display(),
            "priority": self.priority,
            "priority_display": self.get_priority_display(),
            "status": self.status,
            "status_display": self.get_status_display(),
            "process_id": self.process_id,
            "client_id": self.client_id,
            "notes": self.notes,
            "outcome": self.outcome,
            "created_at": self.created_at.isoformat(),
        }

    def __repr__(self):
        return f"<CalendarEvent {self.title} - {self.start_datetime}>"


class ProcessAutomation(db.Model):
    """
    Regras de automação para processos judiciais.
    Define ações automáticas baseadas em eventos ou condições.
    """

    __tablename__ = "process_automations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # Configuração da automação
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)

    # Gatilho (trigger)
    trigger_type = db.Column(
        db.String(50), nullable=False
    )  # 'movement', 'deadline', 'status_change', 'date'
    trigger_condition = db.Column(db.JSON, default=dict)  # Condições específicas

    # Ação a ser executada
    action_type = db.Column(
        db.String(50), nullable=False
    )  # 'notification', 'email', 'task', 'reminder'
    action_config = db.Column(db.JSON, default=dict)  # Configuração da ação

    # Escopo
    applies_to_all_processes = db.Column(db.Boolean, default=False)
    specific_processes = db.Column(db.Text)  # JSON com IDs de processos específicos
    process_types = db.Column(db.Text)  # JSON com tipos de processo

    # Estatísticas
    execution_count = db.Column(db.Integer, default=0)
    last_executed_at = db.Column(db.DateTime)
    success_count = db.Column(db.Integer, default=0)
    failure_count = db.Column(db.Integer, default=0)

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relacionamentos
    user = db.relationship(
        "User", backref=db.backref("process_automations", lazy="dynamic")
    )

    def should_trigger(self, event_data):
        """Verifica se a automação deve ser acionada para determinado evento."""
        # Implementar lógica de verificação de condições
        if not self.is_active:
            return False

        # Verificar tipo de gatilho
        if self.trigger_type != event_data.get("trigger_type"):
            return False

        # Verificar condições específicas
        conditions = self.trigger_condition or {}
        for key, value in conditions.items():
            if event_data.get(key) != value:
                return False

        # Verificar escopo
        if not self.applies_to_all_processes:
            process_id = event_data.get("process_id")
            if process_id:
                specific_ids = self.get_specific_process_ids()
                if specific_ids and process_id not in specific_ids:
                    return False

        return True

    def get_specific_process_ids(self):
        """Retorna lista de IDs de processos específicos."""
        if not self.specific_processes:
            return []
        try:
            return json.loads(self.specific_processes)
        except (TypeError, ValueError):
            return []

    def execute_action(self, event_data):
        """Executa a ação da automação."""
        try:
            self.execution_count += 1
            self.last_executed_at = datetime.now(timezone.utc)

            # Implementar diferentes tipos de ação
            if self.action_type == "notification":
                self._execute_notification(event_data)
            elif self.action_type == "email":
                self._execute_email(event_data)
            elif self.action_type == "task":
                self._execute_task(event_data)
            elif self.action_type == "reminder":
                self._execute_reminder(event_data)

            self.success_count += 1
            db.session.commit()
            return True

        except Exception as e:
            self.failure_count += 1
            db.session.commit()
            print(f"Erro ao executar automação {self.id}: {str(e)}")
            return False

    def _execute_notification(self, event_data):
        """Executa ação de notificação."""
        config = self.action_config or {}
        title = config.get("title", "Notificação Automática")
        message = config.get("message", "Uma automação foi acionada.")

        # Criar notificação
        from app.models import Notification

        Notification.create_notification(
            user_id=self.user_id,
            notification_type="automation",
            title=title,
            message=message,
        )

    def _execute_email(self, event_data):
        """Executa ação de envio de email."""
        # Implementar envio de email
        pass

    def _execute_task(self, event_data):
        """Executa ação de criação de tarefa."""
        # Implementar criação de tarefa
        pass

    def _execute_reminder(self, event_data):
        """Executa ação de lembrete."""
        # Implementar lembrete
        pass

    def __repr__(self):
        return f"<ProcessAutomation {self.name} - {self.trigger_type} -> {self.action_type}>"


class ProcessReport(db.Model):
    """
    Relatórios avançados sobre processos e performance.
    Armazena métricas e estatísticas para análise.
    """

    __tablename__ = "process_reports"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # Tipo de relatório
    report_type = db.Column(
        db.String(50), nullable=False
    )  # 'performance', 'financial', 'timeline', 'custom'
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    # Período do relatório
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    # Filtros aplicados
    filters = db.Column(db.JSON, default=dict)  # Filtros usados na geração

    # Dados do relatório (JSON)
    report_data = db.Column(db.JSON, default=dict)

    # Métricas calculadas
    total_processes = db.Column(db.Integer, default=0)
    active_processes = db.Column(db.Integer, default=0)
    completed_processes = db.Column(db.Integer, default=0)
    total_costs = db.Column(db.Numeric(12, 2), default=Decimal("0.00"))
    average_resolution_time = db.Column(db.Integer)  # Em dias

    # Status
    status = db.Column(
        db.String(20), default="generating"
    )  # 'generating', 'completed', 'failed'
    error_message = db.Column(db.Text)

    # Arquivo gerado (opcional)
    file_path = db.Column(db.String(500))
    file_size = db.Column(db.Integer)

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relacionamentos
    user = db.relationship(
        "User", backref=db.backref("process_reports", lazy="dynamic")
    )

    def generate_report(self):
        """Gera o relatório baseado no tipo."""
        try:
            self.status = "generating"
            db.session.commit()

            if self.report_type == "performance":
                self._generate_performance_report()
            elif self.report_type == "financial":
                self._generate_financial_report()
            elif self.report_type == "timeline":
                self._generate_timeline_report()
            elif self.report_type == "custom":
                self._generate_custom_report()

            self.status = "completed"
            self.completed_at = datetime.now(timezone.utc)
            db.session.commit()

        except Exception as e:
            self.status = "failed"
            self.error_message = str(e)
            db.session.commit()

    def _generate_performance_report(self):
        """Gera relatório de performance dos processos."""
        from app.models import Process, ProcessCost, ProcessMovement

        # Consultar processos no período
        processes = Process.query.filter(
            Process.user_id == self.user_id,
            Process.created_at >= self.start_date,
            Process.created_at <= self.end_date,
        ).all()

        # Calcular métricas
        self.total_processes = len(processes)
        self.active_processes = len(
            [p for p in processes if p.status in ["ongoing", "distributed"]]
        )
        self.completed_processes = len([p for p in processes if p.status == "finished"])

        # Custos totais
        total_costs = (
            db.session.query(db.func.sum(ProcessCost.amount))
            .filter(
                ProcessCost.user_id == self.user_id,
                ProcessCost.created_at >= self.start_date,
                ProcessCost.created_at <= self.end_date,
            )
            .scalar()
            or 0
        )
        self.total_costs = Decimal(str(total_costs))

        # Tempo médio de resolução
        completed_processes = [p for p in processes if p.status == "finished"]
        if completed_processes:
            total_days = 0
            count = 0
            for process in completed_processes:
                if process.distribution_date and process.updated_at:
                    days = (process.updated_at.date() - process.distribution_date).days
                    if days > 0:
                        total_days += days
                        count += 1
            if count > 0:
                self.average_resolution_time = total_days // count

        # Dados detalhados
        self.report_data = {
            "processes_by_status": self._count_processes_by_status(processes),
            "processes_by_court": self._count_processes_by_court(processes),
            "monthly_distribution": self._get_monthly_distribution(),
            "cost_breakdown": self._get_cost_breakdown(),
            "performance_metrics": {
                "completion_rate": (
                    (self.completed_processes / self.total_processes * 100)
                    if self.total_processes > 0
                    else 0
                ),
                "active_rate": (
                    (self.active_processes / self.total_processes * 100)
                    if self.total_processes > 0
                    else 0
                ),
                "average_cost_per_process": (
                    float(self.total_costs) / self.total_processes
                    if self.total_processes > 0
                    else 0
                ),
            },
        }

    def _generate_financial_report(self):
        """Gera relatório financeiro."""
        from app.models import ProcessCost

        costs = ProcessCost.query.filter(
            ProcessCost.user_id == self.user_id,
            ProcessCost.created_at >= self.start_date,
            ProcessCost.created_at <= self.end_date,
        ).all()

        # Agrupar custos por tipo
        cost_by_type = {}
        cost_by_status = {}
        monthly_costs = {}

        for cost in costs:
            # Por tipo
            cost_type = cost.get_type_display()
            if cost_type not in cost_by_type:
                cost_by_type[cost_type] = 0
            cost_by_type[cost_type] += float(cost.amount)

            # Por status
            status_display = cost.get_status_display()[0]
            if status_display not in cost_by_status:
                cost_by_status[status_display] = 0
            cost_by_status[status_display] += float(cost.amount)

            # Por mês
            month_key = cost.created_at.strftime("%Y-%m")
            if month_key not in monthly_costs:
                monthly_costs[month_key] = 0
            monthly_costs[month_key] += float(cost.amount)

        self.report_data = {
            "cost_by_type": cost_by_type,
            "cost_by_status": cost_by_status,
            "monthly_costs": monthly_costs,
            "total_costs": float(self.total_costs),
            "overdue_costs": len([c for c in costs if c.is_overdue()]),
        }

    def _generate_timeline_report(self):
        """Gera relatório de timeline dos processos."""
        from app.models import ProcessMovement

        movements = (
            ProcessMovement.query.join(Process)
            .filter(
                Process.user_id == self.user_id,
                ProcessMovement.movement_date >= self.start_date,
                ProcessMovement.movement_date <= self.end_date,
            )
            .all()
        )

        # Agrupar movimentações por tipo e mês
        movements_by_type = {}
        movements_by_month = {}

        for movement in movements:
            # Por tipo
            if movement.movement_type not in movements_by_type:
                movements_by_type[movement.movement_type] = 0
            movements_by_type[movement.movement_type] += 1

            # Por mês
            month_key = movement.movement_date.strftime("%Y-%m")
            if month_key not in movements_by_month:
                movements_by_month[month_key] = 0
            movements_by_month[month_key] += 1

        self.report_data = {
            "movements_by_type": movements_by_type,
            "movements_by_month": movements_by_month,
            "total_movements": len(movements),
            "average_movements_per_process": (
                len(movements) / self.total_processes if self.total_processes > 0 else 0
            ),
        }

    def _generate_custom_report(self):
        """Gera relatório customizado."""
        # Implementar lógica para relatórios customizados
        pass

    def _count_processes_by_status(self, processes):
        """Conta processos por status."""
        status_count = {}
        for process in processes:
            status_text = process.get_status_display()[0]
            status_count[status_text] = status_count.get(status_text, 0) + 1
        return status_count

    def _count_processes_by_court(self, processes):
        """Conta processos por tribunal."""
        court_count = {}
        for process in processes:
            court = process.court or "Não informado"
            court_count[court] = court_count.get(court, 0) + 1
        return court_count

    def _get_monthly_distribution(self):
        """Distribuição mensal de processos."""
        # Implementar distribuição mensal
        return {}

    def _get_cost_breakdown(self):
        """Quebramento de custos."""
        # Implementar quebramento de custos
        return {}

    def to_dict(self):
        """Serializa para JSON."""
        return {
            "id": self.id,
            "report_type": self.report_type,
            "title": self.title,
            "description": self.description,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "status": self.status,
            "total_processes": self.total_processes,
            "total_costs": float(self.total_costs),
            "report_data": self.report_data,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
        }

    def __repr__(self):
        return f"<ProcessReport {self.title} - {self.report_type}>"


# Modelo para auditoria de alterações
class AuditLog(db.Model):
    """Log de auditoria para rastrear alterações em entidades importantes"""

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Quem fez a alteração
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    user = db.relationship("User", backref="audit_logs")

    # Entidade afetada
    entity_type = db.Column(
        db.String(50), nullable=False
    )  # 'user', 'client', 'petition', etc.
    entity_id = db.Column(db.Integer, nullable=False)  # ID da entidade

    # Tipo de ação
    action = db.Column(
        db.String(50), nullable=False
    )  # 'create', 'update', 'delete', 'login', 'logout'

    # Detalhes da alteração
    old_values = db.Column(db.Text)  # JSON com valores antigos
    new_values = db.Column(db.Text)  # JSON com valores novos
    changed_fields = db.Column(db.Text)  # JSON com campos alterados

    # Contexto da requisição
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4/IPv6
    user_agent = db.Column(db.Text, nullable=True)
    session_id = db.Column(db.String(255), nullable=True)

    # Descrição da alteração
    description = db.Column(db.Text, nullable=True)

    # Metadados adicionais
    additional_metadata = db.Column(db.Text)  # JSON com dados adicionais

    def __init__(
        self,
        user_id=None,
        entity_type=None,
        entity_id=None,
        action=None,
        old_values=None,
        new_values=None,
        changed_fields=None,
        ip_address=None,
        user_agent=None,
        session_id=None,
        description=None,
        additional_metadata=None,
    ):
        self.user_id = user_id
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.action = action
        self.old_values = json.dumps(old_values) if old_values else None
        self.new_values = json.dumps(new_values) if new_values else None
        self.changed_fields = json.dumps(changed_fields) if changed_fields else None
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.session_id = session_id
        self.description = description
        self.additional_metadata = (
            json.dumps(additional_metadata) if additional_metadata else None
        )

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "user_email": self.user.email if self.user else None,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "action": self.action,
            "old_values": json.loads(self.old_values) if self.old_values else None,
            "new_values": json.loads(self.new_values) if self.new_values else None,
            "changed_fields": json.loads(self.changed_fields)
            if self.changed_fields
            else None,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "session_id": self.session_id,
            "description": self.description,
            "metadata": json.loads(self.additional_metadata)
            if self.additional_metadata
            else None,
        }

    def __repr__(self):
        return f"<AuditLog {self.entity_type}:{self.entity_id} - {self.action} by {self.user_id}>"


# =============================================================================
# LGPD - DEANONYMIZATION REQUESTS (Reversão de Anonimização)
# =============================================================================


class DeanonymizationRequest(db.Model):
    """Solicitações de reversão de anonimização de dados (LGPD Art. 18)"""

    __tablename__ = "deanonymization_requests"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    anonymization_request_id = db.Column(
        db.Integer, db.ForeignKey("anonymization_requests.id"), nullable=False
    )

    # Status
    status = db.Column(
        db.String(20), default="pending"
    )  # 'pending', 'approved', 'rejected'
    request_reason = db.Column(db.Text, nullable=False)

    # Datas
    requested_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    processed_at = db.Column(db.DateTime, nullable=True)
    processed_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    # Admin notes e resultado
    admin_notes = db.Column(db.Text)
    rejection_reason = db.Column(db.Text)
    restored_data = db.Column(db.Text)  # JSON com dados restaurados

    # Relacionamentos
    user = db.relationship(
        "User",
        foreign_keys=[user_id],
        backref=db.backref("deanonymization_requests", lazy="dynamic"),
    )
    anonymization_request = db.relationship(
        "AnonymizationRequest",
        foreign_keys=[anonymization_request_id],
        backref=db.backref("deanonymization_requests", lazy="dynamic"),
    )
    processor = db.relationship(
        "User",
        foreign_keys=[processed_by_id],
        backref=db.backref("processed_deanonymizations", lazy="dynamic"),
    )

    def __repr__(self):
        return f"<DeanonymizationRequest user={self.user_id} status={self.status}>"

    def to_dict(self):
        return {
            "id": self.id,
            "status": self.status,
            "request_reason": self.request_reason,
            "requested_at": self.requested_at.isoformat(),
            "processed_at": self.processed_at.isoformat()
            if self.processed_at
            else None,
            "admin_notes": self.admin_notes,
            "rejection_reason": self.rejection_reason,
        }


class AgendaBlock(db.Model):
    """
    Bloqueios de agenda do usuário.
    Permite configurar horários/dias em que o usuário não está disponível.
    Exemplos: Segunda, Quarta e Sexta ocupados / Sexta à tarde indisponível
    """

    __tablename__ = "agenda_blocks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # Nome do bloqueio (ex: "Aulas na Faculdade", "Reunião de Equipe")
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    # Tipo de bloqueio
    block_type = db.Column(
        db.String(30), nullable=False, default="recurring"
    )  # 'recurring' (recorrente), 'single' (único), 'period' (período)

    # Para bloqueios recorrentes (semanais)
    # Dias da semana: 0=Segunda, 1=Terça, 2=Quarta, 3=Quinta, 4=Sexta, 5=Sábado, 6=Domingo
    weekdays = db.Column(db.String(50))  # JSON array: [0, 2, 4] = Seg, Qua, Sex

    # Horário do bloqueio
    start_time = db.Column(db.Time)  # Hora início (ex: 14:00)
    end_time = db.Column(db.Time)  # Hora fim (ex: 18:00)
    all_day = db.Column(db.Boolean, default=False)  # Dia inteiro

    # Para bloqueios de período específico
    start_date = db.Column(db.Date)  # Data início
    end_date = db.Column(db.Date)  # Data fim

    # Período do dia (alternativa ao horário específico)
    day_period = db.Column(
        db.String(20)
    )  # 'morning' (manhã), 'afternoon' (tarde), 'evening' (noite), 'all_day'

    # Cor para exibição no calendário
    color = db.Column(db.String(20), default="#6c757d")

    # Status
    is_active = db.Column(db.Boolean, default=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relacionamentos
    user = db.relationship("User", backref=db.backref("agenda_blocks", lazy="dynamic"))

    def __repr__(self):
        return f"<AgendaBlock {self.title} user={self.user_id}>"

    def get_weekdays_display(self):
        """Retorna os dias da semana formatados."""
        if not self.weekdays:
            return ""

        import json

        days_map = {
            0: "Segunda",
            1: "Terça",
            2: "Quarta",
            3: "Quinta",
            4: "Sexta",
            5: "Sábado",
            6: "Domingo",
        }
        try:
            days = json.loads(self.weekdays)
            return ", ".join([days_map.get(d, "") for d in days])
        except:
            return ""

    def get_period_display(self):
        """Retorna o período do dia formatado."""
        period_map = {
            "morning": "Manhã (08:00 - 12:00)",
            "afternoon": "Tarde (12:00 - 18:00)",
            "evening": "Noite (18:00 - 22:00)",
            "all_day": "Dia Inteiro",
        }
        return period_map.get(self.day_period, "")

    def get_time_display(self):
        """Retorna o horário formatado."""
        if self.all_day:
            return "Dia inteiro"
        if self.day_period:
            return self.get_period_display()
        if self.start_time and self.end_time:
            return f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"
        return ""

    def to_calendar_events(self, start_range, end_range):
        """
        Gera eventos de calendário para o período especificado.
        Útil para exibir os bloqueios no FullCalendar.
        """
        import json
        from datetime import datetime, timedelta

        events = []

        if self.block_type == "single" and self.start_date:
            # Bloqueio único
            start_dt = datetime.combine(
                self.start_date, self.start_time or datetime.min.time()
            )
            end_dt = datetime.combine(
                self.end_date or self.start_date, self.end_time or datetime.max.time()
            )

            if start_dt.date() >= start_range and start_dt.date() <= end_range:
                events.append(
                    {
                        "id": f"block_{self.id}",
                        "title": f"🚫 {self.title}",
                        "start": start_dt.isoformat(),
                        "end": end_dt.isoformat(),
                        "allDay": self.all_day,
                        "color": self.color,
                        "display": "block",
                        "classNames": ["agenda-block"],
                        "extendedProps": {
                            "type": "block",
                            "block_id": self.id,
                            "editable": False,
                        },
                    }
                )

        elif self.block_type == "recurring" and self.weekdays:
            # Bloqueio recorrente
            try:
                weekdays = json.loads(self.weekdays)
            except:
                weekdays = []

            current = start_range
            while current <= end_range:
                # Python: weekday() retorna 0=Segunda, 6=Domingo
                if current.weekday() in weekdays:
                    # Determinar horários baseado no período ou horário específico
                    if self.all_day:
                        start_dt = datetime.combine(current, datetime.min.time())
                        end_dt = datetime.combine(
                            current, datetime.max.time().replace(microsecond=0)
                        )
                    elif self.day_period:
                        periods = {
                            "morning": (
                                datetime.strptime("08:00", "%H:%M").time(),
                                datetime.strptime("12:00", "%H:%M").time(),
                            ),
                            "afternoon": (
                                datetime.strptime("12:00", "%H:%M").time(),
                                datetime.strptime("18:00", "%H:%M").time(),
                            ),
                            "evening": (
                                datetime.strptime("18:00", "%H:%M").time(),
                                datetime.strptime("22:00", "%H:%M").time(),
                            ),
                        }
                        period_times = periods.get(
                            self.day_period, (datetime.min.time(), datetime.max.time())
                        )
                        start_dt = datetime.combine(current, period_times[0])
                        end_dt = datetime.combine(current, period_times[1])
                    else:
                        start_dt = datetime.combine(
                            current, self.start_time or datetime.min.time()
                        )
                        end_dt = datetime.combine(
                            current, self.end_time or datetime.max.time()
                        )

                    events.append(
                        {
                            "id": f"block_{self.id}_{current.isoformat()}",
                            "title": f"🚫 {self.title}",
                            "start": start_dt.isoformat(),
                            "end": end_dt.isoformat(),
                            "allDay": self.all_day,
                            "color": self.color,
                            "display": "block",
                            "classNames": ["agenda-block"],
                            "extendedProps": {
                                "type": "block",
                                "block_id": self.id,
                                "editable": False,
                            },
                        }
                    )

                current += timedelta(days=1)

        elif self.block_type == "period" and self.start_date:
            # Bloqueio de período (férias, licença, etc.)
            start = self.start_date
            end = self.end_date or self.start_date

            # Iterar por cada dia do período
            current = max(start, start_range)
            final = min(end, end_range)

            while current <= final:
                if self.all_day:
                    start_dt = datetime.combine(current, datetime.min.time())
                    end_dt = datetime.combine(
                        current, datetime.max.time().replace(microsecond=0)
                    )
                elif self.day_period:
                    periods = {
                        "morning": (
                            datetime.strptime("08:00", "%H:%M").time(),
                            datetime.strptime("12:00", "%H:%M").time(),
                        ),
                        "afternoon": (
                            datetime.strptime("12:00", "%H:%M").time(),
                            datetime.strptime("18:00", "%H:%M").time(),
                        ),
                        "evening": (
                            datetime.strptime("18:00", "%H:%M").time(),
                            datetime.strptime("22:00", "%H:%M").time(),
                        ),
                    }
                    period_times = periods.get(
                        self.day_period, (datetime.min.time(), datetime.max.time())
                    )
                    start_dt = datetime.combine(current, period_times[0])
                    end_dt = datetime.combine(current, period_times[1])
                else:
                    start_dt = datetime.combine(
                        current, self.start_time or datetime.min.time()
                    )
                    end_dt = datetime.combine(
                        current, self.end_time or datetime.max.time()
                    )

                events.append(
                    {
                        "id": f"block_{self.id}_{current.isoformat()}",
                        "title": f"🚫 {self.title}",
                        "start": start_dt.isoformat(),
                        "end": end_dt.isoformat(),
                        "allDay": self.all_day,
                        "color": self.color,
                        "display": "block",
                        "classNames": ["agenda-block"],
                        "extendedProps": {
                            "type": "block",
                            "block_id": self.id,
                            "editable": False,
                        },
                    }
                )

                current += timedelta(days=1)

        return events

    def to_dict(self):
        import json

        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "block_type": self.block_type,
            "weekdays": json.loads(self.weekdays) if self.weekdays else [],
            "weekdays_display": self.get_weekdays_display(),
            "start_time": self.start_time.strftime("%H:%M")
            if self.start_time
            else None,
            "end_time": self.end_time.strftime("%H:%M") if self.end_time else None,
            "all_day": self.all_day,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "day_period": self.day_period,
            "period_display": self.get_period_display(),
            "time_display": self.get_time_display(),
            "color": self.color,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class TemplateExample(db.Model):
    """
    Armazena templates exemplares aprovados para uso como referência na geração com IA.
    Implementa few-shot learning - a IA aprende com exemplos de alta qualidade.
    """

    __tablename__ = "template_examples"

    id = db.Column(db.Integer, primary_key=True)

    # Informações do template
    name = db.Column(db.String(255), nullable=False)  # Nome descritivo
    description = db.Column(db.Text)  # Descrição do tipo de petição
    template_content = db.Column(db.Text, nullable=False)  # O template Jinja2

    # Categorização
    petition_type_id = db.Column(
        db.Integer, db.ForeignKey("petition_types.id"), nullable=True
    )
    petition_type = db.relationship("PetitionType")

    # Tags para busca (ex: "civel,cobranca,indenizacao")
    tags = db.Column(db.String(500))

    # Qualidade e uso
    quality_score = db.Column(db.Float, default=5.0)  # 1.0-5.0 (estrelas)
    usage_count = db.Column(
        db.Integer, default=0
    )  # Quantas vezes foi usado como exemplo
    is_active = db.Column(db.Boolean, default=True)

    # Origem
    source = db.Column(db.String(50), default="manual")  # manual, ai_approved, imported
    original_model_id = db.Column(
        db.Integer, db.ForeignKey("petition_models.id"), nullable=True
    )

    # Metadados
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    creator = db.relationship("User", foreign_keys=[created_by])
    original_model = db.relationship("PetitionModel", foreign_keys=[original_model_id])

    @classmethod
    def get_best_examples(cls, petition_type_id=None, tags=None, limit=2):
        """
        Retorna os melhores templates exemplares para uso no prompt.
        IMPORTANTE: Retorna APENAS exemplos do mesmo tipo de petição para evitar
        misturar contextos (ex: ação civil vs criminal).
        """
        query = cls.query.filter(cls.is_active.is_(True))

        # OBRIGATÓRIO: Filtrar por tipo de petição
        # Não usar exemplos de outros tipos para evitar contaminação de contexto
        if petition_type_id:
            query = query.filter(cls.petition_type_id == petition_type_id)
        else:
            # Se não especificou tipo, não retorna exemplos
            # É melhor não ter exemplo do que ter exemplo errado
            return []

        # Filtrar por tags se especificado (refinamento adicional)
        if tags:
            for tag in tags[:3]:  # Máximo 3 tags
                query = query.filter(cls.tags.ilike(f"%{tag}%"))

        # Ordenar por qualidade e retornar
        return (
            query.order_by(cls.quality_score.desc(), cls.usage_count.desc())
            .limit(limit)
            .all()
        )

    def increment_usage(self):
        """Incrementa contador de uso."""
        self.usage_count += 1
        db.session.commit()

    def __repr__(self):
        return f"<TemplateExample {self.name}>"


class AIGenerationFeedback(db.Model):
    """
    Armazena feedback dos usuários sobre templates gerados pela IA.
    Usado para melhorar a qualidade das gerações futuras.
    """

    __tablename__ = "ai_generation_feedback"

    id = db.Column(db.Integer, primary_key=True)

    # Referência ao modelo (se aplicável)
    petition_model_id = db.Column(
        db.Integer, db.ForeignKey("petition_models.id"), nullable=True
    )

    # O template gerado
    generated_template = db.Column(db.Text, nullable=False)

    # Feedback do usuário
    rating = db.Column(db.Integer, nullable=False)  # 1-5 estrelas
    feedback_type = db.Column(db.String(20))  # positive, negative, neutral
    feedback_text = db.Column(db.Text)  # Comentário opcional

    # O que o usuário fez depois
    action_taken = db.Column(db.String(30))  # used_as_is, edited, discarded
    edited_template = db.Column(db.Text)  # Se editou, qual foi o resultado

    # Contexto da geração
    prompt_used = db.Column(db.Text)  # O prompt que gerou este template
    sections_used = db.Column(db.JSON)  # IDs das seções usadas

    # Metadados
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    user = db.relationship("User", foreign_keys=[user_id])
    petition_model = db.relationship("PetitionModel", foreign_keys=[petition_model_id])

    @classmethod
    def get_average_rating(cls, petition_type_id=None):
        """Retorna a média de avaliações."""
        from sqlalchemy import func

        query = db.session.query(func.avg(cls.rating))
        if petition_type_id:
            query = query.join(PetitionModel).filter(
                PetitionModel.petition_type_id == petition_type_id
            )
        result = query.scalar()
        return round(result, 1) if result else 0

    def __repr__(self):
        return f"<AIGenerationFeedback {self.id} rating={self.rating}>"


class Referral(db.Model):
    """
    Programa de Indicação - Rastreia indicações entre usuários.

    Créditos só são concedidos quando o indicado faz o primeiro pagamento,
    como proteção anti-fraude contra criação de contas falsas.
    """

    __tablename__ = "referrals"

    id = db.Column(db.Integer, primary_key=True)

    # Quem indicou
    referrer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # Quem foi indicado
    referred_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=True
    )  # null até criar conta
    referred_email = db.Column(db.String(120), nullable=False)  # Email usado no link

    # Código de indicação usado
    referral_code = db.Column(db.String(20), nullable=False)

    # Status da indicação
    status = db.Column(
        db.String(20), default="pending"
    )  # pending, registered, converted, expired, invalid

    # Datas importantes
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    registered_at = db.Column(
        db.DateTime, nullable=True
    )  # Quando o indicado criou conta
    converted_at = db.Column(db.DateTime, nullable=True)  # Quando o indicado pagou

    # Recompensas
    referrer_reward_credits = db.Column(
        db.Integer, default=0
    )  # Créditos dados ao indicador
    referred_reward_credits = db.Column(
        db.Integer, default=0
    )  # Créditos dados ao indicado
    reward_granted = db.Column(db.Boolean, default=False)  # Se a recompensa já foi dada

    # Informações de conversão
    first_payment_id = db.Column(
        db.Integer, db.ForeignKey("payments.id"), nullable=True
    )
    first_payment_amount = db.Column(db.Numeric(10, 2), nullable=True)

    # Proteção anti-fraude
    referred_ip = db.Column(db.String(45), nullable=True)
    referred_user_agent = db.Column(db.String(500), nullable=True)

    # Relacionamentos
    referrer = db.relationship(
        "User", foreign_keys=[referrer_id], backref="referrals_made"
    )
    referred = db.relationship(
        "User", foreign_keys=[referred_id], backref="referral_received"
    )
    first_payment = db.relationship("Payment", foreign_keys=[first_payment_id])

    # Configurações do programa (valores padrão)
    REFERRER_REWARD_CREDITS = 50  # Créditos para quem indica
    REFERRED_BONUS_CREDITS = 20  # Créditos extras para quem é indicado
    MAX_REFERRALS_PER_MONTH = 20  # Limite mensal de indicações com recompensa

    @classmethod
    def generate_referral_code(cls, user):
        """Gera um código de indicação único para o usuário."""
        import re
        import secrets

        # Tenta usar parte do nome do usuário
        if user.full_name:
            name_part = re.sub(r"[^a-zA-Z]", "", user.full_name.split()[0].upper())[:4]
        else:
            name_part = user.username[:4].upper()

        # Adiciona números aleatórios
        random_part = secrets.token_hex(2).upper()

        code = f"{name_part}{random_part}"

        # Garante unicidade
        while cls.query.filter_by(referral_code=code).first():
            random_part = secrets.token_hex(2).upper()
            code = f"{name_part}{random_part}"

        return code

    @classmethod
    def get_user_referral_code(cls, user):
        """Obtém ou cria o código de indicação do usuário."""
        # Verifica se usuário já tem um código
        existing = cls.query.filter_by(referrer_id=user.id).first()
        if existing:
            return existing.referral_code

        # Se não tem, gera um novo
        return cls.generate_referral_code(user)

    @classmethod
    def get_referrer_by_code(cls, code):
        """Encontra o usuário que possui um código de indicação."""
        referral = cls.query.filter_by(referral_code=code.upper()).first()
        if referral:
            return referral.referrer

        # Busca por código armazenado no User (se implementado)
        user = User.query.filter(
            User.id
            == cls.query.filter_by(referral_code=code.upper())
            .with_entities(cls.referrer_id)
            .scalar()
        ).first()
        return user

    @classmethod
    def create_referral(
        cls, referrer_id, referred_email, referral_code, ip=None, user_agent=None
    ):
        """Cria um registro de indicação quando alguém usa um link de indicação."""
        # Verifica se já existe indicação para este email
        existing = cls.query.filter_by(referred_email=referred_email.lower()).first()
        if existing:
            return existing

        referral = cls(
            referrer_id=referrer_id,
            referred_email=referred_email.lower(),
            referral_code=referral_code.upper(),
            status="pending",
            referred_ip=ip,
            referred_user_agent=user_agent,
        )
        db.session.add(referral)
        db.session.commit()
        return referral

    @classmethod
    def mark_as_registered(cls, email, user_id):
        """Marca a indicação como registrada quando o usuário cria conta."""
        referral = cls.query.filter_by(
            referred_email=email.lower(), status="pending"
        ).first()

        if referral:
            referral.status = "registered"
            referral.referred_id = user_id
            referral.registered_at = datetime.now(timezone.utc)
            db.session.commit()
            return referral
        return None

    @classmethod
    def process_conversion(cls, user_id, payment_id, payment_amount):
        """
        Processa a conversão quando o indicado faz o primeiro pagamento.
        Concede créditos ao indicador e bônus ao indicado.
        """
        referral = cls.query.filter_by(
            referred_id=user_id, status="registered", reward_granted=False
        ).first()

        if not referral:
            return None

        # Verifica limite mensal do indicador
        month_start = datetime.now(timezone.utc).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        month_conversions = cls.query.filter(
            cls.referrer_id == referral.referrer_id,
            cls.converted_at >= month_start,
            cls.reward_granted.is_(True),
        ).count()

        if month_conversions >= cls.MAX_REFERRALS_PER_MONTH:
            referral.status = "converted"
            referral.converted_at = datetime.now(timezone.utc)
            referral.first_payment_id = payment_id
            referral.first_payment_amount = payment_amount
            # Não concede recompensa, mas marca como convertido
            db.session.commit()
            return referral

        # Concede créditos ao indicador
        referrer_credits = UserCredits.get_or_create(referral.referrer_id)
        referrer_credits.add_credits(
            cls.REFERRER_REWARD_CREDITS,
            source="referral_reward",
            description=f"Indicação convertida: {referral.referred_email}",
        )

        # Concede bônus ao indicado
        referred_credits = UserCredits.get_or_create(user_id)
        referred_credits.add_credits(
            cls.REFERRED_BONUS_CREDITS,
            source="referral_bonus",
            description="Bônus de boas-vindas por indicação",
        )

        # Atualiza registro
        referral.status = "converted"
        referral.converted_at = datetime.now(timezone.utc)
        referral.first_payment_id = payment_id
        referral.first_payment_amount = payment_amount
        referral.referrer_reward_credits = cls.REFERRER_REWARD_CREDITS
        referral.referred_reward_credits = cls.REFERRED_BONUS_CREDITS
        referral.reward_granted = True

        db.session.commit()
        return referral

    @classmethod
    def get_user_stats(cls, user_id):
        """Retorna estatísticas de indicação do usuário."""
        total = cls.query.filter_by(referrer_id=user_id).count()
        registered = cls.query.filter_by(
            referrer_id=user_id, status="registered"
        ).count()
        converted = cls.query.filter_by(referrer_id=user_id, status="converted").count()

        total_credits = (
            db.session.query(
                db.func.coalesce(db.func.sum(cls.referrer_reward_credits), 0)
            )
            .filter(cls.referrer_id == user_id, cls.reward_granted.is_(True))
            .scalar()
        )

        return {
            "total_referrals": total,
            "pending": total - registered - converted,
            "registered": registered,
            "converted": converted,
            "total_credits_earned": int(total_credits or 0),
            "conversion_rate": round((converted / total * 100) if total > 0 else 0, 1),
        }

    def __repr__(self):
        return f"<Referral {self.id} {self.referrer_id} -> {self.referred_email} ({self.status})>"


class ReferralCode(db.Model):
    """
    Armazena códigos de indicação únicos para cada usuário.
    Separado do Referral para permitir códigos permanentes.
    """

    __tablename__ = "referral_codes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False
    )
    code = db.Column(db.String(20), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default=True)

    # Estatísticas rápidas
    total_clicks = db.Column(db.Integer, default=0)
    total_registrations = db.Column(db.Integer, default=0)
    total_conversions = db.Column(db.Integer, default=0)

    user = db.relationship(
        "User", backref=db.backref("referral_code_obj", uselist=False)
    )

    @classmethod
    def get_or_create(cls, user):
        """Obtém ou cria o código de indicação do usuário."""
        existing = cls.query.filter_by(user_id=user.id).first()
        if existing:
            return existing

        # Gera código único
        import re
        import secrets

        if user.full_name:
            name_part = re.sub(r"[^a-zA-Z]", "", user.full_name.split()[0].upper())[:4]
        else:
            name_part = user.username[:4].upper()

        random_part = secrets.token_hex(2).upper()
        code = f"{name_part}{random_part}"

        while cls.query.filter_by(code=code).first():
            random_part = secrets.token_hex(2).upper()
            code = f"{name_part}{random_part}"

        new_code = cls(user_id=user.id, code=code)
        db.session.add(new_code)
        db.session.commit()
        return new_code

    def increment_clicks(self):
        """Incrementa contador de cliques."""
        self.total_clicks += 1
        db.session.commit()

    def increment_registrations(self):
        """Incrementa contador de registros."""
        self.total_registrations += 1
        db.session.commit()

    def increment_conversions(self):
        """Incrementa contador de conversões."""
        self.total_conversions += 1
        db.session.commit()

    def __repr__(self):
        return f"<ReferralCode {self.code} user={self.user_id}>"


class PromoCoupon(db.Model):
    """
    Cupom promocional para dar dias de acesso e/ou créditos de IA.
    Uso único global - cada cupom só pode ser usado uma vez.
    """

    __tablename__ = "promo_coupons"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)

    # Benefícios
    benefit_days = db.Column(db.Integer, default=0)  # Dias de acesso ao plano premium
    benefit_credits = db.Column(db.Integer, default=0)  # Créditos de IA

    # Descrição do cupom (para admin)
    description = db.Column(db.String(255))

    # Validade do cupom para resgate
    expires_at = db.Column(db.DateTime)  # Data limite para usar o cupom

    # Status
    is_used = db.Column(db.Boolean, default=False)
    used_at = db.Column(db.DateTime)
    used_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    # Quem criou
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relacionamentos
    used_by = db.relationship("User", foreign_keys=[used_by_id], backref="coupons_used")
    created_by = db.relationship(
        "User", foreign_keys=[created_by_id], backref="coupons_created"
    )

    @classmethod
    def generate_code(cls, prefix="PETITIO"):
        """Gera um código único para o cupom"""
        import secrets

        random_part = secrets.token_hex(4).upper()
        return f"{prefix}-{random_part}"

    @classmethod
    def create_coupon(
        cls,
        created_by_id,
        benefit_days=0,
        benefit_credits=0,
        description=None,
        expires_at=None,
        custom_code=None,
    ):
        """
        Cria um novo cupom promocional.

        Args:
            created_by_id: ID do usuário master que está criando
            benefit_days: Dias de acesso premium
            benefit_credits: Créditos de IA
            description: Descrição do cupom
            expires_at: Data de expiração para resgate
            custom_code: Código personalizado (opcional)

        Returns:
            PromoCoupon: O cupom criado
        """
        code = custom_code or cls.generate_code()

        # Verificar se código já existe
        if cls.query.filter_by(code=code).first():
            # Gerar novo código se já existir
            code = cls.generate_code()

        coupon = cls(
            code=code,
            benefit_days=benefit_days,
            benefit_credits=benefit_credits,
            description=description,
            expires_at=expires_at,
            created_by_id=created_by_id,
        )
        db.session.add(coupon)
        db.session.commit()
        return coupon

    def is_valid(self):
        """Verifica se o cupom é válido para uso"""
        if self.is_used:
            return False, "Este cupom já foi utilizado"

        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False, "Este cupom expirou"

        return True, "Cupom válido"

    def apply_to_user(self, user):
        """
        Aplica os benefícios do cupom ao usuário.

        Args:
            user: Objeto User que está usando o cupom

        Returns:
            tuple: (success, message, details)
        """
        # Verificar se cupom é válido
        valid, msg = self.is_valid()
        if not valid:
            return False, msg, {}

        details = {
            "days_added": 0,
            "credits_added": 0,
            "new_trial_end": None,
            "new_credit_balance": 0,
        }

        # Aplicar dias de acesso
        if self.benefit_days > 0:
            # Se usuário tem assinatura ativa, adiciona dias
            active_sub = user.subscriptions.filter_by(status="active").first()

            if active_sub and active_sub.current_period_end:
                # Adiciona dias à assinatura existente
                active_sub.current_period_end += timedelta(days=self.benefit_days)
                details["new_trial_end"] = active_sub.current_period_end
            else:
                # Cria/estende trial no User
                # Calcular data atual de fim do trial (se existir)
                current_trial_end = None
                if user.trial_active and user.trial_start_date and user.trial_days:
                    current_trial_end = user.trial_start_date + timedelta(
                        days=user.trial_days
                    )

                if current_trial_end and current_trial_end > datetime.now(timezone.utc):
                    # Extende trial existente
                    user.trial_days += self.benefit_days
                else:
                    # Novo trial
                    user.trial_start_date = datetime.now(timezone.utc)
                    user.trial_days = self.benefit_days

                user.trial_active = True
                details["new_trial_end"] = user.trial_start_date + timedelta(
                    days=user.trial_days
                )

            details["days_added"] = self.benefit_days

        # Aplicar créditos de IA
        if self.benefit_credits > 0:
            if not user.credits:
                user.credits = UserCredits(user_id=user.id, balance=0)
                db.session.add(user.credits)

            user.credits.add_credits(self.benefit_credits, source="bonus")
            details["credits_added"] = self.benefit_credits
            details["new_credit_balance"] = user.credits.balance

            # Registrar transação de créditos
            transaction = CreditTransaction(
                user_id=user.id,
                amount=self.benefit_credits,
                transaction_type="coupon_bonus",
                description=f"Cupom promocional: {self.code}",
                balance_after=user.credits.balance,
            )
            db.session.add(transaction)

        # Marcar cupom como usado
        self.is_used = True
        self.used_at = datetime.now(timezone.utc)
        self.used_by_id = user.id

        db.session.commit()

        return True, "Cupom aplicado com sucesso!", details

    def __repr__(self):
        status = "USADO" if self.is_used else "DISPONÍVEL"
        return f"<PromoCoupon {self.code} [{status}]>"


# =============================================================================
# CONFIGURAÇÃO DE CUSTOS DE IA
# =============================================================================


class AICreditConfig(db.Model):
    """Configuração de custos de créditos de IA - editável pelo admin"""

    __tablename__ = "ai_credit_configs"

    id = db.Column(db.Integer, primary_key=True)
    operation_key = db.Column(
        db.String(50), unique=True, nullable=False
    )  # Ex: 'section', 'improve', 'analyze_risk'
    name = db.Column(db.String(100), nullable=False)  # Nome amigável
    description = db.Column(db.Text)  # Descrição da operação
    credit_cost = db.Column(db.Integer, nullable=False, default=1)  # Custo em créditos
    is_premium = db.Column(db.Boolean, default=False)  # Se usa modelo premium (GPT-4o)
    is_active = db.Column(db.Boolean, default=True)  # Se a operação está disponível
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Configurações padrão
    DEFAULT_CONFIGS = [
        {
            "operation_key": "section",
            "name": "Gerar Seção",
            "description": "Gera uma seção individual da petição (fatos, direito, pedidos)",
            "credit_cost": 1,
            "is_premium": False,
        },
        {
            "operation_key": "improve",
            "name": "Melhorar Texto",
            "description": "Melhora e revisa um trecho de texto selecionado",
            "credit_cost": 1,
            "is_premium": False,
        },
        {
            "operation_key": "summarize",
            "name": "Resumir Texto",
            "description": "Resume um texto longo em pontos principais",
            "credit_cost": 1,
            "is_premium": False,
        },
        {
            "operation_key": "full_petition",
            "name": "Petição Completa",
            "description": "Gera uma petição completa com todas as seções",
            "credit_cost": 5,
            "is_premium": True,
        },
        {
            "operation_key": "analyze",
            "name": "Análise Jurídica",
            "description": "Analisa juridicamente um caso ou situação",
            "credit_cost": 3,
            "is_premium": True,
        },
        {
            "operation_key": "fundamentos",
            "name": "Fundamentação Jurídica",
            "description": "Gera fundamentação jurídica com citações de leis",
            "credit_cost": 3,
            "is_premium": True,
        },
        {
            "operation_key": "analyze_document",
            "name": "Análise de Documento",
            "description": "Analisa documento PDF/DOCX e extrai informações",
            "credit_cost": 4,
            "is_premium": True,
        },
        {
            "operation_key": "analyze_risk",
            "name": "Análise de Riscos e Chances",
            "description": "Analisa riscos, pontos fortes/fracos e chances de êxito",
            "credit_cost": 3,
            "is_premium": True,
        },
    ]

    @classmethod
    def get_cost(cls, operation_key: str) -> int:
        """Retorna o custo em créditos para uma operação"""
        config = cls.query.filter_by(
            operation_key=operation_key, is_active=True
        ).first()
        if config:
            return config.credit_cost
        # Fallback para defaults
        for default in cls.DEFAULT_CONFIGS:
            if default["operation_key"] == operation_key:
                return default["credit_cost"]
        return 1  # Default mínimo

    @classmethod
    def is_premium_operation(cls, operation_key: str) -> bool:
        """Verifica se a operação usa modelo premium"""
        config = cls.query.filter_by(
            operation_key=operation_key, is_active=True
        ).first()
        if config:
            return config.is_premium
        # Fallback para defaults
        for default in cls.DEFAULT_CONFIGS:
            if default["operation_key"] == operation_key:
                return default["is_premium"]
        return False

    @classmethod
    def is_operation_active(cls, operation_key: str) -> bool:
        """Verifica se a operação está ativa"""
        config = cls.query.filter_by(operation_key=operation_key).first()
        if config:
            return config.is_active
        return True  # Default: ativo

    @classmethod
    def get_all_configs(cls) -> dict:
        """Retorna todas as configurações como dicionário"""
        configs = cls.query.filter_by(is_active=True).order_by(cls.sort_order).all()
        result = {}
        for config in configs:
            result[config.operation_key] = {
                "name": config.name,
                "description": config.description,
                "credit_cost": config.credit_cost,
                "is_premium": config.is_premium,
            }
        return result

    @classmethod
    def seed_defaults(cls):
        """Popula a tabela com as configurações padrão se não existirem"""
        for default in cls.DEFAULT_CONFIGS:
            existing = cls.query.filter_by(
                operation_key=default["operation_key"]
            ).first()
            if not existing:
                config = cls(
                    operation_key=default["operation_key"],
                    name=default["name"],
                    description=default["description"],
                    credit_cost=default["credit_cost"],
                    is_premium=default["is_premium"],
                    sort_order=cls.DEFAULT_CONFIGS.index(default),
                )
                db.session.add(config)
        db.session.commit()

    def __repr__(self):
        return f"<AICreditConfig {self.operation_key}: {self.credit_cost} créditos>"

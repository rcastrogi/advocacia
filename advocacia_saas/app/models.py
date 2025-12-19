import json
from datetime import datetime, timedelta
from decimal import Decimal

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db, login_manager

# Cache para usuário demo em memória
_demo_user_cache = {}

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
    return User.query.get(user_id)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    user_type = db.Column(
        db.String(20), nullable=False, default="advogado"
    )  # 'master', 'advogado' or 'escritorio'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Profile information
    full_name = db.Column(db.String(200))
    oab_number = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    logo_filename = db.Column(db.String(200))
    billing_status = db.Column(
        db.String(20), default="active"
    )  # active, delinquent, trial, pending_payment
    quick_actions = db.Column(db.Text, default=json.dumps(DEFAULT_QUICK_ACTIONS))
    stripe_customer_id = db.Column(db.String(120), unique=True, index=True)

    # Password security fields
    password_changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    password_expires_at = db.Column(db.DateTime)
    password_history = db.Column(
        db.Text, default="[]"
    )  # JSON array of last 3 password hashes
    force_password_change = db.Column(db.Boolean, default=False)

    # Relationships
    clients = db.relationship("Client", backref="lawyer", lazy="dynamic")
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
    petition_templates = db.relationship(
        "PetitionTemplate",
        backref="owner",
        lazy="dynamic",
        cascade="all, delete-orphan",
        foreign_keys="PetitionTemplate.owner_id",
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
        self.password_changed_at = datetime.utcnow()
        self.password_expires_at = datetime.utcnow() + timedelta(days=90)  # 3 meses
        self.force_password_change = False

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_password_expired(self):
        """Verifica se a senha está expirada"""
        if not self.password_expires_at:
            return True  # Se não tem data de expiração, força mudança
        return datetime.utcnow() > self.password_expires_at

    def days_until_password_expires(self):
        """Retorna quantos dias faltam para a senha expirar"""
        if not self.password_expires_at:
            return 0
        delta = self.password_expires_at - datetime.utcnow()
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

    def get_active_plan(self):
        return self.plans.filter_by(is_current=True).first()

    def has_active_subscription(self):
        plan = self.get_active_plan()
        return plan is not None and plan.status == "active"

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


class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lawyer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
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
    slug = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(180), nullable=False)
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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

    def get_sections_ordered(self):
        """Retorna as seções deste tipo de petição ordenadas."""
        return self.type_sections.order_by(PetitionTypeSection.order).all()

    def __repr__(self):
        return f"<PetitionType {self.slug}>"


class PetitionTemplate(db.Model):
    __tablename__ = "petition_templates"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), default="civel")
    content = db.Column(db.Text, nullable=False)
    # JSON field to store default values for form fields (facts, fundamentos, pedidos, etc.)
    default_values = db.Column(db.Text, default="{}")
    is_global = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    petition_type_id = db.Column(
        db.Integer, db.ForeignKey("petition_types.id"), nullable=False
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    petition_type = db.relationship("PetitionType", backref="templates")

    def get_default_values(self) -> dict:
        """Returns the default values as a dictionary."""
        if self.default_values:
            try:
                return json.loads(self.default_values)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    def set_default_values(self, values: dict):
        """Sets the default values from a dictionary."""
        self.default_values = json.dumps(values, ensure_ascii=False)

    def is_accessible_by(self, user: "User") -> bool:
        if self.is_global:
            return True
        return self.owner_id == user.id

    def __repr__(self):
        scope = "global" if self.is_global else f"user={self.owner_id}"
        return f"<PetitionTemplate {self.slug} ({scope})>"


class BillingPlan(db.Model):
    __tablename__ = "billing_plans"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    plan_type = db.Column(db.String(20), nullable=False, default="per_usage")
    monthly_fee = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))
    usage_rate = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))
    description = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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

    def includes_petition(self, petition_type):
        return petition_type in self.petition_types

    @property
    def is_per_usage(self):
        """Check if this is a pay-per-use plan"""
        return self.plan_type == "per_usage"

    @property
    def plan_type_label(self):
        """Get friendly label for plan type"""
        labels = {
            "per_usage": "Pague por uso",
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
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
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
    generated_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    billing_cycle = db.Column(db.String(7), index=True)  # YYYY-MM
    billable = db.Column(db.Boolean, default=False)
    amount = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))
    extra_data = db.Column(db.JSON)

    plan = db.relationship("BillingPlan")

    def __repr__(self):
        return f"<PetitionUsage user={self.user_id} petition={self.petition_type_id}>"


class Invoice(db.Model):
    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    billing_cycle = db.Column(db.String(7), nullable=False)
    amount_due = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))
    amount_paid = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))
    status = db.Column(db.String(20), default="pending")
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime)

    payments = db.relationship(
        "Payment",
        backref="invoice",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Invoice {self.billing_cycle} user={self.user_id}>"


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    paid_at = db.Column(db.DateTime, default=datetime.utcnow)
    method = db.Column(db.String(30))
    reference = db.Column(db.String(120))

    # Stripe-specific fields
    stripe_customer_id = db.Column(db.String(120), index=True)
    stripe_payment_intent_id = db.Column(db.String(120), unique=True, index=True)
    stripe_checkout_session_id = db.Column(db.String(120), unique=True, index=True)
    stripe_subscription_id = db.Column(db.String(120), index=True)
    payment_status = db.Column(
        db.String(30), default="pending"
    )  # pending, completed, failed, refunded
    webhook_received_at = db.Column(db.DateTime)
    extra_metadata = db.Column(db.JSON)

    user = db.relationship("User", backref="payments")

    def __repr__(self):
        return f"<Payment invoice={self.invoice_id} amount={self.amount} status={self.payment_status}>"


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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
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

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def get_fields(self):
        """Retorna os campos da seção."""
        return self.fields_schema or []

    def set_fields(self, fields: list):
        """Define os campos da seção."""
        self.fields_schema = fields

    def __repr__(self):
        return f"<PetitionSection {self.slug}>"


class PetitionTypeSection(db.Model):
    """
    Relaciona tipos de petição com suas seções (muitos para muitos com metadados).
    Permite definir quais seções aparecem em cada tipo de petição e em qual ordem.
    """

    __tablename__ = "petition_type_sections"

    id = db.Column(db.Integer, primary_key=True)
    petition_type_id = db.Column(
        db.Integer, db.ForeignKey("petition_types.id"), nullable=False
    )
    section_id = db.Column(
        db.Integer, db.ForeignKey("petition_sections.id"), nullable=False
    )
    order = db.Column(db.Integer, default=0)  # Ordem desta seção neste tipo de petição
    is_required = db.Column(db.Boolean, default=False)  # Seção obrigatória?
    is_expanded = db.Column(db.Boolean, default=True)  # Começa expandida?

    # Sobrescrever campos específicos para este tipo (opcional)
    # Ex: {"author_name": {"label": "Nome do Requerente"}} - muda apenas o label
    field_overrides = db.Column(db.JSON, default=dict)

    # Relacionamentos
    petition_type = db.relationship(
        "PetitionType",
        backref=db.backref(
            "type_sections", lazy="dynamic", order_by="PetitionTypeSection.order"
        ),
    )
    section = db.relationship(
        "PetitionSection", backref=db.backref("type_sections", lazy="dynamic")
    )

    def get_fields(self):
        """Retorna os campos da seção com overrides aplicados para este tipo de petição."""
        import copy

        fields = copy.deepcopy(self.section.get_fields()) if self.section else []
        overrides = self.field_overrides or {}

        for field in fields:
            field_name = field.get("name")
            if field_name in overrides:
                field.update(overrides[field_name])

        return fields

    def __repr__(self):
        return f"<PetitionTypeSection type={self.petition_type_id} section={self.section_id}>"


class SavedPetition(db.Model):
    """
    Petições salvas pelo usuário (rascunhos e finalizadas).
    Permite consulta, edição e acompanhamento das petições criadas.
    """

    __tablename__ = "saved_petitions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    petition_type_id = db.Column(
        db.Integer, db.ForeignKey("petition_types.id"), nullable=False
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

    # Metadados
    notes = db.Column(db.Text)  # Anotações internas
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
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
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
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
    stripe_price_id = db.Column(db.String(100))  # ID do preço no Stripe
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
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
        self.updated_at = datetime.utcnow()
        return self.balance

    def use_credits(self, amount):
        """Usa créditos (retorna True se teve saldo suficiente)"""
        if self.balance >= amount:
            self.balance -= amount
            self.total_used += amount
            self.updated_at = datetime.utcnow()
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
    payment_intent_id = db.Column(db.String(100))  # ID do pagamento Stripe

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
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
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # 'petition_ready', 'credit_low', 'payment_due', 'password_expiring', 'ai_limit', 'system'
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(500))  # URL para ação relacionada
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime)
    
    # Relacionamento
    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic', cascade='all, delete-orphan'))
    
    def mark_as_read(self):
        """Marca a notificação como lida"""
        self.read = True
        self.read_at = datetime.utcnow()
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
            link=link
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
        return Notification.query\
            .filter_by(user_id=user_id)\
            .order_by(Notification.created_at.desc())\
            .limit(limit)\
            .all()
    
    def __repr__(self):
        return f"<Notification {self.type} - User {self.user_id}>"

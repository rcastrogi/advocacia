import json
from datetime import datetime, timedelta

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


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

    # Password security fields
    password_changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    password_expires_at = db.Column(db.DateTime)
    password_history = db.Column(
        db.Text, default="[]"
    )  # JSON array of last 3 password hashes
    force_password_change = db.Column(db.Boolean, default=False)

    # Relationships
    clients = db.relationship("Client", backref="lawyer", lazy="dynamic")

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

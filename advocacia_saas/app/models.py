from datetime import datetime

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

    # Relationships
    clients = db.relationship("Client", backref="lawyer", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

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
    
    __tablename__ = 'estados'
    
    id = db.Column(db.Integer, primary_key=True)
    sigla = db.Column(db.String(2), unique=True, nullable=False, index=True)
    nome = db.Column(db.String(50), nullable=False)
    
    # Relationship
    cidades = db.relationship('Cidade', backref='estado', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Estado {self.sigla} - {self.nome}>'
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'sigla': self.sigla,
            'nome': self.nome
        }


class Cidade(db.Model):
    """Brazilian cities model."""
    
    __tablename__ = 'cidades'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, index=True)
    estado_id = db.Column(db.Integer, db.ForeignKey('estados.id'), nullable=False, index=True)
    
    def __repr__(self):
        return f'<Cidade {self.nome} - {self.estado.sigla}>'
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'nome': self.nome,
            'estado_id': self.estado_id
        }

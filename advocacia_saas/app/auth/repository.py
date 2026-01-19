"""
Auth Repository - Camada de Acesso a Dados para Autenticação.

Este módulo encapsula todas as operações de banco de dados relacionadas
à autenticação, seguindo o padrão Repository.
"""

import json
from typing import Optional

from flask import request

from app import db
from app.models import DataConsent, DataProcessingLog, Notification, User


class UserRepository:
    """Repositório para operações de banco de dados com User."""

    @staticmethod
    def find_by_email(email: str) -> Optional[User]:
        """Busca usuário pelo email."""
        return User.query.filter_by(email=email).first()

    @staticmethod
    def find_by_id(user_id: int) -> Optional[User]:
        """Busca usuário pelo ID."""
        return User.query.get(user_id)

    @staticmethod
    def find_by_username(username: str) -> Optional[User]:
        """Busca usuário pelo username."""
        return User.query.filter_by(username=username).first()

    @staticmethod
    def email_exists(email: str, exclude_user_id: Optional[int] = None) -> bool:
        """Verifica se email já existe no banco."""
        query = User.query.filter_by(email=email)
        if exclude_user_id:
            query = query.filter(User.id != exclude_user_id)
        return query.first() is not None

    @staticmethod
    def username_exists(username: str, exclude_user_id: Optional[int] = None) -> bool:
        """Verifica se username já existe no banco."""
        query = User.query.filter_by(username=username)
        if exclude_user_id:
            query = query.filter(User.id != exclude_user_id)
        return query.first() is not None

    @staticmethod
    def master_exists() -> bool:
        """Verifica se existe um usuário master no sistema."""
        return User.query.filter_by(user_type="master").first() is not None

    @staticmethod
    def create_user(
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
        billing_status: str = "active",
        specialties: Optional[list] = None,
    ) -> User:
        """Cria e persiste um novo usuário."""
        user = User(
            username=username,
            email=email,
            full_name=full_name,
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
        )
        user.set_password(password)

        if specialties:
            user.set_specialties(specialties)

        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def update_user(user: User, **kwargs) -> User:
        """Atualiza campos do usuário."""
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        db.session.commit()
        return user

    @staticmethod
    def save(user: User) -> User:
        """Salva alterações no usuário."""
        db.session.commit()
        return user


class ConsentRepository:
    """Repositório para operações de consentimento LGPD."""

    @staticmethod
    def create_consent(
        user_id: int,
        consent_type: str,
        consent_purpose: str,
        consent_version: str = "1.0",
        consent_method: str = "registration_form",
    ) -> DataConsent:
        """Cria um registro de consentimento."""
        consent = DataConsent(
            user_id=user_id,
            consent_type=consent_type,
            consent_purpose=consent_purpose,
            consent_version=consent_version,
            ip_address=request.remote_addr if request else None,
            user_agent=request.headers.get("User-Agent") if request else None,
            consent_method=consent_method,
        )
        db.session.add(consent)
        return consent

    @staticmethod
    def log_processing(
        user_id: int,
        action: str,
        data_category: str,
        purpose: str,
        legal_basis: str,
        endpoint: Optional[str] = None,
        additional_data: Optional[dict] = None,
    ) -> DataProcessingLog:
        """Registra processamento de dados para LGPD."""
        log = DataProcessingLog(
            user_id=user_id,
            action=action,
            data_category=data_category,
            purpose=purpose,
            legal_basis=legal_basis,
            endpoint=endpoint or (request.path if request else None),
            additional_data=json.dumps(additional_data) if additional_data else None,
        )
        db.session.add(log)
        return log

    @staticmethod
    def commit():
        """Commita as alterações no banco."""
        db.session.commit()


class NotificationRepository:
    """Repositório para notificações do sistema."""

    @staticmethod
    def create_notification(
        user_id: int,
        notification_type: str,
        title: str,
        message: str,
    ) -> Notification:
        """Cria uma notificação para o usuário."""
        return Notification.create_notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
        )

"""
Testes para modelos de dados
"""

from datetime import datetime, timedelta

import pytest
from app.models import Client, Deadline, Document, User


class TestUserModel:
    """Testes para o modelo User"""

    def test_user_creation(self, db_session):
        """Testa criação de usuário"""
        user = User(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            oab_number="123456",
        )
        user.set_password("password123")

        db_session.add(user)
        db_session.commit()

        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.oab_number == "123456"
        assert user.check_password("password123")
        assert not user.check_password("wrongpassword")

    def test_user_repr(self, db_session):
        """Testa representação string do usuário"""
        user = User(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            oab_number="123456",
        )

        expected_repr = "<User testuser>"
        assert repr(user) == expected_repr


class TestClientModel:
    """Testes para o modelo Client"""

    def test_client_creation(self, db_session):
        """Testa criação de cliente"""
        user = User(
            username="lawyer",
            email="lawyer@example.com",
            full_name="Lawyer",
            oab_number="123",
        )
        user.set_password("password123")
        db_session.add(user)
        db_session.commit()  # Commit user first to get ID

        client = Client(
            full_name="João Cliente",
            email="joao@cliente.com",
            mobile_phone="11999999999",
            cpf_cnpj="12345678901",
            lawyer_id=user.id,
        )

        db_session.add(client)
        db_session.commit()

        assert client.id is not None
        assert client.full_name == "João Cliente"
        assert client.email == "joao@cliente.com"
        assert client.mobile_phone == "11999999999"
        assert client.cpf_cnpj == "12345678901"

    def test_client_user_relationship(self, db_session):
        """Testa relacionamento cliente-usuário"""
        user = User(
            username="advogado",
            email="advogado@example.com",
            full_name="Advogado Silva",
            oab_number="123456",
        )
        user.set_password("password123")
        db_session.add(user)
        db_session.commit()  # Commit user first

        client = Client(
            full_name="Cliente Teste",
            email="cliente@example.com",
            mobile_phone="11999999999",
            cpf_cnpj="12345678901",
            lawyer_id=user.id,
        )
        db_session.add(client)
        db_session.commit()

        assert client.lawyer == user
        assert client in user.clients


class TestDocumentModel:
    """Testes para o modelo Document"""

    def test_document_creation(self, db_session):
        """Testa criação de documento"""
        user = User(
            username="user",
            email="user@example.com",
            full_name="User",
            oab_number="123",
        )
        user.set_password("password123")
        db_session.add(user)
        db_session.commit()  # Commit user first

        client = Client(
            full_name="Client",
            email="client@example.com",
            mobile_phone="11999999999",
            cpf_cnpj="12345678901",
            lawyer_id=user.id,
        )
        db_session.add(client)
        db_session.commit()  # Commit client first

        document = Document(
            title="Petição Inicial",
            description="Conteúdo da petição...",
            document_type="petition",
            filename="peticao.pdf",
            file_path="/uploads/peticao.pdf",
            user_id=user.id,
            client_id=client.id,
        )

        db_session.add(document)
        db_session.commit()

        assert document.id is not None
        assert document.title == "Petição Inicial"
        assert document.document_type == "petition"
        assert document.filename == "peticao.pdf"
        assert document.created_at is not None


class TestDeadlineModel:
    """Testes para o modelo Deadline"""

    def test_deadline_creation(self, db_session):
        """Testa criação de prazo"""
        user = User(
            username="user_deadline",
            email="user_deadline@example.com",
            full_name="User Deadline",
            oab_number="123",
        )
        user.set_password("password123")
        db_session.add(user)
        db_session.commit()  # Commit user first

        client = Client(
            full_name="Client Deadline",
            email="client_deadline@example.com",
            mobile_phone="11999999999",
            cpf_cnpj="12345678901",
            lawyer_id=user.id,
        )
        db_session.add(client)
        db_session.commit()  # Commit client first

        future_date = datetime.utcnow() + timedelta(days=30)
        deadline = Deadline(
            title="Prazo Importante",
            description="Descrição do prazo",
            deadline_date=future_date,
            user_id=user.id,
            client_id=client.id,
        )

        db_session.add(deadline)
        db_session.commit()

        assert deadline.id is not None
        assert deadline.title == "Prazo Importante"
        assert deadline.deadline_date == future_date
        assert not deadline.is_overdue()

    def test_overdue_deadline(self, db_session):
        """Testa prazo vencido"""
        user = User(
            username="user_overdue",
            email="user_overdue@example.com",
            full_name="User Overdue",
            oab_number="123",
        )
        user.set_password("password123")
        db_session.add(user)
        db_session.commit()  # Commit user first

        past_date = datetime.utcnow() - timedelta(days=1)
        deadline = Deadline(
            title="Prazo Vencido",
            description="Este prazo já venceu",
            deadline_date=past_date,
            user_id=user.id,
        )

        db_session.add(deadline)
        db_session.commit()

        assert deadline.is_overdue()

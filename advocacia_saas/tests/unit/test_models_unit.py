"""
Testes unitários para models do Petitio.
"""

from datetime import datetime, timedelta, timezone

import pytest
from app import db
from app.models import Notification, User, UserCredits


class TestUserModel:
    """Testes para o model User"""

    def test_create_user(self, db_session):
        """Testa criação de usuário"""
        user = User(
            username="newuser",
            email="newuser@example.com",
            full_name="New User",
            user_type="advogado",
        )
        user.set_password("StrongPass123!", skip_history_check=True)

        db_session.add(user)
        db_session.commit()

        assert user.id is not None
        assert user.username == "newuser"
        assert user.check_password("StrongPass123!")

    def test_password_hashing(self, sample_user):
        """Testa hash de senha"""
        assert sample_user.password_hash != "StrongPass123!"
        assert sample_user.check_password("StrongPass123!")
        assert not sample_user.check_password("wrongpassword")

    def test_password_history(self, sample_user, db_session):
        """Testa histórico de senhas"""
        # Trocar senha
        sample_user.set_password("NewPass456!@")
        db_session.commit()

        # Tentar usar senha antiga deve falhar
        with pytest.raises(ValueError, match="senha já foi utilizada"):
            sample_user.set_password("StrongPass123!")

    def test_password_expiration(self, sample_user, db_session):
        """Testa expiração de senha"""
        # Senha recente não deve estar expirada
        assert not sample_user.is_password_expired()

        # Forçar expiração
        sample_user.password_expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        db_session.commit()

        assert sample_user.is_password_expired()

    def test_force_password_change(self, sample_user):
        """Testa flag de mudança forçada de senha"""
        sample_user.force_password_change = True
        assert sample_user.force_password_change == True

        # Mudar senha deve resetar flag
        sample_user.set_password("NewPass789!@#")
        assert sample_user.force_password_change == False


class TestNotificationModel:
    """Testes para o model Notification"""

    def test_create_notification(self, db_session, sample_user):
        """Testa criação de notificação"""
        notification = Notification.create_notification(
            user_id=sample_user.id,
            notification_type="credit_low",
            title="Créditos baixos",
            message="Seus créditos estão acabando",
            link="/billing/credits",
        )

        assert notification.id is not None
        assert notification.user_id == sample_user.id
        assert notification.read == False

    def test_mark_as_read(self, db_session, sample_user):
        """Testa marcar notificação como lida"""
        notification = Notification.create_notification(
            user_id=sample_user.id,
            notification_type="system",
            title="Teste",
            message="Mensagem de teste",
        )

        assert notification.read == False
        assert notification.read_at is None

        notification.mark_as_read()

        assert notification.read == True
        assert notification.read_at is not None

    def test_unread_count(self, db_session, sample_user):
        """Testa contagem de notificações não lidas"""
        # Criar 3 notificações
        for i in range(3):
            Notification.create_notification(
                user_id=sample_user.id,
                notification_type="system",
                title=f"Notificação {i}",
                message=f"Mensagem {i}",
            )

        # Todas não lidas
        assert Notification.get_unread_count(sample_user.id) == 3

        # Marcar uma como lida
        notification = Notification.query.filter_by(user_id=sample_user.id).first()
        notification.mark_as_read()

        assert Notification.get_unread_count(sample_user.id) == 2

    def test_get_recent(self, db_session, sample_user):
        """Testa busca de notificações recentes"""
        # Criar 15 notificações
        for i in range(15):
            Notification.create_notification(
                user_id=sample_user.id,
                notification_type="system",
                title=f"Notificação {i}",
                message=f"Mensagem {i}",
            )

        # Buscar 10 mais recentes
        recent = Notification.get_recent(sample_user.id, limit=10)

        assert len(recent) == 10
        # Deve estar ordenado por data decrescente
        assert recent[0].title == "Notificação 14"


class TestUserCreditsModel:
    """Testes para o model UserCredits"""

    def test_create_credits(self, db_session, sample_user):
        """Testa criação de registro de créditos"""
        credits = UserCredits(
            user_id=sample_user.id, balance=100, total_purchased=100, total_used=0
        )

        db_session.add(credits)
        db_session.commit()

        assert credits.id is not None
        assert credits.balance == 100

    def test_deduct_credits(self, db_session, sample_user):
        """Testa dedução de créditos"""
        credits = UserCredits(
            user_id=sample_user.id, balance=50, total_purchased=50, total_used=0
        )

        db_session.add(credits)
        db_session.commit()

        # Deduzir créditos
        credits.balance -= 10
        credits.total_used += 10
        db_session.commit()

        assert credits.balance == 40
        assert credits.total_used == 10


def test_password_validation():
    """Testa validação de senha forte"""
    from app.utils.validators import validate_strong_password

    # Senha válida
    is_valid, msg = validate_strong_password("StrongPass123!")
    assert is_valid == True

    # Senha muito curta
    is_valid, msg = validate_strong_password("Short1!")
    assert is_valid == False
    assert "mínimo 8 caracteres" in msg

    # Sem maiúscula
    is_valid, msg = validate_strong_password("weakpass123!")
    assert is_valid == False
    assert "maiúscula" in msg

    # Sem número
    is_valid, msg = validate_strong_password("WeakPass!")
    assert is_valid == False
    assert "número" in msg

    # Sem caractere especial
    is_valid, msg = validate_strong_password("WeakPass123")
    assert is_valid == False
    assert "especial" in msg

    # Sequência comum
    is_valid, msg = validate_strong_password("Password123!")
    assert is_valid == False
    assert "sequências comuns" in msg

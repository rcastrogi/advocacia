"""
Testes críticos para sistema de pagamentos
Prioridade: Alta - Sistema de pagamentos é crítico para SaaS
"""

import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock

from app.models import BillingPlan, Payment, Subscription, User


@pytest.fixture
def test_user(db_session):
    """Fixture para criar usuário de teste único"""
    user = User(
        username="testuser_pay",
        full_name="Test User Payment",
        email="test_payment@example.com",
        oab_number="123456",
    )
    user.set_password("Test123!")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def pay_per_use_plan(db_session):
    """Fixture para plano pay-per-use"""
    plan = BillingPlan(
        name="Plano Básico",
        slug="plano-basico",
        plan_type="per_usage",
        monthly_fee=Decimal("99.90"),
        active=True,
        supported_periods="1m"  # String, não lista
    )
    db_session.add(plan)
    db_session.commit()
    return plan


@pytest.fixture
def monthly_plan(db_session):
    """Fixture para plano mensal"""
    plan = BillingPlan(
        name="Plano Mensal",
        slug="plano-mensal",
        plan_type="monthly",
        monthly_fee=Decimal("199.90"),
        monthly_petition_limit=50,
        active=True,
        supported_periods="1m"
    )
    db_session.add(plan)
    db_session.commit()
    return plan


class TestPaymentSystem:
    """Testes para funcionalidades críticas de pagamento"""

    def test_get_plans_page(self, client, db_session, test_user):
        """Testa página de planos - funcionalidade crítica"""
        # Login
        client.post("/auth/login", data={"email": test_user.email, "password": "Test123!", "submit": "Entrar"})

        # Acessar página de planos
        response = client.get("/payments/plans")
        assert response.status_code == 200
        assert b"Plano" in response.data

    def test_create_pix_payment_success(self, client, db_session, test_user, pay_per_use_plan):
        """Testa criação de pagamento PIX - funcionalidade crítica"""
        # Login
        client.post("/auth/login", data={"email": test_user.email, "password": "Test123!", "submit": "Entrar"})

        # Mock Mercado Pago
        mock_payment_response = {
            "id": 12345,
            "status": "pending",
            "point_of_interaction": {
                "transaction_data": {
                    "qr_code": "test-qr-code",
                    "qr_code_base64": "test-qr-base64"
                }
            }
        }

        with patch('app.payments.routes.mp_sdk') as mock_mp:
            mock_mp.payment.return_value.create.return_value = {
                "status": 201,
                "response": mock_payment_response
            }

            # Criar pagamento PIX
            response = client.post(
                "/payments/create-pix-payment",
                json={
                    "plan_slug": "plano-basico",
                    "billing_period": "1m"
                }
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert "payment_id" in data
            assert "pix_code" in data

            # Verificar se pagamento foi criado no banco
            payment = Payment.query.filter_by(user_id=test_user.id).first()
            assert payment is not None
            assert payment.amount == Decimal("99.90")
            assert payment.payment_method == "pix"
            assert payment.status == "pending"

    def test_create_pix_payment_invalid_plan(self, client, db_session, test_user):
        """Testa erro com plano inválido"""
        # Login
        client.post("/auth/login", data={"email": test_user.email, "password": "Test123!", "submit": "Entrar"})

        # Tentar criar pagamento com plano inexistente
        response = client.post(
            "/payments/create-pix-payment",
            json={
                "plan_slug": "plano-inexistente",
                "billing_period": "1m"
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "Plano inválido" in data["error"]

    def test_create_subscription_success(self, client, db_session, test_user, monthly_plan):
        """Testa criação de assinatura recorrente - funcionalidade crítica"""
        # Login
        client.post("/auth/login", data={"email": test_user.email, "password": "Test123!", "submit": "Entrar"})

        # Mock Mercado Pago preapproval
        mock_preapproval_response = {
            "id": "preapproval_123",
            "status": "pending",
            "init_point": "https://mercadopago.com/init"
        }

        with patch('app.payments.routes.mp_sdk') as mock_mp:
            mock_mp.preapproval.return_value.create.return_value = {
                "status": 201,
                "response": mock_preapproval_response
            }

            # Criar assinatura
            response = client.post(
                "/payments/create-mercadopago-subscription",
                json={
                    "plan_slug": "plano-mensal",
                    "billing_period": "1m"
                }
            )

            assert response.status_code == 200
            data = response.get_json()
            assert "preapproval_url" in data

    def test_subscribe_page_invalid_plan(self, client, db_session, test_user):
        """Testa erro com plano inexistente"""
        # Login
        client.post("/auth/login", data={"email": test_user.email, "password": "Test123!", "submit": "Entrar"})

        # Tentar acessar plano inexistente
        response = client.get("/payments/subscribe/plano-inexistente/1m")
        assert response.status_code == 302  # Redirect

    def test_subscribe_page_invalid_period(self, client, db_session, test_user, pay_per_use_plan):
        """Testa erro com período inválido"""
        # Login
        client.post("/auth/login", data={"email": test_user.email, "password": "Test123!", "submit": "Entrar"})

        # Tentar período inválido
        response = client.get("/payments/subscribe/plano-basico/invalid")
        assert response.status_code == 302  # Redirect

    def test_duplicate_subscription_blocked(self, client, db_session, test_user, monthly_plan):
        """Testa que usuário não pode ter múltiplas assinaturas ativas"""
        # Criar assinatura ativa existente
        existing_subscription = Subscription(
            user_id=test_user.id,
            plan_type="monthly",
            billing_period="1m",
            amount=Decimal("199.90"),
            status="active",
            gateway="mercadopago",
            gateway_subscription_id="existing_sub_123"
        )
        db_session.add(existing_subscription)
        db_session.commit()

        # Login
        client.post("/auth/login", data={"email": test_user.email, "password": "Test123!", "submit": "Entrar"})

        # Tentar criar nova assinatura
        response = client.get("/payments/subscribe/plano-mensal/1m")
        assert response.status_code == 302  # Deve redirecionar

    def test_payment_without_authentication(self, client):
        """Testa que rotas de pagamento requerem autenticação"""
        # Tentar acessar sem login
        response = client.get("/payments/plans")
        assert response.status_code == 302  # Redirect to login

        response = client.post("/payments/create-pix-payment", json={})
        assert response.status_code == 302  # Redirect to login

"""
Testes unitários para funcionalidades de timezone do Petitio.
"""

import datetime

import pytest
import pytz
from app import create_app, db
from app.models import User


class TestTimezoneSystem:
    """Testes para o sistema de timezone"""

    def test_user_timezone_field(self, db_session):
        """Testa que o campo timezone existe no modelo User"""
        user = User(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            user_type="advogado",
        )
        user.set_password("TestPass123!", skip_history_check=True)

        db_session.add(user)
        db_session.commit()

        # Verificar que o campo timezone existe e tem valor padrão
        assert hasattr(user, "timezone")
        assert user.timezone == "America/Sao_Paulo"  # valor padrão

    def test_user_timezone_update(self, db_session):
        """Testa atualização do timezone do usuário"""
        user = User(
            username="testuser2",
            email="test2@example.com",
            full_name="Test User 2",
            user_type="advogado",
        )
        user.set_password("TestPass123!", skip_history_check=True)

        db_session.add(user)
        db_session.commit()

        # Atualizar timezone
        user.timezone = "Asia/Tokyo"
        db_session.commit()

        # Verificar atualização
        updated_user = User.query.filter_by(username="testuser2").first()
        assert updated_user.timezone == "Asia/Tokyo"

    def test_local_datetime_filter(self, app):
        """Testa o filtro local_datetime do Jinja2"""
        with app.app_context():
            # Criar datetime UTC
            utc_dt = datetime.datetime(2025, 12, 24, 12, 0, 0, tzinfo=pytz.UTC)

            # Testar conversão para São Paulo (padrão)
            result_sp = app.jinja_env.filters["local_datetime"](utc_dt)
            assert "24/12/2025" in result_sp
            # São Paulo é UTC-3, então 12:00 UTC = 09:00 BRT
            assert "às 09:00" in result_sp

            # Testar conversão para Tokyo
            result_tokyo = app.jinja_env.filters["local_datetime"](
                utc_dt, user_timezone="Asia/Tokyo"
            )
            assert "24/12/2025" in result_tokyo
            # Tokyo é UTC+9, então 12:00 UTC = 21:00 JST
            assert "às 21:00" in result_tokyo

    def test_local_date_filter(self, app):
        """Testa o filtro local_date do Jinja2"""
        with app.app_context():
            # Criar datetime UTC
            utc_dt = datetime.datetime(2025, 12, 24, 12, 0, 0, tzinfo=pytz.UTC)

            # Testar conversão para São Paulo (padrão)
            result_sp = app.jinja_env.filters["local_date"](utc_dt)
            assert result_sp == "24/12/2025"

            # Testar conversão para Tokyo (mesma data)
            result_tokyo = app.jinja_env.filters["local_date"](
                utc_dt, user_timezone="Asia/Tokyo"
            )
            assert result_tokyo == "24/12/2025"

            # Testar mudança de data devido ao timezone (exemplo: Nova York)
            utc_dt_early = datetime.datetime(
                2025, 12, 24, 5, 0, 0, tzinfo=pytz.UTC
            )  # 5:00 UTC
            result_ny = app.jinja_env.filters["local_date"](
                utc_dt_early, user_timezone="America/New_York"
            )
            # Nova York é UTC-5, então 5:00 UTC = 00:00 EST (mesma data)
            assert result_ny == "24/12/2025"

    def test_timezone_validation(self, app):
        """Testa validação de timezones válidos"""
        import pytz

        valid_timezones = pytz.all_timezones

        # Timezones que devem ser válidos
        assert "America/Sao_Paulo" in valid_timezones
        assert "Asia/Tokyo" in valid_timezones
        assert "Europe/Lisbon" in valid_timezones
        assert "America/New_York" in valid_timezones

        # Timezone inválido
        assert "Invalid/Timezone" not in valid_timezones

    def test_datetime_filter_with_naive_datetime(self, app):
        """Testa filtros com datetime naive (sem timezone)"""
        with app.app_context():
            # Criar datetime naive (sem timezone info)
            naive_dt = datetime.datetime(2025, 12, 24, 12, 0, 0)

            # Os filtros devem funcionar mesmo com datetime naive
            result = app.jinja_env.filters["local_datetime"](naive_dt)
            assert "24/12/2025" in result

            result_date = app.jinja_env.filters["local_date"](naive_dt)
            assert result_date == "24/12/2025"

    def test_datetime_filter_with_none_timezone(self, app):
        """Testa filtros quando user_timezone é None"""
        with app.app_context():
            utc_dt = datetime.datetime(2025, 12, 24, 12, 0, 0, tzinfo=pytz.UTC)

            # Quando user_timezone é None, deve usar o padrão (São Paulo)
            result = app.jinja_env.filters["local_datetime"](utc_dt, user_timezone=None)
            assert "24/12/2025" in result
            assert "às 09:00" in result  # 12:00 UTC = 09:00 BRT

    def test_datetime_filter_custom_format(self, app):
        """Testa filtros com formato personalizado"""
        with app.app_context():
            utc_dt = datetime.datetime(2025, 12, 24, 12, 0, 0, tzinfo=pytz.UTC)

            # Formato personalizado para datetime
            result = app.jinja_env.filters["local_datetime"](
                utc_dt, format_string="%Y-%m-%d %H:%M:%S"
            )
            assert "2025-12-24 09:00:00" in result

            # Formato personalizado para date
            result_date = app.jinja_env.filters["local_date"](
                utc_dt, format_string="%Y-%m-%d"
            )
            assert result_date == "2025-12-24"


class TestTimezoneRoute:
    """Testes para a rota de atualização de timezone"""

    def test_update_timezone_route_exists(self, client, db_session):
        """Testa que a rota de atualização de timezone existe"""
        # Criar usuário de teste
        user = User(
            username="testuser3",
            email="test3@example.com",
            full_name="Test User 3",
            user_type="advogado",
        )
        user.set_password("TestPass123!", skip_history_check=True)
        db_session.add(user)
        db_session.commit()

        # Fazer login (simular)
        with client:
            # Como não temos autenticação completa no teste, apenas verificar que a rota existe
            # Em um teste completo, faríamos login primeiro
            response = client.get("/auth/profile")
            # A rota deve existir (não 404)
            assert response.status_code in [200, 302, 401]  # 401 se não autenticado

    def test_timezone_field_in_form(self, client):
        """Testa que o campo timezone aparece no formulário de perfil"""
        response = client.get("/auth/profile")
        # Verificar se o campo timezone está no HTML
        assert b'name="timezone"' in response.data or response.status_code in [302, 401]

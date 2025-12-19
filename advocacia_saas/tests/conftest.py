"""
Configuração de testes para o Petitio.
"""

import os
import pytest
from app import create_app, db
from app.models import User, Client
from config import Config


class TestConfig(Config):
    """Configuração para ambiente de testes"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SERVER_NAME = 'localhost.localdomain'


@pytest.fixture(scope='session')
def app():
    """Cria instância da aplicação para testes"""
    app = create_app(TestConfig)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Cliente de teste para fazer requisições"""
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """CLI runner para testar comandos"""
    return app.test_cli_runner()


@pytest.fixture(scope='function')
def db_session(app):
    """Sessão de banco de dados isolada por teste"""
    with app.app_context():
        # Criar tabelas
        db.create_all()
        
        yield db.session
        
        # Rollback e limpar
        db.session.rollback()
        db.session.remove()


@pytest.fixture
def sample_user(db_session):
    """Cria usuário de exemplo para testes"""
    user = User(
        username='testuser',
        email='test@example.com',
        full_name='Test User',
        user_type='advogado',
        is_active=True
    )
    user.set_password('StrongPass123!', skip_history_check=True)
    
    db_session.add(user)
    db_session.commit()
    
    return user


@pytest.fixture
def admin_user(db_session):
    """Cria usuário admin para testes"""
    admin = User(
        username='admin',
        email='admin@petitio.com',
        full_name='Administrator',
        user_type='master',
        is_active=True
    )
    admin.set_password('AdminPass123!', skip_history_check=True)
    
    db_session.add(admin)
    db_session.commit()
    
    return admin


@pytest.fixture
def authenticated_client(client, sample_user):
    """Cliente autenticado como usuário normal"""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(sample_user.id)
        sess['_fresh'] = True
    
    return client


@pytest.fixture
def admin_client(client, admin_user):
    """Cliente autenticado como admin"""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user.id)
        sess['_fresh'] = True
    
    return client

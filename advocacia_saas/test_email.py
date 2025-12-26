#!/usr/bin/env python3
"""
Script para testar configuração de email com SendGrid
Execute: python test_email.py
"""

import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

def test_email_config():
    """Testa se as configurações de email estão corretas"""

    print("🔍 Verificando configuração de email...\n")

    # Verificar variáveis obrigatórias
    required_vars = [
        'MAIL_SERVER',
        'MAIL_PORT',
        'MAIL_USERNAME',
        'MAIL_PASSWORD',
        'MAIL_DEFAULT_SENDER'
    ]

    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            # Não mostrar senha completa por segurança
            if var == 'MAIL_PASSWORD' and len(value) > 10:
                display_value = value[:6] + "..." + value[-4:]
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")

    if missing_vars:
        print(f"\n❌ Variáveis faltando: {', '.join(missing_vars)}")
        print("\nConfigure estas variáveis no seu .env ou dashboard da plataforma:")
        print("""
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=apikey
MAIL_PASSWORD=SG.sua-api-key-aqui
MAIL_DEFAULT_SENDER=noreply@seudominio.com
        """)
        return False

    print("\n✅ Todas as variáveis de email estão configuradas!")

    # Testar import do Flask-Mail
    try:
        from flask_mail import Mail
        print("✅ Flask-Mail importado com sucesso")
    except ImportError:
        print("❌ Flask-Mail não instalado. Execute: pip install Flask-Mail")
        return False

    return True

def test_send_email():
    """Testa envio de email"""

    if not test_email_config():
        return

    print("\n📧 Testando envio de email...")

    try:
        from flask import Flask
        from app.utils.email import send_email

        # Criar app Flask mínimo para teste
        app = Flask(__name__)
        app.config.from_object('config.Config')

        with app.app_context():
            # Email de teste
            test_email = input("Digite seu email para teste: ").strip()

            if not test_email:
                print("❌ Email não fornecido")
                return

            # Dados de teste
            test_deadline = {
                'title': 'PRAZO DE TESTE - Configuração SendGrid',
                'user': {'name': 'Usuário de Teste'},
                'due_date': '2025-12-31',
                'days_until': 3
            }

            # Tentar enviar
            send_email(
                to=test_email,
                subject='🧪 Teste de Configuração - SendGrid',
                template='emails/deadline_alert.html',
                deadline=test_deadline
            )

            print(f"✅ Email de teste enviado para: {test_email}")
            print("Verifique sua caixa de entrada (e spam) em alguns minutos!")

    except Exception as e:
        print(f"❌ Erro ao enviar email: {e}")
        print("Verifique suas configurações do SendGrid")

if __name__ == "__main__":
    print("🚀 Teste de Configuração de Email - SendGrid\n")

    while True:
        print("\nEscolha uma opção:")
        print("1. Verificar configuração")
        print("2. Testar envio de email")
        print("3. Sair")

        choice = input("\nOpção: ").strip()

        if choice == '1':
            test_email_config()
        elif choice == '2':
            test_send_email()
        elif choice == '3':
            print("👋 Até logo!")
            break
        else:
            print("❌ Opção inválida")
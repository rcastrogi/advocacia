#!/usr/bin/env bash
# Script de build para Render.com

set -o errexit

echo "=== Instalando dependencias ==="
pip install -r requirements.txt

echo ""
echo "=== Inicializando banco de dados ==="
python << 'PYEND'
import sys
import traceback
from datetime import datetime

print(f"[{datetime.now()}] Iniciando script Python...")
print(f"Python version: {sys.version}")

try:
    print("\n[1/6] Importando modulos...")
    from app import create_app, db
    from app.models import User
    print("OK - Modulos importados")
    
    print("\n[2/6] Criando app Flask...")
    app = create_app()
    print(f"OK - App criado: {app}")
    
    print("\n[3/6] Entrando no contexto da aplicacao...")
    with app.app_context():
        print("OK - Contexto ativo")
        
        print("\n[4/6] Criando tabelas no banco de dados...")
        db.create_all()
        print("OK - Tabelas criadas (db.create_all() executado)")
        
        print("\n[5/6] Verificando usuario admin...")
        try:
            print("   Executando query: User.query.filter_by(email='admin@advocaciasaas.com').first()")
            admin = User.query.filter_by(email="admin@advocaciasaas.com").first()
            print(f"   Resultado da query: {admin}")
            
            if admin:
                print("OK - Usuario admin JA EXISTE no banco")
                print(f"   ID: {admin.id}")
                print(f"   Username: {admin.username}")
                print(f"   Email: {admin.email}")
                print(f"   User Type: {admin.user_type}")
            else:
                print("   Usuario admin NAO encontrado. Criando...")
                
                print("\n[6/6] Criando novo usuario admin...")
                admin = User(
                    username="admin",
                    email="admin@advocaciasaas.com",
                    full_name="Administrador do Sistema",
                    user_type="master",
                    oab_number="123456"
                )
                print(f"   Objeto User criado: {admin}")
                
                print("   Definindo senha...")
                admin.set_password("admin123", skip_history_check=True)
                print("   Senha definida")
                
                print("   Adicionando ao session...")
                db.session.add(admin)
                print("   Adicionado ao session")
                
                print("   Fazendo commit...")
                db.session.commit()
                print("   Commit realizado")
                
                print("\nSUCESSO - Usuario admin criado!")
                print("=" * 60)
                print("CREDENCIAIS DE LOGIN")
                print("=" * 60)
                print("Email: admin@advocaciasaas.com")
                print("Senha: admin123")
                print("=" * 60)
                
        except Exception as query_error:
            print(f"\nERRO na etapa de verificacao/criacao do admin:")
            print(f"Tipo: {type(query_error).__name__}")
            print(f"Mensagem: {str(query_error)}")
            traceback.print_exc()
            raise
            
except Exception as e:
    print(f"\n{'='*60}")
    print("ERRO CRITICO NO SCRIPT")
    print(f"{'='*60}")
    print(f"Tipo: {type(e).__name__}")
    print(f"Mensagem: {str(e)}")
    print(f"\nTraceback completo:")
    traceback.print_exc()
    print(f"{'='*60}")
    sys.exit(1)

print(f"\n[{datetime.now()}] Script concluido com sucesso!")
sys.exit(0)
        print("IMPORTANTE: Altere a senha apos o primeiro login!")
PYEND

echo ""
echo "=== Build concluido com sucesso! ==="
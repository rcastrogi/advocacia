#!/usr/bin/env python3
"""
Script para diagnosticar problemas de acesso ao painel admin
"""

import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User
from flask import Flask
from flask_login import current_user, login_user

def diagnose_admin_access():
    """Diagnóstica problemas de acesso ao painel admin"""

    app = create_app()

    with app.app_context():
        print("=== DIAGNÓSTICO DE ACESSO ADMIN ===")
        print(f"Data/Hora: {datetime.now()}")
        print()

        # Verificar usuários master
        master_users = User.query.filter_by(user_type="master").all()
        print(f"Usuários com tipo 'master': {len(master_users)}")

        for user in master_users:
            print(f"  - ID: {user.id}, Email: {user.email}, Nome: {user.full_name}")
            print(f"    Ativo: {user.is_active}, Tipo: {user.user_type}")

        print()

        # Verificar todos os usuários
        all_users = User.query.all()
        print(f"Total de usuários: {len(all_users)}")

        user_types = {}
        for user in all_users:
            user_type = user.user_type or "None"
            if user_type not in user_types:
                user_types[user_type] = 0
            user_types[user_type] += 1

        print("Distribuição por tipo:")
        for user_type, count in user_types.items():
            print(f"  - {user_type}: {count} usuários")

        print()

        # Verificar se existe algum usuário admin ativo
        active_masters = User.query.filter_by(user_type="master", is_active=True).all()
        if active_masters:
            print("✅ Existe(m) usuário(s) master ativo(s)")
            for user in active_masters:
                print(f"   Usuário: {user.email}")
        else:
            print("❌ Nenhum usuário master ativo encontrado!")
            print("   Isso explica por que não consegue acessar 'Gerenciar Usuários'")

        print()

        # Verificar rota admin
        try:
            from app.admin.routes import _require_admin
            print("✅ Função _require_admin() encontrada")

            # Simular teste de permissão (se houver usuário logado)
            if hasattr(app, 'login_manager') and current_user.is_authenticated:
                print(f"Usuário atual logado: {current_user.email} (tipo: {current_user.user_type})")
                try:
                    _require_admin()
                    print("✅ Usuário atual tem permissões admin")
                except Exception as e:
                    print(f"❌ Usuário atual NÃO tem permissões admin: {e}")
            else:
                print("ℹ️  Nenhum usuário logado no contexto atual")

        except ImportError as e:
            print(f"❌ Erro ao importar função admin: {e}")

        print()
        print("=== RECOMENDAÇÕES ===")

        if not active_masters:
            print("1. Criar um usuário master:")
            print("   - Execute: python create_admin_user.py")
            print("   - Ou crie manualmente via banco de dados")

        print("2. Verificar se está logado com usuário master")
        print("3. Se o problema persistir, verifique os logs em logs/portal.log")

if __name__ == "__main__":
    diagnose_admin_access()
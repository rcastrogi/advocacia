#!/usr/bin/env python3
"""
Script para verificar e corrigir acesso ao painel admin
"""

import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash


def fix_admin_access():
    """Corrige problemas de acesso ao painel admin"""

    app = create_app()

    with app.app_context():
        print("=== CORREÇÃO DE ACESSO ADMIN ===")
        print(f"Data/Hora: {datetime.now()}")
        print()

        # Verificar se existe usuário master
        master_user = User.query.filter_by(user_type="master").first()

        if master_user:
            print(f"✅ Usuário master encontrado: {master_user.email}")
            print(f"   ID: {master_user.id}")
            print(f"   Ativo: {master_user.is_active}")
            print(f"   Tipo: {master_user.user_type}")

            # Verificar se tem senha
            if not master_user.password_hash:
                print("⚠️  Usuário master não tem senha definida!")
                # Definir senha padrão
                default_password = "admin123"
                master_user.password_hash = generate_password_hash(default_password)
                db.session.commit()
                print(f"✅ Senha definida: {default_password}")
            else:
                print("✅ Usuário master tem senha definida")

        else:
            print("❌ Nenhum usuário master encontrado!")
            print("   Criando usuário master...")

            # Criar usuário master
            master_user = User(
                username="admin",
                email="admin@petitio.com",
                full_name="Administrador Master",
                user_type="master",
                is_active=True,
                password_hash=generate_password_hash("admin123"),
                created_at=datetime.utcnow(),
            )

            db.session.add(master_user)
            db.session.commit()

            print("✅ Usuário master criado!")
            print("   Email: admin@petitio.com")
            print("   Senha: admin123")

        print()
        print("=== INSTRUÇÕES DE ACESSO ===")
        print("Para acessar 'Gerenciar Usuários':")
        print("1. Faça logout se estiver logado")
        print("2. Vá para a página de login principal (não do portal)")
        print("3. Use as credenciais:")
        print(f"   Email: {master_user.email}")
        print("   Senha: admin123 (ou a senha atual se já tinha)")
        print("4. Após login, você verá o menu 'Administração' no topo")
        print("5. Clique em 'Usuários' no menu lateral esquerdo")

        print()
        print("=== VERIFICAÇÃO ===")
        print("URL para testar acesso direto:")
        print("http://localhost:5000/admin/usuarios")
        print("(Substitua localhost:5000 pela URL correta do seu ambiente)")


if __name__ == "__main__":
    fix_admin_access()

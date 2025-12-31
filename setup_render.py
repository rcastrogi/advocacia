#!/usr/bin/env python3
"""
Script básico para inicializar/setup do banco PostgreSQL no Render.
Apenas cria tabelas e aplica migrações - sem popular dados.
Execute apenas uma vez na primeira configuração.
"""

import os
import sys

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db


def setup_database():
    """Configura o banco de dados - cria tabelas"""
    print("🔧 Criando/verificando tabelas...")
    db.create_all()
    print("✅ Tabelas prontas")


def apply_migrations():
    """Aplica migrações pendentes"""
    print("📦 Aplicando migrações...")
    try:
        from flask_migrate import upgrade

        upgrade()
        print("✅ Migrações aplicadas")
    except Exception as e:
        print(f"⚠️ Erro nas migrações (pode ser normal se já aplicadas): {e}")


def show_summary():
    """Mostra resumo final"""
    from app.models import (
        BillingPlan,
        PetitionModel,
        PetitionSection,
        PetitionType,
        RoadmapCategory,
        User,
    )

    print("\n📊 RESUMO DA CONFIGURAÇÃO:")
    try:
        print(f"   Usuários: {User.query.count()}")
        print(f"   Planos: {BillingPlan.query.count()}")
        print(f"   Seções: {PetitionSection.query.count()}")
        print(f"   Tipos: {PetitionType.query.count()}")
        print(f"   Modelos: {PetitionModel.query.count()}")
        print(f"   Categorias Roadmap: {RoadmapCategory.query.count()}")
    except:
        print("   (Tabelas criadas, mas sem dados ainda)")

    print(
        "\n🎉 Setup básico completo! Use restore_render.py para popular dados se necessário."
    )


def main():
    """Função principal de setup básico"""
    print("🚀 Iniciando setup BÁSICO do banco PostgreSQL no Render...")
    print("📝 Este script SÓ cria tabelas e aplica migrações (sem dados)")

    # Criar app e contexto
    app = create_app()
    with app.app_context():
        try:
            setup_database()
            apply_migrations()
            show_summary()

        except Exception as e:
            print(f"❌ Erro durante setup: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()

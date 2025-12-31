#!/usr/bin/env python3
"""
Script básico para inicializar/setup do banco PostgreSQL no Render.
Apenas cria tabelas e aplica migrações - sem popular dados.
Execute apenas uma vez na primeira configuração.
"""

import os
import sys

# Adicionar o diretório raiz ao path
# No Render, o projeto está em /opt/render/project/src/advocacia_saas/
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, "advocacia_saas")
sys.path.insert(0, project_root)

from app import create_app, db


def setup_database():
    """Configura o banco de dados - cria tabelas"""
    print("🔧 Criando/verificando tabelas...")
    db.create_all()
    print("✅ Tabelas prontas")


def apply_migrations():
    """Aplica estrutura do banco via db.create_all() - mais confiável"""
    print("📦 Aplicando estrutura do banco...")
    try:
        # Usar db.create_all() que é mais confiável que flask db upgrade
        db.create_all()
        print("✅ Estrutura do banco aplicada com sucesso")
    except Exception as e:
        print(f"⚠️ Erro ao aplicar estrutura: {e}")
        # Tentar novamente
        try:
            db.create_all()
            print("✅ Estrutura aplicada na segunda tentativa")
        except Exception as e2:
            print(f"❌ Falha definitiva: {e2}")
            raise


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
    print("📝 Este script cria tabelas usando db.create_all() (estrutura atual)")

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

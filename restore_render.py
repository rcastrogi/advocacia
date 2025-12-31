#!/usr/bin/env python3
"""
Script para restaurar dados essenciais no banco PostgreSQL do Render.
Este script recria dados básicos após migrações: admin user, billing plans, petition sections, types e models.
"""

import os
import sys
from datetime import datetime, timezone
from decimal import Decimal

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import (
    User, BillingPlan, PetitionSection, PetitionType, PetitionModel,
    PetitionModelSection, RoadmapCategory, RoadmapItem
)

def create_admin_user():
    """Cria usuário admin se não existir"""
    admin = User.query.filter_by(email='admin@petitio.com').first()
    if not admin:
        admin = User(
            name='Administrador',
            email='admin@petitio.com',
            user_type='master',
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        admin.set_password('admin123')
        db.session.add(admin)
        print("✅ Usuário admin criado")
    else:
        print("ℹ️ Usuário admin já existe")

def create_billing_plans():
    """Cria planos de cobrança se não existirem"""
    plans_data = [
        {
            'name': 'Básico',
            'slug': 'basico',
            'price_monthly': Decimal('49.90'),
            'price_yearly': Decimal('499.00'),
            'petitions_limit': 50,
            'ai_credits_limit': 1000,
            'features': ['Geração de petições', 'Suporte básico', 'Templates básicos'],
            'is_active': True,
            'is_popular': False
        },
        {
            'name': 'Profissional',
            'slug': 'profissional',
            'price_monthly': Decimal('99.90'),
            'price_yearly': Decimal('999.00'),
            'petitions_limit': 50,
            'ai_credits_limit': 5000,
            'features': ['Tudo do Básico', 'Templates avançados', 'Suporte prioritário', 'Relatórios'],
            'is_active': True,
            'is_popular': True
        },
        {
            'name': 'Empresarial',
            'slug': 'empresarial',
            'price_monthly': Decimal('199.90'),
            'price_yearly': Decimal('1999.00'),
            'petitions_limit': -1,  # ilimitado
            'ai_credits_limit': -1,  # ilimitado
            'features': ['Tudo do Profissional', 'API access', 'Suporte 24/7', 'Consultoria'],
            'is_active': True,
            'is_popular': False
        }
    ]

    for plan_data in plans_data:
        plan = BillingPlan.query.filter_by(slug=plan_data['slug']).first()
        if not plan:
            plan = BillingPlan(**plan_data)
            db.session.add(plan)
            print(f"✅ Plano '{plan_data['name']}' criado")
        else:
            print(f"ℹ️ Plano '{plan_data['name']}' já existe")

def create_petition_sections():
    """Cria seções de petição se não existirem"""
    sections_data = [
        {'name': 'Cabeçalho', 'slug': 'cabecalho', 'description': 'Cabeçalho da petição', 'order': 1, 'is_required': True},
        {'name': 'Qualificação', 'slug': 'qualificacao', 'description': 'Qualificação das partes', 'order': 2, 'is_required': True},
        {'name': 'Fatos', 'slug': 'fatos', 'description': 'Narrativa dos fatos', 'order': 3, 'is_required': True},
        {'name': 'Direito', 'slug': 'direito', 'description': 'Fundamentação jurídica', 'order': 4, 'is_required': True},
        {'name': 'Pedidos', 'slug': 'pedidos', 'description': 'Pedidos formulados', 'order': 5, 'is_required': True},
        {'name': 'Fechamento', 'slug': 'fechamento', 'description': 'Fechamento da petição', 'order': 6, 'is_required': True}
    ]

    for section_data in sections_data:
        section = PetitionSection.query.filter_by(slug=section_data['slug']).first()
        if not section:
            section = PetitionSection(**section_data)
            db.session.add(section)
            print(f"✅ Seção '{section_data['name']}' criada")
        else:
            print(f"ℹ️ Seção '{section_data['name']}' já existe")

def create_petition_types():
    """Cria tipos de petição se não existirem"""
    types_data = [
        {
            'name': 'Ação de Cobrança',
            'slug': 'acao-cobranca',
            'description': 'Petição inicial para ação de cobrança',
            'category': 'civel',
            'icon': 'fa-money-bill',
            'color': 'success',
            'is_billable': True,
            'base_price': Decimal('50.00'),
            'use_dynamic_form': True,
            'is_active': True
        },
        {
            'name': 'Contestação',
            'slug': 'contestacao',
            'description': 'Contestação em processo judicial',
            'category': 'civel',
            'icon': 'fa-gavel',
            'color': 'warning',
            'is_billable': True,
            'base_price': Decimal('75.00'),
            'use_dynamic_form': True,
            'is_active': True
        },
        {
            'name': 'Agravo de Instrumento',
            'slug': 'agravo-instrumento',
            'description': 'Agravo de instrumento',
            'category': 'civel',
            'icon': 'fa-file-contract',
            'color': 'info',
            'is_billable': True,
            'base_price': Decimal('100.00'),
            'use_dynamic_form': True,
            'is_active': True
        },
        {
            'name': 'Recurso Especial',
            'slug': 'recurso-especial',
            'description': 'Recurso especial para STJ',
            'category': 'civel',
            'icon': 'fa-balance-scale',
            'color': 'primary',
            'is_billable': True,
            'base_price': Decimal('150.00'),
            'use_dynamic_form': True,
            'is_active': True
        }
    ]

    for type_data in types_data:
        petition_type = PetitionType.query.filter_by(slug=type_data['slug']).first()
        if not petition_type:
            petition_type = PetitionType(**type_data)
            db.session.add(petition_type)
            print(f"✅ Tipo '{type_data['name']}' criado")
        else:
            print(f"ℹ️ Tipo '{type_data['name']}' já existe")

def create_petition_models():
    """Cria modelos de petição se não existirem"""
    models_data = [
        {
            'name': 'Modelo - Ação de Cobrança Básica',
            'slug': 'modelo-acao-cobranca-basica',
            'description': 'Modelo básico para ação de cobrança',
            'petition_type_id': 1,  # Assumindo que será o primeiro tipo criado
            'is_active': True,
            'use_dynamic_form': True,
            'template_content': 'Template básico para ação de cobrança...'
        },
        {
            'name': 'Modelo - Contestação Simples',
            'slug': 'modelo-contestacao-simples',
            'description': 'Modelo simples para contestação',
            'petition_type_id': 2,
            'is_active': True,
            'use_dynamic_form': True,
            'template_content': 'Template básico para contestação...'
        },
        {
            'name': 'Modelo - Agravo de Instrumento',
            'slug': 'modelo-agravo-instrumento',
            'description': 'Modelo para agravo de instrumento',
            'petition_type_id': 3,
            'is_active': True,
            'use_dynamic_form': True,
            'template_content': 'Template básico para agravo de instrumento...'
        },
        {
            'name': 'Modelo - Recurso Especial',
            'slug': 'modelo-recurso-especial',
            'description': 'Modelo para recurso especial',
            'petition_type_id': 4,
            'is_active': True,
            'use_dynamic_form': True,
            'template_content': 'Template básico para recurso especial...'
        }
    ]

    for model_data in models_data:
        model = PetitionModel.query.filter_by(slug=model_data['slug']).first()
        if not model:
            model = PetitionModel(**model_data)
            db.session.add(model)
            print(f"✅ Modelo '{model_data['name']}' criado")
        else:
            print(f"ℹ️ Modelo '{model_data['name']}' já existe")

def create_roadmap_categories():
    """Cria categorias do roadmap se não existirem"""
    categories_data = [
        {'name': 'Funcionalidades', 'slug': 'funcionalidades', 'description': 'Novas funcionalidades', 'icon': 'fa-lightbulb', 'color': 'primary', 'order': 1, 'is_active': True},
        {'name': 'Melhorias', 'slug': 'melhorias', 'description': 'Melhorias existentes', 'icon': 'fa-tools', 'color': 'success', 'order': 2, 'is_active': True},
        {'name': 'Correções', 'slug': 'correcoes', 'description': 'Correções de bugs', 'icon': 'fa-bug', 'color': 'warning', 'order': 3, 'is_active': True},
        {'name': 'Integrações', 'slug': 'integracoes', 'description': 'Integrações externas', 'icon': 'fa-plug', 'color': 'info', 'order': 4, 'is_active': True}
    ]

    for cat_data in categories_data:
        category = RoadmapCategory.query.filter_by(slug=cat_data['slug']).first()
        if not category:
            category = RoadmapCategory(**cat_data)
            db.session.add(category)
            print(f"✅ Categoria '{cat_data['name']}' criada")
        else:
            print(f"ℹ️ Categoria '{cat_data['name']}' já existe")

def main():
    """Função principal"""
    print("🚀 Iniciando restauração de dados no Render...")

    # Criar app e contexto
    app = create_app()
    with app.app_context():
        try:
            # Criar tabelas se não existirem (por segurança)
            db.create_all()
            print("✅ Tabelas verificadas/criadas")

            # Restaurar dados
            create_admin_user()
            create_billing_plans()
            create_petition_sections()
            create_petition_types()
            create_petition_models()
            create_roadmap_categories()

            # Commit final
            db.session.commit()
            print("✅ Todos os dados restaurados com sucesso!")

            # Verificar contagens
            print("\n📊 Verificação final:")
            print(f"   Usuários: {User.query.count()}")
            print(f"   Planos: {BillingPlan.query.count()}")
            print(f"   Seções: {PetitionSection.query.count()}")
            print(f"   Tipos: {PetitionType.query.count()}")
            print(f"   Modelos: {PetitionModel.query.count()}")
            print(f"   Categorias Roadmap: {RoadmapCategory.query.count()}")

        except Exception as e:
            print(f"❌ Erro durante restauração: {e}")
            db.session.rollback()
            sys.exit(1)

if __name__ == '__main__':
    main()
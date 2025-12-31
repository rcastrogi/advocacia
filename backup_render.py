#!/usr/bin/env python3
"""
Script para exportar dados do banco PostgreSQL do Render para backup.
Salva dados em JSON para importação posterior.
"""

import os
import sys
import json
from datetime import datetime
from decimal import Decimal

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import (
    User, BillingPlan, PetitionSection, PetitionType, PetitionModel,
    PetitionModelSection, RoadmapCategory, RoadmapItem, RoadmapFeedback,
    Client, PetitionUsage, Payment, UserCredits, AIGeneration,
    SavedPetition, UserPlan
)

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def export_users():
    """Exporta usuários"""
    users = User.query.all()
    return [{
        'id': u.id,
        'name': u.name,
        'email': u.email,
        'user_type': u.user_type,
        'is_active': u.is_active,
        'created_at': u.created_at.isoformat() if u.created_at else None,
        'last_login': u.last_login.isoformat() if u.last_login else None,
        'phone': u.phone,
        'company': u.company,
        'oab_number': u.oab_number,
        'specialization': u.specialization,
        'trial_ends_at': u.trial_ends_at.isoformat() if u.trial_ends_at else None,
        'subscription_status': u.subscription_status,
        'stripe_customer_id': u.stripe_customer_id,
        'mercadopago_customer_id': u.mercadopago_customer_id
    } for u in users]

def export_billing_plans():
    """Exporta planos de cobrança"""
    plans = BillingPlan.query.all()
    return [{
        'id': p.id,
        'name': p.name,
        'slug': p.slug,
        'price_monthly': float(p.price_monthly),
        'price_yearly': float(p.price_yearly),
        'petitions_limit': p.petitions_limit,
        'ai_credits_limit': p.ai_credits_limit,
        'features': p.features,
        'is_active': p.is_active,
        'is_popular': p.is_popular,
        'created_at': p.created_at.isoformat() if p.created_at else None
    } for p in plans]

def export_petition_sections():
    """Exporta seções de petição"""
    sections = PetitionSection.query.all()
    return [{
        'id': s.id,
        'name': s.name,
        'slug': s.slug,
        'description': s.description,
        'order': s.order,
        'is_required': s.is_required,
        'is_active': s.is_active,
        'created_at': s.created_at.isoformat() if s.created_at else None
    } for s in sections]

def export_petition_types():
    """Exporta tipos de petição"""
    types = PetitionType.query.all()
    return [{
        'id': t.id,
        'name': t.name,
        'slug': t.slug,
        'description': t.description,
        'category': t.category,
        'icon': t.icon,
        'color': t.color,
        'is_billable': t.is_billable,
        'base_price': float(t.base_price),
        'use_dynamic_form': t.use_dynamic_form,
        'is_active': t.is_active,
        'created_at': t.created_at.isoformat() if t.created_at else None
    } for t in types]

def export_petition_models():
    """Exporta modelos de petição"""
    models = PetitionModel.query.all()
    return [{
        'id': m.id,
        'name': m.name,
        'slug': m.slug,
        'description': m.description,
        'petition_type_id': m.petition_type_id,
        'is_active': m.is_active,
        'use_dynamic_form': m.use_dynamic_form,
        'template_content': m.template_content,
        'created_at': m.created_at.isoformat() if m.created_at else None
    } for m in models]

def export_roadmap_categories():
    """Exporta categorias do roadmap"""
    categories = RoadmapCategory.query.all()
    return [{
        'id': c.id,
        'name': c.name,
        'slug': c.slug,
        'description': c.description,
        'icon': c.icon,
        'color': c.color,
        'order': c.order,
        'is_active': c.is_active,
        'created_at': c.created_at.isoformat() if c.created_at else None
    } for c in categories]

def export_roadmap_items():
    """Exporta itens do roadmap"""
    items = RoadmapItem.query.all()
    return [{
        'id': i.id,
        'category_id': i.category_id,
        'title': i.title,
        'slug': i.slug,
        'description': i.description,
        'detailed_description': i.detailed_description,
        'status': i.status,
        'priority': i.priority,
        'estimated_effort': i.estimated_effort,
        'visible_to_users': i.visible_to_users,
        'internal_only': i.internal_only,
        'show_new_badge': i.show_new_badge,
        'planned_start_date': i.planned_start_date.isoformat() if i.planned_start_date else None,
        'planned_completion_date': i.planned_completion_date.isoformat() if i.planned_completion_date else None,
        'actual_start_date': i.actual_start_date.isoformat() if i.actual_start_date else None,
        'actual_completion_date': i.actual_completion_date.isoformat() if i.actual_completion_date else None,
        'business_value': i.business_value,
        'technical_complexity': i.technical_complexity,
        'user_impact': i.user_impact,
        'dependencies': i.dependencies,
        'blockers': i.blockers,
        'tags': i.tags,
        'notes': i.notes,
        'assigned_to': i.assigned_to,
        'created_by': i.created_by,
        'last_updated_by': i.last_updated_by,
        'created_at': i.created_at.isoformat() if i.created_at else None,
        'updated_at': i.updated_at.isoformat() if i.updated_at else None
    } for i in items]

def export_clients():
    """Exporta clientes"""
    clients = Client.query.all()
    return [{
        'id': c.id,
        'lawyer_id': c.lawyer_id,
        'name': c.name,
        'email': c.email,
        'phone': c.phone,
        'cpf_cnpj': c.cpf_cnpj,
        'address': c.address,
        'city': c.city,
        'state': c.state,
        'zip_code': c.zip_code,
        'notes': c.notes,
        'created_at': c.created_at.isoformat() if c.created_at else None
    } for c in clients]

def export_petition_usage():
    """Exporta uso de petições"""
    usages = PetitionUsage.query.all()
    return [{
        'id': u.id,
        'user_id': u.user_id,
        'petition_type_id': u.petition_type_id,
        'amount': float(u.amount),
        'generated_at': u.generated_at.isoformat() if u.generated_at else None,
        'content': u.content,
        'metadata': u.metadata
    } for u in usages]

def export_payments():
    """Exporta pagamentos"""
    payments = Payment.query.all()
    return [{
        'id': p.id,
        'user_id': p.user_id,
        'amount': float(p.amount),
        'currency': p.currency,
        'payment_method': p.payment_method,
        'payment_status': p.payment_status,
        'external_payment_id': p.external_payment_id,
        'paid_at': p.paid_at.isoformat() if p.paid_at else None,
        'metadata': p.metadata,
        'created_at': p.created_at.isoformat() if p.created_at else None
    } for p in payments]

def export_user_credits():
    """Exporta créditos de IA dos usuários"""
    credits = UserCredits.query.all()
    return [{
        'id': c.id,
        'user_id': c.user_id,
        'balance': c.balance,
        'total_used': c.total_used,
        'last_updated': c.last_updated.isoformat() if c.last_updated else None
    } for c in credits]

def export_ai_generations():
    """Exporta gerações de IA"""
    generations = AIGeneration.query.all()
    return [{
        'id': g.id,
        'user_id': g.user_id,
        'prompt': g.prompt,
        'response': g.response,
        'tokens_total': g.tokens_total,
        'cost_usd': float(g.cost_usd) if g.cost_usd else None,
        'model_used': g.model_used,
        'created_at': g.created_at.isoformat() if g.created_at else None
    } for g in generations]

def main():
    """Função principal de exportação"""
    print("🚀 Iniciando exportação de dados do Render...")

    # Criar app e contexto
    app = create_app()
    with app.app_context():
        try:
            # Coletar todos os dados
            data = {
                'exported_at': datetime.now().isoformat(),
                'database_type': 'postgresql_render',
                'users': export_users(),
                'billing_plans': export_billing_plans(),
                'petition_sections': export_petition_sections(),
                'petition_types': export_petition_types(),
                'petition_models': export_petition_models(),
                'roadmap_categories': export_roadmap_categories(),
                'roadmap_items': export_roadmap_items(),
                'clients': export_clients(),
                'petition_usage': export_petition_usage(),
                'payments': export_payments(),
                'user_credits': export_user_credits(),
                'ai_generations': export_ai_generations()
            }

            # Salvar em arquivo JSON
            filename = f'backup_render_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, cls=DecimalEncoder)

            print(f"✅ Backup salvo em: {filename}")
            print("📊 Estatísticas do backup:")
            print(f"   Usuários: {len(data['users'])}")
            print(f"   Planos: {len(data['billing_plans'])}")
            print(f"   Seções: {len(data['petition_sections'])}")
            print(f"   Tipos: {len(data['petition_types'])}")
            print(f"   Modelos: {len(data['petition_models'])}")
            print(f"   Categorias Roadmap: {len(data['roadmap_categories'])}")
            print(f"   Itens Roadmap: {len(data['roadmap_items'])}")
            print(f"   Clientes: {len(data['clients'])}")
            print(f"   Uso de Petições: {len(data['petition_usage'])}")
            print(f"   Pagamentos: {len(data['payments'])}")
            print(f"   Créditos IA: {len(data['user_credits'])}")
            print(f"   Gerações IA: {len(data['ai_generations'])}")

            print(f"\n📁 Baixe o arquivo '{filename}' do Render e use-o para importar localmente.")

        except Exception as e:
            print(f"❌ Erro durante exportação: {e}")
            sys.exit(1)

if __name__ == '__main__':
    main()
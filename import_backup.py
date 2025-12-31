#!/usr/bin/env python3
"""
Script para importar dados do backup do Render para o banco local SQLite.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import (
    AIGeneration,
    BillingPlan,
    Client,
    Payment,
    PetitionModel,
    PetitionModelSection,
    PetitionSection,
    PetitionType,
    PetitionUsage,
    RoadmapCategory,
    RoadmapFeedback,
    RoadmapItem,
    SavedPetition,
    User,
    UserCredits,
    UserPlan,
)


def parse_datetime(date_str):
    """Converte string ISO para datetime"""
    if not date_str:
        return None
    try:
        # Remover 'Z' se existir e adicionar timezone
        if date_str.endswith("Z"):
            date_str = date_str[:-1] + "+00:00"
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except:
        return None


def import_users(data):
    """Importa usuários"""
    print(f"📥 Importando {len(data)} usuários...")
    count = 0
    for user_data in data:
        # Verificar se já existe
        existing = User.query.filter_by(email=user_data["email"]).first()
        if existing:
            print(f"   ℹ️ Usuário {user_data['email']} já existe, pulando...")
            continue

        user = User(
            name=user_data["name"],
            email=user_data["email"],
            user_type=user_data["user_type"],
            is_active=user_data["is_active"],
            created_at=parse_datetime(user_data["created_at"]),
            last_login=parse_datetime(user_data["last_login"]),
            phone=user_data.get("phone"),
            company=user_data.get("company"),
            oab_number=user_data.get("oab_number"),
            specialization=user_data.get("specialization"),
            trial_ends_at=parse_datetime(user_data.get("trial_ends_at")),
            subscription_status=user_data.get("subscription_status"),
            stripe_customer_id=user_data.get("stripe_customer_id"),
            mercadopago_customer_id=user_data.get("mercadopago_customer_id"),
        )
        # Se não tem senha, definir uma padrão
        if not hasattr(user, "password_hash") or not user.password_hash:
            user.set_password("temp123")  # Senha temporária

        db.session.add(user)
        count += 1

    db.session.commit()
    print(f"✅ {count} usuários importados")


def import_billing_plans(data):
    """Importa planos de cobrança"""
    print(f"📥 Importando {len(data)} planos...")
    count = 0
    for plan_data in data:
        existing = BillingPlan.query.filter_by(slug=plan_data["slug"]).first()
        if existing:
            print(f"   ℹ️ Plano {plan_data['name']} já existe, pulando...")
            continue

        plan = BillingPlan(
            name=plan_data["name"],
            slug=plan_data["slug"],
            price_monthly=Decimal(str(plan_data["price_monthly"])),
            price_yearly=Decimal(str(plan_data["price_yearly"])),
            petitions_limit=plan_data["petitions_limit"],
            ai_credits_limit=plan_data["ai_credits_limit"],
            features=plan_data["features"],
            is_active=plan_data["is_active"],
            is_popular=plan_data["is_popular"],
            created_at=parse_datetime(plan_data["created_at"]),
        )
        db.session.add(plan)
        count += 1

    db.session.commit()
    print(f"✅ {count} planos importados")


def import_petition_sections(data):
    """Importa seções de petição"""
    print(f"📥 Importando {len(data)} seções...")
    count = 0
    for section_data in data:
        existing = PetitionSection.query.filter_by(slug=section_data["slug"]).first()
        if existing:
            print(f"   ℹ️ Seção {section_data['name']} já existe, pulando...")
            continue

        section = PetitionSection(
            name=section_data["name"],
            slug=section_data["slug"],
            description=section_data["description"],
            order=section_data["order"],
            is_required=section_data["is_required"],
            is_active=section_data["is_active"],
            created_at=parse_datetime(section_data["created_at"]),
        )
        db.session.add(section)
        count += 1

    db.session.commit()
    print(f"✅ {count} seções importadas")


def import_petition_types(data):
    """Importa tipos de petição"""
    print(f"📥 Importando {len(data)} tipos...")
    count = 0
    for type_data in data:
        existing = PetitionType.query.filter_by(slug=type_data["slug"]).first()
        if existing:
            print(f"   ℹ️ Tipo {type_data['name']} já existe, pulando...")
            continue

        petition_type = PetitionType(
            name=type_data["name"],
            slug=type_data["slug"],
            description=type_data["description"],
            category=type_data["category"],
            icon=type_data["icon"],
            color=type_data["color"],
            is_billable=type_data["is_billable"],
            base_price=Decimal(str(type_data["base_price"])),
            use_dynamic_form=type_data["use_dynamic_form"],
            is_active=type_data["is_active"],
            created_at=parse_datetime(type_data["created_at"]),
        )
        db.session.add(petition_type)
        count += 1

    db.session.commit()
    print(f"✅ {count} tipos importados")


def import_petition_models(data):
    """Importa modelos de petição"""
    print(f"📥 Importando {len(data)} modelos...")
    count = 0
    for model_data in data:
        existing = PetitionModel.query.filter_by(slug=model_data["slug"]).first()
        if existing:
            print(f"   ℹ️ Modelo {model_data['name']} já existe, pulando...")
            continue

        model = PetitionModel(
            name=model_data["name"],
            slug=model_data["slug"],
            description=model_data["description"],
            petition_type_id=model_data["petition_type_id"],
            is_active=model_data["is_active"],
            use_dynamic_form=model_data["use_dynamic_form"],
            template_content=model_data["template_content"],
            created_at=parse_datetime(model_data["created_at"]),
        )
        db.session.add(model)
        count += 1

    db.session.commit()
    print(f"✅ {count} modelos importados")


def import_roadmap_categories(data):
    """Importa categorias do roadmap"""
    print(f"📥 Importando {len(data)} categorias do roadmap...")
    count = 0
    for cat_data in data:
        existing = RoadmapCategory.query.filter_by(slug=cat_data["slug"]).first()
        if existing:
            print(f"   ℹ️ Categoria {cat_data['name']} já existe, pulando...")
            continue

        category = RoadmapCategory(
            name=cat_data["name"],
            slug=cat_data["slug"],
            description=cat_data["description"],
            icon=cat_data["icon"],
            color=cat_data["color"],
            order=cat_data["order"],
            is_active=cat_data["is_active"],
            created_at=parse_datetime(cat_data["created_at"]),
        )
        db.session.add(category)
        count += 1

    db.session.commit()
    print(f"✅ {count} categorias importadas")


def import_roadmap_items(data):
    """Importa itens do roadmap"""
    print(f"📥 Importando {len(data)} itens do roadmap...")
    count = 0
    for item_data in data:
        existing = RoadmapItem.query.filter_by(slug=item_data["slug"]).first()
        if existing:
            print(f"   ℹ️ Item {item_data['title']} já existe, pulando...")
            continue

        item = RoadmapItem(
            category_id=item_data["category_id"],
            title=item_data["title"],
            slug=item_data["slug"],
            description=item_data["description"],
            detailed_description=item_data["detailed_description"],
            status=item_data["status"],
            priority=item_data["priority"],
            estimated_effort=item_data["estimated_effort"],
            visible_to_users=item_data["visible_to_users"],
            internal_only=item_data["internal_only"],
            show_new_badge=item_data["show_new_badge"],
            planned_start_date=parse_datetime(item_data["planned_start_date"]),
            planned_completion_date=parse_datetime(
                item_data["planned_completion_date"]
            ),
            actual_start_date=parse_datetime(item_data["actual_start_date"]),
            actual_completion_date=parse_datetime(item_data["actual_completion_date"]),
            business_value=item_data["business_value"],
            technical_complexity=item_data["technical_complexity"],
            user_impact=item_data["user_impact"],
            dependencies=item_data["dependencies"],
            blockers=item_data["blockers"],
            tags=item_data["tags"],
            notes=item_data["notes"],
            assigned_to=item_data["assigned_to"],
            created_by=item_data["created_by"],
            last_updated_by=item_data["last_updated_by"],
            created_at=parse_datetime(item_data["created_at"]),
            updated_at=parse_datetime(item_data["updated_at"]),
        )
        db.session.add(item)
        count += 1

    db.session.commit()
    print(f"✅ {count} itens importados")


def import_clients(data):
    """Importa clientes"""
    print(f"📥 Importando {len(data)} clientes...")
    count = 0
    for client_data in data:
        # Verificar se já existe (mesmo lawyer_id e email)
        existing = Client.query.filter_by(
            lawyer_id=client_data["lawyer_id"], email=client_data["email"]
        ).first()
        if existing:
            print(f"   ℹ️ Cliente {client_data['name']} já existe, pulando...")
            continue

        client = Client(
            lawyer_id=client_data["lawyer_id"],
            name=client_data["name"],
            email=client_data["email"],
            phone=client_data.get("phone"),
            cpf_cnpj=client_data.get("cpf_cnpj"),
            address=client_data.get("address"),
            city=client_data.get("city"),
            state=client_data.get("state"),
            zip_code=client_data.get("zip_code"),
            notes=client_data.get("notes"),
            created_at=parse_datetime(client_data["created_at"]),
        )
        db.session.add(client)
        count += 1

    db.session.commit()
    print(f"✅ {count} clientes importados")


def import_petition_usage(data):
    """Importa uso de petições"""
    print(f"📥 Importando {len(data)} registros de uso...")
    count = 0
    for usage_data in data:
        # Evitar duplicatas - verificar se já existe com mesmo user_id e generated_at
        existing = PetitionUsage.query.filter_by(
            user_id=usage_data["user_id"],
            generated_at=parse_datetime(usage_data["generated_at"]),
        ).first()
        if existing:
            continue

        usage = PetitionUsage(
            user_id=usage_data["user_id"],
            petition_type_id=usage_data["petition_type_id"],
            amount=Decimal(str(usage_data["amount"])),
            generated_at=parse_datetime(usage_data["generated_at"]),
            content=usage_data.get("content"),
            metadata=usage_data.get("metadata"),
        )
        db.session.add(usage)
        count += 1

    db.session.commit()
    print(f"✅ {count} registros de uso importados")


def import_payments(data):
    """Importa pagamentos"""
    print(f"📥 Importando {len(data)} pagamentos...")
    count = 0
    for payment_data in data:
        # Evitar duplicatas por external_payment_id
        if payment_data.get("external_payment_id"):
            existing = Payment.query.filter_by(
                external_payment_id=payment_data["external_payment_id"]
            ).first()
            if existing:
                continue

        payment = Payment(
            user_id=payment_data["user_id"],
            amount=Decimal(str(payment_data["amount"])),
            currency=payment_data["currency"],
            payment_method=payment_data["payment_method"],
            payment_status=payment_data["payment_status"],
            external_payment_id=payment_data.get("external_payment_id"),
            paid_at=parse_datetime(payment_data["paid_at"]),
            metadata=payment_data.get("metadata"),
            created_at=parse_datetime(payment_data["created_at"]),
        )
        db.session.add(payment)
        count += 1

    db.session.commit()
    print(f"✅ {count} pagamentos importados")


def import_user_credits(data):
    """Importa créditos de IA"""
    print(f"📥 Importando {len(data)} registros de créditos...")
    count = 0
    for credit_data in data:
        existing = UserCredits.query.filter_by(user_id=credit_data["user_id"]).first()
        if existing:
            # Atualizar se já existe
            existing.balance = credit_data["balance"]
            existing.total_used = credit_data["total_used"]
            existing.last_updated = parse_datetime(credit_data["last_updated"])
        else:
            credit = UserCredits(
                user_id=credit_data["user_id"],
                balance=credit_data["balance"],
                total_used=credit_data["total_used"],
                last_updated=parse_datetime(credit_data["last_updated"]),
            )
            db.session.add(credit)
            count += 1

    db.session.commit()
    print(f"✅ {count} registros de créditos importados/atualizados")


def import_ai_generations(data):
    """Importa gerações de IA"""
    print(f"📥 Importando {len(data)} gerações de IA...")
    count = 0
    for gen_data in data:
        # Evitar duplicatas - verificar por user_id e created_at
        existing = AIGeneration.query.filter_by(
            user_id=gen_data["user_id"],
            created_at=parse_datetime(gen_data["created_at"]),
        ).first()
        if existing:
            continue

        generation = AIGeneration(
            user_id=gen_data["user_id"],
            prompt=gen_data.get("prompt"),
            response=gen_data.get("response"),
            tokens_total=gen_data.get("tokens_total"),
            cost_usd=Decimal(str(gen_data["cost_usd"]))
            if gen_data.get("cost_usd")
            else None,
            model_used=gen_data.get("model_used"),
            created_at=parse_datetime(gen_data["created_at"]),
        )
        db.session.add(generation)
        count += 1

    db.session.commit()
    print(f"✅ {count} gerações de IA importadas")


def main():
    parser = argparse.ArgumentParser(
        description="Importar backup do Render para SQLite local"
    )
    parser.add_argument("backup_file", help="Arquivo JSON do backup")
    args = parser.parse_args()

    if not os.path.exists(args.backup_file):
        print(f"❌ Arquivo {args.backup_file} não encontrado!")
        sys.exit(1)

    print(f"🚀 Iniciando importação do backup: {args.backup_file}")

    # Carregar dados
    with open(args.backup_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"📅 Backup exportado em: {data['exported_at']}")
    print(f"🗄️ Origem: {data['database_type']}")

    # Criar app e contexto
    app = create_app()
    with app.app_context():
        try:
            # Importar em ordem de dependências
            import_users(data["users"])
            import_billing_plans(data["billing_plans"])
            import_petition_sections(data["petition_sections"])
            import_petition_types(data["petition_types"])
            import_petition_models(data["petition_models"])
            import_roadmap_categories(data["roadmap_categories"])
            import_roadmap_items(data["roadmap_items"])
            import_clients(data["clients"])
            import_petition_usage(data["petition_usage"])
            import_payments(data["payments"])
            import_user_credits(data["user_credits"])
            import_ai_generations(data["ai_generations"])

            print("\n✅ Importação concluída com sucesso!")
            print(
                "🔄 Execute 'flask db upgrade' se necessário para sincronizar migrações."
            )

        except Exception as e:
            print(f"❌ Erro durante importação: {e}")
            db.session.rollback()
            sys.exit(1)


if __name__ == "__main__":
    main()

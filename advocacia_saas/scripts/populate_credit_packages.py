"""
Script para popular pacotes de créditos de IA no banco de dados
"""

import os
import sys

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db
from app.models import CreditPackage


def create_credit_packages():
    """Cria os pacotes de créditos iniciais"""

    packages = [
        {
            "name": "Starter",
            "slug": "starter",
            "credits": 50,
            "bonus_credits": 0,
            "price": 49.90,
            "description": "Ideal para começar a usar IA nas suas petições",
            "is_active": True,
            "is_featured": False,
            "sort_order": 1,
        },
        {
            "name": "Professional",
            "slug": "professional",
            "credits": 150,
            "bonus_credits": 20,
            "price": 129.90,
            "original_price": 149.90,
            "description": "Melhor custo-benefício para advogados ativos",
            "is_active": True,
            "is_featured": True,
            "sort_order": 2,
        },
        {
            "name": "Business",
            "slug": "business",
            "credits": 300,
            "bonus_credits": 50,
            "price": 239.90,
            "original_price": 299.90,
            "description": "Para escritórios com alto volume de petições",
            "is_active": True,
            "is_featured": False,
            "sort_order": 3,
        },
        {
            "name": "Enterprise",
            "slug": "enterprise",
            "credits": 500,
            "bonus_credits": 100,
            "price": 379.90,
            "original_price": 499.90,
            "description": "Pacote completo para grandes escritórios",
            "is_active": True,
            "is_featured": False,
            "sort_order": 4,
        },
    ]

    app = create_app()

    with app.app_context():
        print("Criando pacotes de créditos...")

        for pkg_data in packages:
            # Verificar se já existe
            existing = CreditPackage.query.filter_by(slug=pkg_data["slug"]).first()

            if existing:
                print(f"  ⚠️  Pacote '{pkg_data['name']}' já existe, atualizando...")
                for key, value in pkg_data.items():
                    setattr(existing, key, value)
            else:
                print(f"  ✅ Criando pacote '{pkg_data['name']}'...")
                package = CreditPackage(**pkg_data)
                db.session.add(package)

        db.session.commit()
        print("\n✨ Pacotes de créditos criados com sucesso!")
        print("\nPacotes disponíveis:")

        all_packages = CreditPackage.query.order_by(CreditPackage.sort_order).all()
        for pkg in all_packages:
            print(f"\n  📦 {pkg.name}")
            print(
                f"     Créditos: {pkg.credits} + {pkg.bonus_credits} bônus = {pkg.total_credits}"
            )
            print(f"     Preço: R$ {pkg.price}")
            print(f"     URL: /ai/credits/buy/{pkg.slug}")


if __name__ == "__main__":
    create_credit_packages()

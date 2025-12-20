"""
Script para configurar os pacotes de créditos padrão.
Execute com: flask shell < scripts/setup_credit_packages.py
ou: python scripts/setup_credit_packages.py
"""

from app import create_app, db
from app.models import CreditPackage


def setup_packages():
    """Cria os pacotes de créditos padrão"""

    packages = [
        {
            "name": "50 Créditos",
            "slug": "creditos-50",
            "credits": 50,
            "bonus_credits": 0,
            "price": 29.90,
            "original_price": None,
            "description": "Pacote inicial para começar a usar a IA",
            "is_active": True,
            "is_featured": False,
            "sort_order": 1,
        },
        {
            "name": "150 Créditos",
            "slug": "creditos-150",
            "credits": 150,
            "bonus_credits": 15,  # 10% bônus
            "price": 69.90,
            "original_price": 89.90,
            "description": "Melhor custo-benefício! Inclui 15 créditos bônus",
            "is_active": True,
            "is_featured": True,  # Destaque
            "sort_order": 2,
        },
        {
            "name": "500 Créditos",
            "slug": "creditos-500",
            "credits": 500,
            "bonus_credits": 100,  # 20% bônus
            "price": 199.90,
            "original_price": 299.90,
            "description": "Para uso profissional intensivo. Inclui 100 créditos bônus!",
            "is_active": True,
            "is_featured": False,
            "sort_order": 3,
        },
    ]

    created = 0
    updated = 0

    for pkg_data in packages:
        existing = CreditPackage.query.filter_by(slug=pkg_data["slug"]).first()

        if existing:
            # Atualiza o pacote existente
            for key, value in pkg_data.items():
                setattr(existing, key, value)
            updated += 1
            print(f"✓ Pacote atualizado: {pkg_data['name']}")
        else:
            # Cria novo pacote
            package = CreditPackage(**pkg_data)
            db.session.add(package)
            created += 1
            print(f"✓ Pacote criado: {pkg_data['name']}")

    db.session.commit()

    print("\n=== Resumo ===")
    print(f"Pacotes criados: {created}")
    print(f"Pacotes atualizados: {updated}")
    print(
        f"Total de pacotes ativos: {CreditPackage.query.filter_by(is_active=True).count()}"
    )


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        print("Configurando pacotes de créditos...\n")
        setup_packages()
        print("\n✅ Configuração concluída!")

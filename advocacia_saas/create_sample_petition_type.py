#!/usr/bin/env python3
"""
Script para criar um tipo de petição de exemplo usando o sistema dinâmico.
Executar após popular seções: python create_sample_petition_type.py
"""

from app import create_app, db
from app.models import PetitionType, PetitionTypeSection, PetitionSection

def create_sample_petition_type():
    """Cria um tipo de petição de exemplo usando seções dinâmicas"""

    app = create_app()
    with app.app_context():
        # Criar tipo de petição
        petition_type = PetitionType(
            name="Ação Cível - Indenizatória",
            slug="acao-civel-indenizatoria",
            description="Modelo para ações indenizatórias cíveis",
            category="civel",
            icon="fa-gavel",
            color="primary",
            is_billable=True,
            base_price=150.00,
            use_dynamic_form=True
        )

        db.session.add(petition_type)
        db.session.commit()

        print(f"✓ Criado tipo de petição: {petition_type.name}")

        # Buscar seções criadas anteriormente
        sections_order = [
            "cabecalho-processo",
            "qualificacao-partes",
            "dos-fatos",
            "do-direito",
            "dos-pedidos",
            "valor-causa",
            "assinatura"
        ]

        order = 1
        for section_slug in sections_order:
            section = PetitionSection.query.filter_by(slug=section_slug).first()
            if section:
                config = PetitionTypeSection(
                    petition_type_id=petition_type.id,
                    section_id=section.id,
                    order=order,
                    is_required=True,
                    is_expanded=True
                )
                db.session.add(config)
                print(f"✓ Adicionada seção: {section.name} (ordem {order})")
                order += 1

        db.session.commit()
        print(f"\n🎉 Tipo de petição '{petition_type.name}' criado com sucesso!")
        print(f"📝 Slug: {petition_type.slug}")
        print(f"🔗 URL: /dynamic/{petition_type.slug}")

if __name__ == "__main__":
    create_sample_petition_type()
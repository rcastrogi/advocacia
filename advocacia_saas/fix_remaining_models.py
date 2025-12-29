"""
Script simplificado para corrigir os modelos restantes
"""

from app import create_app
from app.models import PetitionModel, PetitionModelSection, PetitionSection, db


def get_section_by_slug(slug):
    return PetitionSection.query.filter_by(slug=slug, is_active=True).first()


def clear_and_add_sections(model_id, sections_list):
    """Limpa e adiciona seções a um modelo."""
    # Limpar seções existentes
    PetitionModelSection.query.filter_by(petition_model_id=model_id).delete()
    db.session.commit()

    # Adicionar novas seções
    for i, (slug, required, expanded) in enumerate(sections_list, 1):
        section = get_section_by_slug(slug)
        if section:
            model_section = PetitionModelSection(
                petition_model_id=model_id,
                section_id=section.id,
                order=i,
                is_required=required,
                is_expanded=expanded,
            )
            db.session.add(model_section)
        else:
            print(f"⚠️ Seção '{slug}' não encontrada!")

    db.session.commit()


def main():
    app = create_app()
    with app.app_context():
        print("🔧 Corrigindo modelos restantes...")

        # Modelo 29: Ação de Indenização por Acidente de Trânsito
        print("Corrigindo Modelo 29...")
        sections_29 = [
            ("cabecalho", True, True),
            ("autor", True, True),
            ("reu", True, True),
            ("dados-acidente-transito", True, True),
            ("fatos", True, True),
            ("danos-materiais-morais", True, True),
            ("direito", True, True),
            ("pedidos", True, True),
            ("valor-causa", True, True),
            ("provas", True, True),
            ("assinatura", True, True),
        ]
        clear_and_add_sections(29, sections_29)

        # Modelo 34: Ação de Cobrança de Honorários Advocatícios
        print("Corrigindo Modelo 34...")
        sections_34 = [
            ("cabecalho", True, True),
            ("autor", True, True),
            ("reu", True, True),
            ("fatos", True, True),
            ("honorarios-advocaticios", True, True),
            ("direito", True, True),
            ("pedidos", True, True),
            ("valor-causa", True, True),
            ("provas", True, True),
            ("assinatura", True, True),
        ]
        clear_and_add_sections(34, sections_34)

        # Modelo 35: Petição Personalizada
        print("Corrigindo Modelo 35...")
        sections_35 = [
            ("processo-existente", False, True),
            ("cabecalho", True, True),
            ("autor", False, True),
            ("reu", False, True),
            ("fatos", False, True),
            ("direito", False, True),
            ("pedidos", False, True),
            ("valor-causa", False, True),
            ("assinatura", True, True),
        ]
        clear_and_add_sections(35, sections_35)

        # Modelo 36: Petição Família
        print("Corrigindo Modelo 36...")
        sections_36 = [
            ("processo-existente", False, True),
            ("cabecalho", True, True),
            ("autor", True, True),
            ("reu", True, True),
            ("casamento", False, True),
            ("filhos", False, True),
            ("pensao", False, True),
            ("patrimonio", False, True),
            ("fatos", True, True),
            ("direito", True, True),
            ("pedidos", True, True),
            ("valor-causa", False, True),
            ("assinatura", True, True),
        ]
        clear_and_add_sections(36, sections_36)

        print("✅ Correções concluídas!")


if __name__ == "__main__":
    main()

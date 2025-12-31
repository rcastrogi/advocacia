"""
Script para validar e corrigir seções dos modelos de petições
para deixá-las condizentes com petições jurídicas reais.
"""

from app import create_app
from app.models import PetitionModel, PetitionModelSection, PetitionSection, db


def get_section_by_slug(slug):
    """Busca uma seção pelo slug."""
    return PetitionSection.query.filter_by(slug=slug, is_active=True).first()


def clear_model_sections(model_id):
    """Remove todas as seções de um modelo."""
    PetitionModelSection.query.filter_by(petition_model_id=model_id).delete()
    db.session.commit()


def add_section_to_model(
    model_id, section_slug, order, is_required=False, is_expanded=True
):
    """Adiciona uma seção a um modelo."""
    section = get_section_by_slug(section_slug)
    if not section:
        print(f"⚠️  Seção '{section_slug}' não encontrada!")
        return False

    model_section = PetitionModelSection(
        petition_model_id=model_id,
        section_id=section.id,
        order=order,
        is_required=is_required,
        is_expanded=is_expanded,
    )
    db.session.add(model_section)
    return True


def fix_acao_civel_indenizatoria():
    """Corrige o modelo Ação Cível - Indenizatória (ID: 27)."""
    print("🔧 Corrigindo Modelo - Ação Cível - Indenizatória...")

    model_id = 27
    clear_model_sections(model_id)

    # Ordem correta para ação indenizatória
    sections = [
        ("cabecalho", True, True),  # Cabeçalho obrigatório
        ("autor", True, True),  # Autor obrigatório
        ("reu", True, True),  # Réu obrigatório
        ("fatos", True, True),  # Fatos obrigatórios
        ("direito", True, True),  # Direito obrigatório
        ("pedidos", True, True),  # Pedidos obrigatórios
        ("valor-causa", True, True),  # Valor da causa obrigatório
        ("provas", False, True),  # Provas opcionais
        ("assinatura", True, True),  # Assinatura obrigatória
    ]

    for i, (slug, required, expanded) in enumerate(sections, 1):
        if add_section_to_model(model_id, slug, i, required, expanded):
            print(f"  ✅ Adicionada seção: {slug} (ordem: {i})")

    db.session.commit()
    print("✅ Modelo corrigido!\n")


def fix_acao_divorcio_litigioso():
    """Corrige o modelo Ação de Divórcio Litigioso (ID: 28)."""
    print("🔧 Corrigindo Modelo - Ação de Divórcio Litigioso...")

    model_id = 28
    clear_model_sections(model_id)

    # Ordem correta para ação de divórcio litigioso
    sections = [
        ("cabecalho", True, True),
        ("conjuge1", True, True),  # Requerente
        ("conjuge2", True, True),  # Requerido
        ("casamento", True, True),  # Dados do casamento
        ("filhos", False, True),  # Filhos (se houver)
        ("regime-bens", True, True),  # Regime de bens
        ("patrimonio", True, True),  # Partilha de bens
        ("pensao", False, True),  # Pensão alimentícia
        ("fatos", True, True),  # Fatos
        ("direito", True, True),  # Fundamentação jurídica
        ("pedidos", True, True),  # Pedidos
        ("valor-causa", True, True),  # Valor da causa
        ("provas", False, True),  # Provas
        ("assinatura", True, True),  # Assinatura
    ]

    for i, (slug, required, expanded) in enumerate(sections, 1):
        if add_section_to_model(model_id, slug, i, required, expanded):
            print(f"  ✅ Adicionada seção: {slug} (ordem: {i})")

    db.session.commit()
    print("✅ Modelo corrigido!\n")


def fix_acao_indenizacao_acidente_transito():
    """Corrige o modelo Ação de Indenização por Acidente de Trânsito (ID: 29)."""
    print("🔧 Corrigindo Modelo - Ação de Indenização por Acidente de Trânsito...")

    model_id = 29
    clear_model_sections(model_id)

    # Ordem correta para ação de indenização por acidente de trânsito
    sections = [
        ("cabecalho", True, True),
        ("autor", True, True),  # Vítima/requerente
        ("reu", True, True),  # Responsável/réu
        ("dados-acidente-transito", True, True),  # Dados específicos do acidente
        ("fatos", True, True),  # Fatos do acidente
        ("danos-materiais-morais", True, True),  # Danos materiais e morais
        ("direito", True, True),  # Fundamentação jurídica
        ("pedidos", True, True),  # Pedidos de indenização
        ("valor-causa", True, True),  # Valor da causa
        ("provas", True, True),  # Provas (laudos, testemunhas, etc.)
        ("assinatura", True, True),  # Assinatura
    ]

    for i, (slug, required, expanded) in enumerate(sections, 1):
        if add_section_to_model(model_id, slug, i, required, expanded):
            print(f"  ✅ Adicionada seção: {slug} (ordem: {i})")

    db.session.commit()
    print("✅ Modelo corrigido!\n")


def fix_acao_cobranca_honorarios():
    """Corrige o modelo Ação de Cobrança de Honorários Advocatícios (ID: 34)."""
    print("🔧 Corrigindo Modelo - Ação de Cobrança de Honorários Advocatícios...")

    model_id = 34
    clear_model_sections(model_id)

    # Ordem correta para ação de cobrança de honorários
    sections = [
        ("cabecalho", True, True),
        ("autor", True, True),  # Advogado/requerente
        ("reu", True, True),  # Cliente/réu
        ("fatos", True, True),  # Fatos (contrato, serviços prestados, etc.)
        ("honorarios-advocaticios", True, True),  # Detalhamento dos honorários
        ("direito", True, True),  # Fundamentação jurídica
        ("pedidos", True, True),  # Pedidos
        ("valor-causa", True, True),  # Valor da causa
        ("provas", True, True),  # Provas (contrato, recibos, etc.)
        ("assinatura", True, True),  # Assinatura
    ]

    for i, (slug, required, expanded) in enumerate(sections, 1):
        if add_section_to_model(model_id, slug, i, required, expanded):
            print(f"  ✅ Adicionada seção: {slug} (ordem: {i})")

    db.session.commit()
    print("✅ Modelo corrigido!\n")


def fix_peticao_personalizada():
    """Corrige o modelo Petição Personalizada (ID: 35)."""
    print("🔧 Corrigindo Modelo - Petição Personalizada...")

    model_id = 35
    clear_model_sections(model_id)

    # Para petição personalizada, manter mais flexível
    sections = [
        ("processo-existente", False, True),  # Dados do processo (se existir)
        ("cabecalho", True, True),  # Cabeçalho
        ("autor", False, True),  # Autor (opcional)
        ("reu", False, True),  # Réu (opcional)
        ("fatos", False, True),  # Fatos
        ("direito", False, True),  # Direito
        ("pedidos", False, True),  # Pedidos
        ("valor-causa", False, True),  # Valor da causa
        ("assinatura", True, True),  # Assinatura obrigatória
    ]

    for i, (slug, required, expanded) in enumerate(sections, 1):
        if add_section_to_model(model_id, slug, i, required, expanded):
            print(f"  ✅ Adicionada seção: {slug} (ordem: {i})")

    db.session.commit()
    print("✅ Modelo corrigido!\n")


def fix_peticao_familia():
    """Corrige o modelo Petição Família (ID: 36)."""
    print("🔧 Corrigindo Modelo - Petição Família...")

    model_id = 36
    clear_model_sections(model_id)

    # Para petição família, incluir seções comuns a processos familiares
    sections = [
        ("processo-existente", False, True),  # Dados do processo
        ("cabecalho", True, True),  # Cabeçalho
        ("autor", True, True),  # Requerente
        ("reu", True, True),  # Requerido
        ("casamento", False, True),  # Dados do casamento
        ("filhos", False, True),  # Filhos
        ("pensao", False, True),  # Pensão alimentícia
        ("patrimonio", False, True),  # Patrimônio
        ("fatos", True, True),  # Fatos
        ("direito", True, True),  # Direito
        ("pedidos", True, True),  # Pedidos
        ("valor-causa", False, True),  # Valor da causa
        ("assinatura", True, True),  # Assinatura
    ]

    for i, (slug, required, expanded) in enumerate(sections, 1):
        if add_section_to_model(model_id, slug, i, required, expanded):
            print(f"  ✅ Adicionada seção: {slug} (ordem: {i})")

    db.session.commit()
    print("✅ Modelo corrigido!\n")


def main():
    """Função principal para executar todas as correções."""
    app = create_app()
    with app.app_context():
        print("🚀 Iniciando validação e correção dos modelos de petições...\n")

        # Executar correções
        fix_acao_civel_indenizatoria()
        fix_acao_divorcio_litigioso()
        fix_acao_indenizacao_acidente_transito()
        fix_acao_cobranca_honorarios()
        fix_peticao_personalizada()
        fix_peticao_familia()

        print("🎉 Validação e correção concluídas!")
        print(
            "Verifique os modelos corrigidos executando o script de verificação novamente."
        )


if __name__ == "__main__":
    main()

"""
Script ultra-simplificado - faz tudo em um único commit.
"""
from app import create_app, db
from app.models import PetitionType, PetitionSection, PetitionTypeSection

app = create_app()

# Mapeamento simplificado
PETITION_TYPE_SECTIONS = {
    "peticao-inicial-civel": ["cabecalho", "autor", "reu", "fatos", "direito", "pedidos", "valor-causa", "provas", "justica-gratuita", "assinatura"],
    "acao-de-cobranca": ["cabecalho", "autor", "reu", "fatos", "direito", "pedidos", "valor-causa", "provas", "justica-gratuita", "assinatura"],
    "acao-de-alimentos": ["cabecalho", "autor", "reu", "pensao", "fatos", "direito", "pedidos", "valor-causa", "justica-gratuita", "assinatura"],
    "guarda-e-regulacao-de-visitas": ["cabecalho", "autor", "reu", "filhos", "fatos", "direito", "pedidos", "valor-causa", "justica-gratuita", "assinatura"],
    "divorcio-litigioso": ["cabecalho", "conjuge1", "conjuge2", "casamento", "filhos", "pensao", "patrimonio", "dividas", "nome", "fatos", "direito", "pedidos", "valor-causa", "provas", "justica-gratuita", "assinatura"],
    "divorcio-consensual": ["cabecalho", "conjuge1", "conjuge2", "casamento", "filhos", "pensao", "patrimonio", "nome", "fatos", "direito", "pedidos", "assinatura"],
    "peticao-juntada-mle": ["processo-existente", "mle", "assinatura"],
    "peticao-simples-penhora-inss": ["processo-existente", "penhora-inss", "assinatura"],
    "contestacao-civel": ["cabecalho", "processo-existente", "autor", "reu", "fatos", "direito", "pedidos", "provas", "justica-gratuita", "assinatura"],
    "mandado-de-seguranca": ["cabecalho", "autor", "reu", "fatos", "direito", "pedidos", "provas", "assinatura"],
    "reclamacao-trabalhista": ["cabecalho", "autor", "reu", "fatos", "direito", "pedidos", "valor-causa", "justica-gratuita", "assinatura"],
    "defesa-trabalhista": ["cabecalho", "processo-existente", "autor", "reu", "fatos", "direito", "pedidos", "provas", "assinatura"],
    "pedido-de-habeas-corpus": ["cabecalho", "autor", "fatos", "direito", "pedidos", "assinatura"],
    "defesa-criminal": ["cabecalho", "processo-existente", "autor", "fatos", "direito", "pedidos", "provas", "assinatura"],
    "execucao-fiscal": ["cabecalho", "processo-existente", "autor", "fatos", "direito", "pedidos", "valor-causa", "assinatura"],
}

with app.app_context():
    print("Buscando dados...")
    
    # Buscar todos os dados primeiro
    all_sections = PetitionSection.query.all()
    section_map = {s.slug: s.id for s in all_sections}
    
    all_types = PetitionType.query.all()
    type_map = {t.slug: t for t in all_types}
    
    print(f"Seções: {len(section_map)}, Tipos: {len(type_map)}")
    
    # Limpar vínculos antigos
    print("Limpando vínculos...")
    PetitionTypeSection.query.delete()
    
    # Criar todos os vínculos
    print("Criando vínculos...")
    links_to_add = []
    
    for type_slug, section_slugs in PETITION_TYPE_SECTIONS.items():
        petition_type = type_map.get(type_slug)
        if not petition_type:
            print(f"  Tipo nao encontrado: {type_slug}")
            continue
        
        petition_type.use_dynamic_form = True
        
        for order, section_slug in enumerate(section_slugs):
            section_id = section_map.get(section_slug)
            if not section_id:
                continue
            
            link = PetitionTypeSection(
                petition_type_id=petition_type.id,
                section_id=section_id,
                order=order,
                is_required=(section_slug in ["fatos", "direito", "pedidos"]),
                is_expanded=True,
                field_overrides={},
            )
            links_to_add.append(link)
        
        print(f"  + {petition_type.name}")
    
    # Adicionar todos os links
    for link in links_to_add:
        db.session.add(link)
    
    # Um único commit
    print(f"\nSalvando {len(links_to_add)} vínculos...")
    db.session.commit()
    print("CONCLUÍDO!")

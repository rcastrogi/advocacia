"""
Script simplificado para vincular seções aos tipos de petição.
"""
from app import create_app, db
from app.models import PetitionType, PetitionSection, PetitionTypeSection
import time

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
    print("=" * 60)
    print("🔗 VINCULANDO SEÇÕES AOS TIPOS DE PETIÇÃO")
    print("=" * 60)
    
    # Buscar seções
    all_sections = PetitionSection.query.all()
    section_map = {s.slug: s.id for s in all_sections}
    print(f"\n📦 {len(section_map)} seções encontradas")
    
    # Limpar vínculos antigos
    print("\n🧹 Limpando vínculos antigos...")
    PetitionTypeSection.query.delete()
    db.session.commit()
    print("   Vínculos removidos!")
    time.sleep(0.5)
    
    configured = 0
    
    for type_slug, section_slugs in PETITION_TYPE_SECTIONS.items():
        try:
            petition_type = PetitionType.query.filter_by(slug=type_slug).first()
            if not petition_type:
                print(f"  ⚠️ Tipo não encontrado: {type_slug}")
                continue
            
            # Ativar formulário dinâmico
            petition_type.use_dynamic_form = True
            db.session.commit()
            time.sleep(0.2)
            
            # Criar vínculos
            for order, section_slug in enumerate(section_slugs):
                section_id = section_map.get(section_slug)
                if not section_id:
                    print(f"    ⚠️ Seção não encontrada: {section_slug}")
                    continue
                
                link = PetitionTypeSection(
                    petition_type_id=petition_type.id,
                    section_id=section_id,
                    order=order,
                    is_required=(section_slug in ["fatos", "direito", "pedidos"]),
                    is_expanded=True,
                    field_overrides={},
                )
                db.session.add(link)
            
            db.session.commit()
            print(f"  ✓ {petition_type.name}: {len(section_slugs)} seções")
            configured += 1
            time.sleep(0.3)
            
        except Exception as e:
            print(f"  ❌ Erro em {type_slug}: {str(e)}")
            db.session.rollback()
            continue
    
    print("\n" + "=" * 60)
    print(f"✅ {configured} tipos configurados!")
    print("=" * 60)

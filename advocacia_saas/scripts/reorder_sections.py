"""
Script para reordenar seções do formulário dinâmico.
Coloca o Representante Legal do Autor logo após o Autor,
e o Representante Legal do Réu logo após o Réu.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import PetitionSection


def reorder_sections():
    """Reordena as seções para melhor organização"""
    
    # Nova ordem das seções (slug -> order)
    # Seções mantidas agrupadas logicamente
    new_order = {
        # Cabeçalho
        "cabecalho": 1,
        "processo-existente": 2,
        
        # Partes - Autor e seu representante legal
        "autor": 10,
        "autor-peticionario": 10,
        "representante-autor": 11,
        
        # Partes - Réu e seu representante legal
        "reu": 20,
        "reu-acusado": 20,
        "representante-reu": 21,
        
        # Cônjuges (divórcio)
        "conjuge1": 30,
        "conjuge2": 31,
        
        # Outras partes
        "terceiro-interessado": 40,
        "representante-terceiro": 41,
        "testemunha": 42,
        
        # Representante Legal genérico (caso exista)
        "representante-legal": 45,
        
        # Dados específicos do caso
        "casamento": 50,
        "filhos": 51,
        "pensao": 52,
        "patrimonio": 53,
        "dividas": 54,
        "nome": 55,
        "regime-bens": 56,
        "pedido-alimentos": 57,
        
        # Dados do processo/fatos
        "dados-processo": 60,
        "dados-imovel": 61,
        "dados-contratuais": 62,
        "dados-trabalhistas": 63,
        "dados-familiares": 64,
        "dados-criminais": 65,
        "dados-previdenciarios": 66,
        "dados-tributarios": 67,
        "dados-ambientais": 68,
        "dados-consumeristas": 69,
        "dados-consumo": 70,
        "dados-acidente-transito": 71,
        "dados-contrato-trabalho": 72,
        
        # Fundamentos
        "fatos": 80,
        "direito": 81,
        "fundamentacao": 82,
        "fundamentacao-juridica": 83,
        "da-cobranca": 84,
        "danos-materiais-morais": 85,
        "reclamacao-trabalhista": 86,
        
        # Pedidos e provas
        "pedidos": 90,
        "pedido-urgencia": 91,
        "provas": 92,
        "documentos-provas": 93,
        "documentos-apresentados": 94,
        "penhora-inss": 95,
        "mle": 96,
        "juntada": 97,
        
        # Valores e custas
        "valor-causa": 100,
        "justica-gratuita": 101,
        "honorarios-advocaticios": 102,
        "custas-processuais": 103,
        
        # Fechamento
        "assinatura": 200,
        
        # Teste (manter no final)
        "secao-visual-teste": 9999,
    }
    
    app = create_app()
    with app.app_context():
        sections = PetitionSection.query.all()
        updated = 0
        
        for section in sections:
            if section.slug in new_order:
                old_order = section.order
                new = new_order[section.slug]
                if old_order != new:
                    section.order = new
                    print(f"✅ {section.slug}: {old_order} → {new}")
                    updated += 1
            else:
                print(f"⚠️  {section.slug} não está no mapeamento (order atual: {section.order})")
        
        if updated > 0:
            db.session.commit()
            print(f"\n✅ {updated} seções reordenadas com sucesso!")
        else:
            print("\n✅ Todas as seções já estão na ordem correta.")
        
        # Mostrar resultado final
        print("\n📋 Nova ordem das seções:")
        sections = PetitionSection.query.order_by(PetitionSection.order).all()
        for s in sections:
            print(f"  {s.order:4d}: {s.slug} - {s.name}")


if __name__ == "__main__":
    reorder_sections()

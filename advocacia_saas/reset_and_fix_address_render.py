#!/usr/bin/env python3
"""
Script para limpar e refazer os campos de endereço no Render PostgreSQL
Este script remove os campos que foram adicionados incorretamente e refaz do zero
"""

import json
import psycopg2
from psycopg2.extras import RealDictCursor

def reset_and_fix_address_fields():
    """Reseta e corrige campos de endereço no Render"""
    
    try:
        database_url = "postgresql://petitio_db_user:krGWlyjOxEJKLwgoNHBZjOzaMV1T0JZf@dpg-d54kpj6r433s73d37900-a.oregon-postgres.render.com/petitio_db"
        
        print("🔗 Conectando ao Render PostgreSQL...\n")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("✅ Conectado!\n")
        
        # Lista de seções a corrigir
        sections_to_fix = [
            (33, "autor-peticionario", "Autor/Peticionário"),
            (34, "reu-acusado", "Réu/Acusado"),
            (35, "testemunha", "Testemunha"),
            (36, "terceiro-interessado", "Terceiro Interessado"),
            (37, "representante-legal", "Representante Legal"),
        ]
        
        total_fixed = 0
        
        for section_id, slug, name in sections_to_fix:
            print(f"🔧 RESET Seção {section_id}: {name} ({slug})")
            
            # Buscar seção atual
            cursor.execute("SELECT id, fields_schema FROM petition_sections WHERE id = %s", (section_id,))
            result = cursor.fetchone()
            
            if not result:
                print(f"❌ Seção não encontrada\n")
                continue
            
            fields_schema = result['fields_schema'] or []
            
            # Limpar campos antigos de endereço e deixar apenas cep, estado, cidade
            new_schema = []
            for field in fields_schema:
                field_name = field.get('name', '').lower()
                # Manter apenas campos que NÃO são de endereço (exceto cep, estado, cidade)
                if field_name not in ['endereco', 'logradouro', 'numero', 'bairro', 'complemento', 'numero', 'bairro']:
                    new_schema.append(field)
            
            # Encontrar posição para inserir (após cep, ou no final)
            cep_index = None
            for i, field in enumerate(new_schema):
                if field.get('name') == 'cep':
                    cep_index = i
                    break
            
            if cep_index is None:
                cep_index = len(new_schema) - 1
            
            # Preparar campos corretos de endereço
            correct_fields = [
                {
                    "name": "numero",
                    "label": "Número",
                    "type": "text",
                    "required": False,
                    "size": "col-md-2",
                    "placeholder": "Ex: 123"
                },
                {
                    "name": "bairro",
                    "label": "Bairro",
                    "type": "text",
                    "required": False,
                    "size": "col-md-3",
                    "placeholder": "Ex: Centro"
                },
                {
                    "name": "complemento",
                    "label": "Complemento",
                    "type": "text",
                    "required": False,
                    "size": "col-md-4",
                    "placeholder": "Ex: Apto 101"
                }
            ]
            
            # Inserir campos corretos após CEP
            for i, field in enumerate(correct_fields):
                new_schema.insert(cep_index + 1 + i, field)
            
            # Atualizar banco
            cursor.execute(
                "UPDATE petition_sections SET fields_schema = %s WHERE id = %s",
                (json.dumps(new_schema), section_id)
            )
            conn.commit()
            
            print(f"   ✅ Removidos campos duplicados/incorretos")
            print(f"   ✅ Adicionados 3 campos corretos:")
            print(f"      - numero: Número")
            print(f"      - bairro: Bairro")
            print(f"      - complemento: Complemento\n")
            
            total_fixed += 1
        
        print(f"\n✨ Reset e correção completa!")
        print(f"   📊 Seções corrigidas: {total_fixed}")
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Erro de banco de dados: {str(e)}")
        conn.rollback()
        return False
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import sys
    success = reset_and_fix_address_fields()
    sys.exit(0 if success else 1)

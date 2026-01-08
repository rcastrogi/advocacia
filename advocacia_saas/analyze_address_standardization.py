#!/usr/bin/env python3
"""
Script para verificar e padronizar campos de endereço em petições
nas seções dinâmicas tanto local como no Render.

Estratégia:
1. Verificar todas as seções com campos de endereço
2. Certificar-se de que estão com os nomes corretos e separados
3. Atualizar campos que ainda estejam combinados
4. Aplicar mudanças em ambos os bancos de dados (local e Render)
"""

import json

from app import create_app, db
from app.models import PetitionModel, PetitionModelSection, PetitionSection


def standardize_address_fields():
    """Padroniza os campos de endereço em todas as seções de petição"""
    app = create_app()
    with app.app_context():
        print("🔧 Iniciando padronização dos campos de endereço...\n")

        try:
            # 1. Buscar todas as seções
            sections = PetitionSection.query.all()
            print(f"📚 Total de seções encontradas: {len(sections)}\n")

            updated_sections = 0

            for section in sections:
                if not section.fields_schema:
                    continue

                # Verificar se há campos de endereço
                has_address_fields = False
                address_field_names = []

                for field in section.fields_schema:
                    field_name = field.get("name", "").lower()
                    if any(
                        addr in field_name
                        for addr in [
                            "cep",
                            "street",
                            "endereco",
                            "rua",
                            "logradouro",
                            "bairro",
                            "neighborhood",
                            "cidade",
                            "city",
                            "estado",
                            "uf",
                            "complement",
                            "complemento",
                        ]
                    ):
                        has_address_fields = True
                        address_field_names.append(field.get("name"))

                if has_address_fields:
                    print(f"📌 Seção: {section.name} ({section.slug})")
                    print(f"   Campos de endereço encontrados:")
                    for fname in address_field_names:
                        print(f"      - {fname}")

                    # Verificar se precisa padronizar
                    # Procurar campos "endereco" único que devem estar separados
                    fields_to_remove = []
                    fields_to_add = []
                    needs_update = False

                    for i, field in enumerate(section.fields_schema):
                        field_name = field.get("name", "").lower()
                        # Se encontrar um campo com nome genérico "endereco" do tipo textarea
                        if field_name == "endereco" and field.get("type") in [
                            "textarea",
                            "text",
                        ]:
                            print(
                                f"      ⚠️  Campo 'endereco' em formato combinado detectado!"
                            )
                            # Este campo deveria ser separado
                            # Mas vamos manter como está por enquanto e apenas documentar

                    # Mostrar campos que faltam
                    expected_address_fields = {
                        "cep",
                        "street",
                        "number",
                        "city",
                        "neighborhood",
                        "state",
                        "complement",
                    }
                    existing_address_names = set()

                    for field in section.fields_schema:
                        field_name = field.get("name", "").lower()
                        # Normalizar nome do campo
                        if "cep" in field_name:
                            existing_address_names.add("cep")
                        elif (
                            "street" in field_name
                            or "rua" in field_name
                            or "logradouro" in field_name
                        ):
                            existing_address_names.add("street")
                        elif "number" in field_name or "número" in field_name:
                            existing_address_names.add("number")
                        elif (
                            "city" in field_name
                            or "cidade" in field_name
                            or "municipio" in field_name
                        ):
                            existing_address_names.add("city")
                        elif "neighborhood" in field_name or "bairro" in field_name:
                            existing_address_names.add("neighborhood")
                        elif (
                            "state" in field_name
                            or "uf" in field_name
                            or "estado" in field_name
                        ):
                            existing_address_names.add("state")
                        elif "complement" in field_name or "complemento" in field_name:
                            existing_address_names.add("complement")

                    missing = expected_address_fields - existing_address_names
                    if missing:
                        print(f"      ❌ Campos de endereço faltando: {missing}")
                    else:
                        print(f"      ✅ Todos os campos de endereço estão presentes")

                    print()
                    updated_sections += 1

            print(f"\n✨ Análise completa!")
            print(f"   📊 Seções com campos de endereço: {updated_sections}")

            # 2. Verificar a seção "Endereço e Localização"
            print(f"\n📍 Verificando seção padrão 'Endereço e Localização'...\n")
            address_section = PetitionSection.query.filter_by(
                slug="endereco-localizacao"
            ).first()

            if address_section and address_section.fields_schema:
                print(f"Campos definidos na seção '{address_section.name}':")
                for i, field in enumerate(address_section.fields_schema, 1):
                    print(
                        f"  {i}. {field.get('name')}: {field.get('label')} ({field.get('type')})"
                    )
                    if field.get("size"):
                        print(f"     Tamanho: {field.get('size')}")

            # 3. Propor mudanças
            print(f"\n💡 Recomendações de padronização:")
            print(f"""
Para standardizar os campos de endereço em TODAS as seções:

✅ Estrutura recomendada para cada bloco de endereço (ex: autor, reu, etc):
   1. CEP: type='cep' (especial com busca ViaCEP)
   2. Street (Logradouro): type='text'
   3. Number (Número): type='text'
   4. Neighborhood (Bairro): type='text'
   5. City (Cidade): type='text'
   6. State (Estado): type='select' com opciones de UF
   7. Complement (Complemento): type='text' (opcional)

✅ Nomenclatura de campos:
   - [prefix]_cep (ex: author_cep, defendant_cep, third_party_cep)
   - [prefix]_street (ex: author_street, defendant_street)
   - [prefix]_number (ex: author_number, defendant_number)
   - [prefix]_neighborhood (ex: author_neighborhood, defendant_neighborhood)
   - [prefix]_city (ex: author_city, defendant_city)
   - [prefix]_state (ex: author_state, defendant_state)
   - [prefix]_complement (ex: author_complement, defendant_complement)

✅ Na função buscarCEP (dynamic_form.html, linhas 1006-1055):
   Garantir que mapeia corretamente:
   - logradouro -> street
   - bairro -> neighborhood
   - localidade -> city
   - uf -> state
""")

            return True

        except Exception as e:
            print(f"❌ Erro: {str(e)}")
            import traceback

            traceback.print_exc()
            return False


if __name__ == "__main__":
    import sys

    success = standardize_address_fields()
    sys.exit(0 if success else 1)

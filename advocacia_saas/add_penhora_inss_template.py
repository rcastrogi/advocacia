#!/usr/bin/env python
"""
Script para adicionar o template de Petição de Penhora de Benefício INSS.
"""

import json
import sys

sys.path.insert(0, ".")

from app import create_app, db
from app.models import PetitionTemplate, PetitionType

app = create_app()

# Conteúdo do template Jinja2 para Penhora de Benefício INSS
TEMPLATE_CONTENT = """
<div class="petition-header">
    <p class="text-center fw-bold">
        EXCELENTÍSSIMO SENHOR DOUTOR JUIZ DE DIREITO DA {{ vara|default('___ VARA DO JUIZADO ESPECIAL CÍVEL', true) }}{% if forum %} DO {{ forum|upper }}{% endif %}
    </p>
</div>

<div class="petition-info mt-5">
    <p class="fw-bold">{{ action_type|default('AÇÃO DE EXECUÇÃO', true)|upper }}</p>
    <p><strong>Processo nº</strong> {{ process_number }}</p>
</div>

<div class="petition-body mt-4">
    <p class="text-justify" style="text-indent: 2em;">
        <strong>{{ author_name|upper }}</strong>, já devidamente qualificado nos autos da ação em epígrafe, que move em face de <strong>{{ defendant_name|upper }}</strong>, igualmente qualificado, vem por seu advogado, em atenção à resposta do INSS, que constatou o recebimento pelo EXECUTADO de benefício ativo no montante de R$ {{ valor_beneficio_inss }} ({{ valor_beneficio_extenso }}), vem à presença de Vossa Excelência requerer a <strong>penhora de {{ percentual_penhora|default('30%', true) }}</strong> deste rendimento, vez que é sabido que o EXECUTADO possui outras formas de rendimento e se oculta para evitar o adimplemento de suas obrigações perante seus credores, lesando a sociedade como um todo.
    </p>
    
    {{ facts|safe }}
    
    <p class="text-justify mt-3" style="text-indent: 2em;">
        Ora, como cidadãos, não podemos aceitar que um indivíduo cause prejuízos, atrapalhando a vida e a rotina daqueles que cumprem corretamente com suas obrigações e saia impune aos olhos do Estado.
    </p>
    
    <p class="text-justify mt-3" style="text-indent: 2em;">
        Deste modo, o desconto de R$ {{ valor_penhora }} ({{ valor_penhora_extenso }}) não configura abuso de direito, por, inclusive, representar quantia aceita em nossa jurisprudência para que os espertinhos que se apresentam como pobres, na acepção do termo, possam reparar os danos causados a terceiros por eles mesmos.
    </p>
    
    {% if tempo_inadimplencia %}
    <p class="text-justify mt-3" style="text-indent: 2em;">
        Ainda, cumpre salientar que o EXECUTADO logrou êxito em ludibriar a justiça, se escondendo de oficiais de justiça e esquivando-se dos atos oficiais por {{ tempo_inadimplencia }}, ou seja, desde a propositura da presente demanda, mais precisamente após a sentença de mérito.
    </p>
    {% endif %}
    
    <p class="text-justify mt-3" style="text-indent: 2em;">
        Portanto, apenas para ratificar, requer o EXEQUENTE a <strong>penhora de {{ percentual_penhora|default('30%', true) }} do benefício</strong> recebido pelo EXECUTADO junto ao INSS, correspondente a R$ {{ valor_penhora }} ({{ valor_penhora_extenso }}) enquanto durar o benefício ou quitar a dívida, o que vier primeiro.
    </p>
    
    <p class="text-justify mt-3" style="text-indent: 2em;">
        O débito atualizado corresponde ao montante de <strong>R$ {{ debito_atualizado }}</strong> ({{ debito_extenso }}){% if qtd_parcelas %}, e seria quitado integralmente em {{ qtd_parcelas }} parcelas se considerarmos juros e atualizações monetárias{% endif %}, portanto, perfeitamente possível adotar a solução apresentada, sendo que o EXECUTADO poderá quitar integralmente sua pendência quando achar necessário.
    </p>
    
    {{ pedidos|safe }}
</div>

<div class="petition-closing mt-5">
    <p class="text-center">Termos em que,</p>
    <p class="text-center">Pede deferimento.</p>
</div>

<div class="petition-signature mt-5">
    <p class="text-center">{{ cidade|default('São Paulo', true) }}, {{ data_assinatura_formatada }}</p>
    
    <div class="text-center mt-5">
        <p class="mb-0"><strong>{{ advogado_nome|upper }}</strong></p>
        <p>{{ advogado_oab }}</p>
    </div>
</div>
"""

# Valores padrão para o formulário
DEFAULT_VALUES = {
    "facts": """<p>Assim, por possuir empresa em seu nome, trabalhar com outras atividades, embora igualmente ocultadas ou registradas em nome de terceiros, e possuir uma condição satisfatória de subsistência, a medida requerida se apresenta como a única maneira de reparar prejuízo causado unicamente pelo EXECUTADO.</p>""",
    "pedidos": """<p>Termos em que,</p>
<p>Pede deferimento.</p>""",
}


def add_penhora_inss_template():
    with app.app_context():
        # Verificar/criar o tipo de petição
        petition_type = PetitionType.query.filter_by(
            slug="peticao-simples-penhora-inss"
        ).first()

        if not petition_type:
            petition_type = PetitionType(
                slug="peticao-simples-penhora-inss",
                name="Petição Simples - Penhora INSS",
                description="Petições de penhora de benefício previdenciário (INSS)",
                category="execucao",
                is_implemented=True,
            )
            db.session.add(petition_type)
            db.session.commit()
            print(
                f"✓ Criado PetitionType: {petition_type.name} (ID: {petition_type.id})"
            )
        else:
            print(
                f"• PetitionType já existe: {petition_type.name} (ID: {petition_type.id})"
            )

        # Verificar se o template já existe
        existing = PetitionTemplate.query.filter_by(
            slug="penhora-beneficio-inss"
        ).first()

        if existing:
            print(f"• Template já existe: {existing.name} (ID: {existing.id})")
            # Atualizar conteúdo
            existing.content = TEMPLATE_CONTENT.strip()
            existing.default_values = json.dumps(DEFAULT_VALUES)
            db.session.commit()
            print(f"✓ Template atualizado!")
            return

        # Criar o template
        template = PetitionTemplate(
            slug="penhora-beneficio-inss",
            name="Penhora de Benefício INSS",
            description="Petição requerendo penhora de percentual do benefício previdenciário do executado junto ao INSS",
            petition_type_id=petition_type.id,
            content=TEMPLATE_CONTENT.strip(),
            category="execucao",
            default_values=json.dumps(DEFAULT_VALUES),
            is_active=True,
        )

        db.session.add(template)
        db.session.commit()

        print(f"✓ Criado PetitionTemplate: {template.name} (ID: {template.id})")
        print(f"✓ Modelo de Penhora de Benefício INSS adicionado com sucesso!")


if __name__ == "__main__":
    add_penhora_inss_template()

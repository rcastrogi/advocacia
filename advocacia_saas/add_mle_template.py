"""
Script para adicionar o modelo de Petição de Juntada de MLE (Mandado de Levantamento Eletrônico).
"""

import json
from decimal import Decimal

from app import create_app, db
from app.models import PetitionTemplate, PetitionType

app = create_app()

# Template de Petição de Juntada de MLE
MLE_TEMPLATE_CONTENT = """
<div class="header">
<p class="header-forum">{{ forum | upper }}</p>
<p class="header-vara">{{ vara }}</p>
</div>

<p style="text-indent: 0;">Processo nº: {{ process_number }}</p>

<p style="text-indent: 0; margin-top: 24pt;"><strong>{{ author_name | upper }}</strong>, já devidamente qualificado nos autos da ação em epígrafe, que move <strong>{{ action_type | upper }}</strong> em face de <strong>{{ defendant_name | upper }}</strong>, igualmente qualificado, vem à presença de Vossa Excelência, requerer:</p>

<h1>JUNTADA DE MLE - MANDADO DE LEVANTAMENTO ELETRÔNICO</h1>

{{ facts }}

<p style="margin-top: 18pt;">Requer a juntada do MLE anexo{% if folhas_referencia %}, referente às quantias informadas nas folhas {{ folhas_referencia }}{% endif %}, totalizando a quantia de <strong>R$ {{ valor_levantamento }}</strong> ({{ valor_extenso }}), a ser creditado através de:</p>

<div style="margin: 18pt 0; padding: 12pt; border: 1px solid #ccc; background-color: #f9f9f9;">
{% if pix_chave %}
<p style="text-indent: 0; margin: 6pt 0;"><strong>PIX:</strong> {{ pix_chave }}</p>
{% endif %}
{% if banco_dados %}
<p style="text-indent: 0; margin: 6pt 0;"><strong>Dados Bancários:</strong> {{ banco_dados }}</p>
{% endif %}
<p style="text-indent: 0; margin: 6pt 0;"><strong>Titular:</strong> {{ titular_conta }}</p>
{% if procuracao_folha %}
<p style="text-indent: 0; margin: 6pt 0;"><strong>Procuração:</strong> fl. {{ procuracao_folha }}</p>
{% endif %}
</div>

{% if pedidos %}
<h2>DOS PEDIDOS</h2>
{{ pedidos }}
{% endif %}

<p style="text-indent: 0; margin-top: 24pt;">Termos em que,<br>Pede Deferimento.</p>

<div class="signature-block">
<p class="signature-city-date">{{ cidade }}, {{ data_assinatura }}</p>
<div class="signature-line">
<p class="signature-name">{{ advogado_nome | upper }}</p>
<p class="signature-oab">{{ advogado_oab }}</p>
</div>
</div>
"""

# Valores padrão para o template
MLE_DEFAULT_VALUES = {
    "facts": "<p>Conforme decisão proferida nos autos, foi determinado o levantamento dos valores depositados em favor da parte autora.</p>",
    "pedidos": "<p>a) A juntada do Mandado de Levantamento Eletrônico (MLE) anexo;</p><p>b) A expedição de ordem de pagamento/transferência para a conta indicada;</p><p>c) A certificação do cumprimento nos autos.</p>",
}


def add_mle_template():
    with app.app_context():
        # Verificar se o tipo de petição já existe
        petition_type = PetitionType.query.filter_by(slug="peticao-juntada-mle").first()
        if not petition_type:
            petition_type = PetitionType(
                slug="peticao-juntada-mle",
                name="Petição Simples - Juntada de MLE",
                category="civel",
                is_billable=True,
                base_price=Decimal("5.00"),  # Preço menor por ser petição simples
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
        template = PetitionTemplate.query.filter_by(slug="modelo-juntada-mle").first()
        if not template:
            template = PetitionTemplate(
                slug="modelo-juntada-mle",
                name="Juntada de MLE (Levantamento de Valores)",
                description="Petição simples para requerer juntada de Mandado de Levantamento Eletrônico e indicar dados bancários para crédito de valores.",
                category="civel",
                content=MLE_TEMPLATE_CONTENT.strip(),
                default_values=json.dumps(MLE_DEFAULT_VALUES, ensure_ascii=False),
                is_global=True,
                petition_type_id=petition_type.id,
            )
            db.session.add(template)
            db.session.commit()
            print(f"✓ Criado PetitionTemplate: {template.name} (ID: {template.id})")
        else:
            # Atualizar template existente
            template.content = MLE_TEMPLATE_CONTENT.strip()
            template.default_values = json.dumps(MLE_DEFAULT_VALUES, ensure_ascii=False)
            db.session.commit()
            print(f"✓ Atualizado PetitionTemplate: {template.name} (ID: {template.id})")

        print("\n✓ Modelo de Juntada de MLE adicionado com sucesso!")
        print("\nCampos do template:")
        print("  - forum: Fórum/Tribunal")
        print("  - vara: Vara")
        print("  - process_number: Número do processo")
        print("  - author_name: Nome do autor")
        print("  - action_type: Tipo da ação original")
        print("  - defendant_name: Nome do réu")
        print("  - valor_levantamento: Valor a ser levantado")
        print("  - valor_extenso: Valor por extenso")
        print("  - folhas_referencia: Folhas de referência (opcional)")
        print("  - pix_chave: Chave PIX (opcional)")
        print("  - banco_dados: Dados bancários (opcional)")
        print("  - titular_conta: Nome do titular da conta")
        print("  - procuracao_folha: Folha da procuração (opcional)")


if __name__ == "__main__":
    add_mle_template()

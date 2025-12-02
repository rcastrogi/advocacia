"""
Script para atualizar os templates de petição no banco de dados
com formatação HTML profissional para geração de PDF.
"""

from app import create_app, db
from app.models import PetitionTemplate, PetitionType

app = create_app()

# Template de Divórcio Litigioso com HTML profissional
DIVORCIO_LITIGIOSO_CONTENT = """
<div class="header">
<p class="header-forum">{{ forum | upper }}</p>
<p class="header-vara">{{ vara }}</p>
</div>

<p style="text-indent: 0;">Processo nº: {{ process_number or 'a atribuir' }}</p>

<p class="party-name" style="text-indent: 0; margin-top: 24pt;">{{ spouse_one_name | upper }}</p>
<p class="party-qualification" style="text-indent: 0;">{{ spouse_one_qualification }}{% if author_cpf %}, CPF nº {{ author_cpf }}{% endif %}{% if author_address %}, residente e domiciliado(a) em {{ author_address }}{% endif %}</p>

<p style="text-indent: 0; margin-top: 18pt;">vem, respeitosamente, à presença de Vossa Excelência, por seu advogado ao final assinado, com fundamento nos artigos 1.571 e seguintes do Código Civil, na Lei nº 6.515/77 (Lei do Divórcio), na Lei Maria da Penha (Lei nº 11.340/06) e demais disposições aplicáveis, propor a presente</p>

<h1>AÇÃO DE DIVÓRCIO C/C REGULAMENTAÇÃO DE GUARDA, ALIMENTOS E PARTILHA DE BENS</h1>

<p style="text-indent: 0;">em face de <strong>{{ spouse_two_name | upper }}</strong>, {{ spouse_two_qualification }}{% if defendant_address %}, residente e domiciliado(a) em {{ defendant_address }}{% endif %}, pelos fatos e fundamentos a seguir expostos:</p>

<h2>I - DO CASAMENTO</h2>

<p>As partes contraíram matrimônio em <strong>{{ marriage_city or '[cidade]' }}</strong>{% if marriage_date %}, no dia <strong>{{ marriage_date }}</strong>{% endif %}, sob o regime de <strong>{{ marriage_regime or 'comunhão parcial de bens' }}</strong>{% if prenup_summary %}, conforme pacto antenupcial: {{ prenup_summary }}{% endif %}.</p>

{% if separation_date %}
<p>O casal encontra-se separado de fato desde <strong>{{ separation_date }}</strong>.</p>
{% endif %}

<h2>II - DOS FATOS</h2>
{{ facts }}

{% if has_domestic_violence %}
<h2>III - DA VIOLÊNCIA DOMÉSTICA</h2>
<p>{{ domestic_violence_facts }}</p>
{% if has_protective_order %}
<p><strong>Medida Protetiva:</strong> {{ protective_order_details }}</p>
{% endif %}
{% if moral_damages_amount %}
<p>Requer-se, ainda, a condenação do réu ao pagamento de danos morais no valor de <strong>R$ {{ '%.2f' | format(moral_damages_amount) }}</strong>, em razão das agressões sofridas.</p>
{% endif %}
{% endif %}

<h2>{% if has_domestic_violence %}IV{% else %}III{% endif %} - DOS FILHOS E DA GUARDA</h2>

<p>{{ children_info or 'Não há filhos menores ou incapazes.' }}</p>

{% if children_names %}
<p><strong>Filhos do casal:</strong> {{ children_names }}</p>
{% endif %}

<p><strong>Proposta de guarda e convivência:</strong> {{ custody_plan or 'Requer-se a guarda unilateral dos menores em favor da Autora, com direito de visitas regulamentado ao Réu.' }}</p>

<h2>{% if has_domestic_violence %}V{% else %}IV{% endif %} - DOS ALIMENTOS</h2>

<p>{{ alimony_plan or 'Requer-se a fixação de alimentos em favor dos filhos menores.' }}</p>

{% if defendant_income %}
<p>O Réu aufere renda mensal de aproximadamente <strong>R$ {{ '%.2f' | format(defendant_income) }}</strong>.</p>
{% endif %}

{% if alimony_amount %}
<p>Pleiteia-se a fixação de pensão alimentícia no valor de <strong>R$ {{ '%.2f' | format(alimony_amount) }}</strong> mensais, correspondentes a aproximadamente {% if defendant_income %}{{ '%.0f' | format((alimony_amount / defendant_income) * 100) }}%{% else %}30%{% endif %} dos rendimentos do alimentante.</p>
{% endif %}

{% if health_plan_details %}
<p><strong>Plano de Saúde:</strong> {{ health_plan_details }}</p>
{% endif %}

<h2>{% if has_domestic_violence %}VI{% else %}V{% endif %} - DO PATRIMÔNIO E PARTILHA DE BENS</h2>

<p>{{ property_description or 'Os bens adquiridos na constância do casamento serão objeto de partilha oportuna.' }}</p>

{% if debts_description %}
<p><strong>Dívidas do casal:</strong> {{ debts_description }}</p>
{% endif %}

<h2>{% if has_domestic_violence %}VII{% else %}VI{% endif %} - DO DIREITO</h2>
{{ fundamentos }}

<h2>{% if has_domestic_violence %}VIII{% else %}VII{% endif %} - DOS PEDIDOS</h2>

<p style="text-indent: 0;">Ante o exposto, requer a Vossa Excelência:</p>

{{ pedidos }}

{% if name_change %}
<p>l) A averbação da alteração do nome da Autora para seu nome de solteira.</p>
{% endif %}

{% if request_free_justice %}
<p style="margin-top: 18pt;"><strong>DA JUSTIÇA GRATUITA:</strong> Requer a concessão dos benefícios da Justiça Gratuita, nos termos do art. 98 do CPC, uma vez que a parte autora não possui condições de arcar com as custas processuais sem prejuízo de seu sustento.</p>
{% endif %}

<h2>{% if has_domestic_violence %}IX{% else %}VIII{% endif %} - DO VALOR DA CAUSA</h2>

<p class="valor-causa">Dá-se à causa o valor de <strong>R$ {% if valor_causa %}{{ '%.2f' | format(valor_causa) }}{% else %}1.000,00{% endif %}</strong> para efeitos fiscais.</p>

<p style="text-indent: 0; margin-top: 18pt;">Nestes termos,<br>Pede deferimento.</p>

<div class="signature-block">
<p class="signature-city-date">{{ cidade }}, {{ data_assinatura }}</p>

{% if signature_author %}
<div class="signature-line" style="margin-bottom: 36pt;">
<p class="signature-name">{{ spouse_one_name | upper }}</p>
<p class="signature-oab">Autora</p>
</div>
{% endif %}

<div class="signature-line">
<p class="signature-name">{{ advogado_nome }}</p>
<p class="signature-oab">OAB {{ advogado_oab }}</p>
{% if lawyer_address %}<p style="font-size: 10pt;">{{ lawyer_address }}</p>{% endif %}
</div>
</div>
"""


def update_templates():
    with app.app_context():
        # Buscar ou criar o tipo de petição para divórcio litigioso
        petition_type = PetitionType.query.filter_by(slug="divorcio-litigioso").first()
        if not petition_type:
            petition_type = PetitionType(
                slug="divorcio-litigioso",
                name="Divórcio Litigioso c/c Guarda e Alimentos",
                category="familia",
                is_billable=True,
                base_price=20.00,
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

        # Buscar ou criar o template de divórcio litigioso
        template = PetitionTemplate.query.filter_by(slug="divorcio-litigioso").first()
        if not template:
            template = PetitionTemplate(
                slug="divorcio-litigioso",
                name="Divórcio Litigioso c/c Guarda e Alimentos",
                description="Modelo completo de divórcio litigioso com pedido de guarda, alimentos e partilha de bens. Inclui seções para violência doméstica, medidas protetivas e danos morais.",
                category="familia",
                content=DIVORCIO_LITIGIOSO_CONTENT.strip(),
                is_global=True,
                petition_type_id=petition_type.id,
            )
            db.session.add(template)
            db.session.commit()
            print(f"✓ Criado PetitionTemplate: {template.name} (ID: {template.id})")
        else:
            # Atualizar o conteúdo do template existente
            template.content = DIVORCIO_LITIGIOSO_CONTENT.strip()
            db.session.commit()
            print(f"✓ Atualizado PetitionTemplate: {template.name} (ID: {template.id})")

        # Atualizar os templates existentes com formatação HTML
        existing_templates = PetitionTemplate.query.filter(
            PetitionTemplate.slug.in_(
                [
                    "modelo-padrao-peticao-inicial",
                    "modelo-padrao-contestacao",
                    "modelo-familia-divorcio",
                ]
            )
        ).all()

        for tpl in existing_templates:
            print(f"• Template existente: {tpl.name} (slug: {tpl.slug})")
            # Os templates serão recriados na próxima vez que ensure_default_templates() for chamado
            # após a atualização do código

        print("\n✓ Templates atualizados com sucesso!")
        print(
            "\nNota: Reinicie o servidor Flask para que as alterações nos templates padrão tenham efeito."
        )


if __name__ == "__main__":
    update_templates()

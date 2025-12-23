#!/usr/bin/env python3
"""
Script para criar templates específicos para os tipos de petição criados.
"""

import json
import os
import sys

# Adicionar o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar a configuração da aplicação
from app import db
from app.models import PetitionType, PetitionTypeSection, PetitionSection, PetitionTemplate

# Configurar Flask app para scripts
from flask import Flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/advocacia_saas')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar SQLAlchemy com a app
db.init_app(app)

def create_templates():
    """Cria templates específicos para os tipos de petição"""

    with app.app_context():
        templates_data = [
            {
                "petition_slug": "acao-de-alimentos",
                "template_name": "Modelo Padrão - Ação de Alimentos",
                "template_slug": "modelo-padrao-acao-alimentos",
                "content": """
<div class="header">
<p class="header-forum">{{ foro | upper }}</p>
<p class="header-vara">{{ vara }}</p>
</div>

<p style="text-indent: 0;">Processo nº: {{ processo_numero or 'a ser definido' }}</p>

<p class="party-name" style="text-indent: 0; margin-top: 24pt;">{{ autor_nome | upper }}</p>
<p class="party-qualification" style="text-indent: 0;">{{ autor_qualificacao }}</p>

<p style="text-indent: 0;">vem, por seus advogados, com fundamento nos artigos 1.694 e seguintes do Código Civil, propor a presente</p>

<h1>AÇÃO DE ALIMENTOS</h1>

<p style="text-indent: 0;">em face de <strong>{{ reu_nome | upper }}</strong>, {{ reu_qualificacao }}, pelos fatos e fundamentos a seguir expostos:</p>

<h2>I - DOS FATOS</h2>
{{ fatos }}

<h2>II - DO PEDIDO DE ALIMENTOS</h2>
<p style="text-indent: 0;">O Autor pleiteia a concessão de alimentos {{ "provisórios e definitivos" if tipo_alimentos == "provisorios_definitivos" else ("provisórios" if tipo_alimentos == "provisorios" else "definitivos") }}, no valor mensal de <strong>R$ {{ "%.2f"|format(valor_pretendido) }}</strong> ({{ valor_pretendido | int }} reais).</p>

{{ justificativa_valor }}

<h2>III - DO DIREITO</h2>
{{ fundamentacao_juridica }}

<h2>IV - DOS PEDIDOS</h2>
<p style="text-indent: 0;">Ante o exposto, requer:</p>
{{ pedidos }}

<h2>V - DO VALOR DA CAUSA</h2>
<p class="valor-causa">{% if valor_causa %}Dá-se à causa o valor de <strong>R$ {{ '%.2f' | format(valor_causa) }}</strong> ({{ valor_causa | int }} reais).{% else %}Requer a atribuição do valor que Vossa Excelência entender pertinente.{% endif %}</p>

<p style="text-indent: 0; margin-top: 18pt;">Nestes termos,<br>Pede deferimento.</p>

<div class="signature-block">
<p class="signature-city-date">{{ cidade_assinatura }}, {{ data_assinatura.strftime('%d de %B de %Y') if data_assinatura else 'data' }}</p>
<div class="signature-line">
<p class="signature-name">{{ advogado_nome }}</p>
<p class="signature-oab">OAB {{ advogado_oab }}</p>
</div>
</div>
""",
                "default_values": {
                    "foro": "Foro Central da Comarca de São Paulo",
                    "vara": "Vara de Família e Sucessões",
                    "tipo_alimentos": "provisorios_definitivos"
                }
            },
            {
                "petition_slug": "acao-de-divorcio-litigioso",
                "template_name": "Modelo Padrão - Divórcio Litigioso",
                "template_slug": "modelo-padrao-divorcio-litigioso",
                "content": """
<div class="header">
<p class="header-forum">{{ foro | upper }}</p>
<p class="header-vara">{{ vara }}</p>
</div>

<p style="text-indent: 0;">Processo nº: {{ processo_numero or 'a ser definido' }}</p>

<p class="party-name" style="text-indent: 0; margin-top: 24pt;">{{ autor_nome | upper }}</p>
<p class="party-qualification" style="text-indent: 0;">{{ autor_qualificacao }}</p>

<p style="text-indent: 0;">vem, por seus advogados, com fundamento no artigo 1.571, § 1º do Código Civil, propor a presente</p>

<h1>AÇÃO DE DIVÓRCIO LITIGIOSO</h1>

<p style="text-indent: 0;">em face de <strong>{{ reu_nome | upper }}</strong>, {{ reu_qualificacao }}, pelos fatos e fundamentos a seguir expostos:</p>

<h2>I - DO CASAMENTO</h2>
<p style="text-indent: 0;">As partes contraíram matrimônio em {{ data_casamento.strftime('%d/%m/%Y') if data_casamento else 'data não informada' }}, sob o regime de {{ "comunhão parcial de bens" if regime_casamento == "comunhao_parcial" else ("comunhão universal de bens" if regime_casamento == "comunhao_universal" else ("separação total de bens" if regime_casamento == "separacao_total" else "participação final nos aquestos")) }}.</p>

{% if pacto_antenupcial == "sim" %}
<p style="text-indent: 0;">As partes celebraram pacto antenupcial, conforme documento anexo.</p>
{% endif %}

<h2>II - DOS FATOS</h2>
{{ fatos }}

<h2>III - DO DIREITO</h2>
{{ fundamentacao_juridica }}

<h2>IV - DOS PEDIDOS</h2>
<p style="text-indent: 0;">Ante o exposto, requer:</p>
{{ pedidos }}

<h2>V - DO VALOR DA CAUSA</h2>
<p class="valor-causa">{% if valor_causa %}Dá-se à causa o valor de <strong>R$ {{ '%.2f' | format(valor_causa) }}</strong> ({{ valor_causa | int }} reais).{% else %}Requer a atribuição do valor que Vossa Excelência entender pertinente.{% endif %}</p>

<p style="text-indent: 0; margin-top: 18pt;">Nestes termos,<br>Pede deferimento.</p>

<div class="signature-block">
<p class="signature-city-date">{{ cidade_assinatura }}, {{ data_assinatura.strftime('%d de %B de %Y') if data_assinatura else 'data' }}</p>
<div class="signature-line">
<p class="signature-name">{{ advogado_nome }}</p>
<p class="signature-oab">OAB {{ advogado_oab }}</p>
</div>
</div>
""",
                "default_values": {
                    "foro": "Foro Central da Comarca de São Paulo",
                    "vara": "Vara de Família e Sucessões",
                    "regime_casamento": "comunhao_parcial",
                    "pacto_antenupcial": "nao"
                }
            },
            {
                "petition_slug": "reclamacao-trabalhista",
                "template_name": "Modelo Padrão - Reclamação Trabalhista",
                "template_slug": "modelo-padrao-reclamacao-trabalhista",
                "content": """
<div class="header">
<p class="header-forum">{{ foro | upper }}</p>
<p class="header-vara">{{ vara }}</p>
</div>

<p style="text-indent: 0;">Processo nº: {{ processo_numero or 'a ser definido' }}</p>

<p class="party-name" style="text-indent: 0; margin-top: 24pt;">{{ autor_nome | upper }}</p>
<p class="party-qualification" style="text-indent: 0;">{{ autor_qualificacao }}</p>

<p style="text-indent: 0;">vem, por seus advogados, com fundamento na Constituição Federal e na Consolidação das Leis do Trabalho, propor a presente</p>

<h1>RECLAMAÇÃO TRABALHISTA</h1>

<p style="text-indent: 0;">em face de <strong>{{ reu_nome | upper }}</strong>, {{ reu_qualificacao }}, pelos fatos e fundamentos a seguir expostos:</p>

<h2>I - DA RELAÇÃO DE EMPREGO</h2>
<p style="text-indent: 0;">O Reclamante foi admitido em {{ data_admissao.strftime('%d/%m/%Y') if data_admissao else 'data não informada' }} para exercer a função de {{ cargo }}, com salário de R$ {{ "%.2f"|format(salario) }} mensais.</p>

{% if data_demissao %}
<p style="text-indent: 0;">A rescisão contratual ocorreu em {{ data_demissao.strftime('%d/%m/%Y') }}.</p>
{% endif %}

{% if horario_trabalho %}
<p style="text-indent: 0;">A jornada de trabalho era das {{ horario_trabalho }}.</p>
{% endif %}

<h2>II - DOS FATOS</h2>
{{ fatos }}

<h2>III - DA RECLAMAÇÃO</h2>
{{ motivo_reclamacao }}

<h2>IV - DO DIREITO</h2>
{{ fundamentacao_juridica }}

<h2>V - DOS PEDIDOS</h2>
<p style="text-indent: 0;">Ante o exposto, requer:</p>
{{ pedidos }}

<h2>VI - DO VALOR DA CAUSA</h2>
<p class="valor-causa">{% if valor_causa %}Dá-se à causa o valor de <strong>R$ {{ '%.2f' | format(valor_causa) }}</strong> ({{ valor_causa | int }} reais).{% else %}Requer a atribuição do valor que Vossa Excelência entender pertinente.{% endif %}</p>

<p style="text-indent: 0; margin-top: 18pt;">Nestes termos,<br>Pede deferimento.</p>

<div class="signature-block">
<p class="signature-city-date">{{ cidade_assinatura }}, {{ data_assinatura.strftime('%d de %B de %Y') if data_assinatura else 'data' }}</p>
<div class="signature-line">
<p class="signature-name">{{ advogado_nome }}</p>
<p class="signature-oab">OAB {{ advogado_oab }}</p>
</div>
</div>
""",
                "default_values": {
                    "foro": "Foro Central da Comarca de São Paulo",
                    "vara": "Vara do Trabalho"
                }
            },
            {
                "petition_slug": "acao-de-cobranca",
                "template_name": "Modelo Padrão - Ação de Cobrança",
                "template_slug": "modelo-padrao-acao-cobranca",
                "content": """
<div class="header">
<p class="header-forum">{{ foro | upper }}</p>
<p class="header-vara">{{ vara }}</p>
</div>

<p style="text-indent: 0;">Processo nº: {{ processo_numero or 'a ser definido' }}</p>

<p class="party-name" style="text-indent: 0; margin-top: 24pt;">{{ autor_nome | upper }}</p>
<p class="party-qualification" style="text-indent: 0;">{{ autor_qualificacao }}</p>

<p style="text-indent: 0;">vem, por seus advogados, com fundamento nos artigos 397 e seguintes do Código Civil, propor a presente</p>

<h1>AÇÃO DE COBRANÇA</h1>

<p style="text-indent: 0;">em face de <strong>{{ reu_nome | upper }}</strong>, {{ reu_qualificacao }}, pelos fatos e fundamentos a seguir expostos:</p>

<h2>I - DA OBRIGAÇÃO</h2>
<p style="text-indent: 0;">O Réu deve ao Autor a quantia de <strong>R$ {{ "%.2f"|format(valor_cobrado) }}</strong> ({{ valor_cobrado | int }} reais), com vencimento em {{ data_vencimento.strftime('%d/%m/%Y') if data_vencimento else 'data não informada' }}.</p>

<h3>Origem da Dívida</h3>
{{ origem_divida }}

<h2>II - DOS FATOS</h2>
{{ fatos }}

<h2>III - DO DIREITO</h2>
{{ fundamentacao_juridica }}

<h2>IV - DOS PEDIDOS</h2>
<p style="text-indent: 0;">Ante o exposto, requer:</p>
{{ pedidos }}

<h2>V - DO VALOR DA CAUSA</h2>
<p class="valor-causa">{% if valor_causa %}Dá-se à causa o valor de <strong>R$ {{ '%.2f' | format(valor_causa) }}</strong> ({{ valor_causa | int }} reais).{% else %}Requer a atribuição do valor que Vossa Excelência entender pertinente.{% endif %}</p>

<p style="text-indent: 0; margin-top: 18pt;">Nestes termos,<br>Pede deferimento.</p>

<div class="signature-block">
<p class="signature-city-date">{{ cidade_assinatura }}, {{ data_assinatura.strftime('%d de %B de %Y') if data_assinatura else 'data' }}</p>
<div class="signature-line">
<p class="signature-name">{{ advogado_nome }}</p>
<p class="signature-oab">OAB {{ advogado_oab }}</p>
</div>
</div>
""",
                "default_values": {
                    "foro": "Foro Central da Comarca de São Paulo",
                    "vara": "1ª Vara Cível"
                }
            }
        ]

        for template_data in templates_data:
            # Buscar o tipo de petição
            petition_type = PetitionType.query.filter_by(slug=template_data['petition_slug']).first()
            if not petition_type:
                print(f"⚠️ Tipo de petição não encontrado: {template_data['petition_slug']}")
                continue

            # Verificar se template já existe
            existing = PetitionTemplate.query.filter_by(slug=template_data['template_slug']).first()
            if existing:
                print(f"⚠️ Template já existe: {existing.name}")
                continue

            # Criar template
            template = PetitionTemplate(
                name=template_data['template_name'],
                slug=template_data['template_slug'],
                description=f"Template padrão para {petition_type.name}",
                content=template_data['content'],
                default_values=json.dumps(template_data['default_values']),
                is_global=True,
                petition_type_id=petition_type.id
            )

            db.session.add(template)
            db.session.commit()

            print(f"✓ Template criado: {template.name} para {petition_type.name}")

        print("\n🎉 Templates criados com sucesso!")

if __name__ == "__main__":
    create_templates()
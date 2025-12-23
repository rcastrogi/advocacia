#!/usr/bin/env python3
"""
Script para criar templates REALISTAS baseados em casos reais do direito brasileiro.
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

def create_real_case_templates():
    """Cria templates realistas baseados em casos reais"""

    with app.app_context():
        real_templates = [
            {
                "petition_slug": "acao-indenizacao-acidente-transito",
                "template_name": "Modelo Real - Acidente de Trânsito com Lesões",
                "template_slug": "modelo-real-acidente-transito-lesoes",
                "content": """
<div class="header">
<p class="header-forum">{{ foro | upper }}</p>
<p class="header-vara">{{ vara }}</p>
</div>

<p style="text-indent: 0;">Processo nº: {{ processo_numero or 'a ser definido' }}</p>

<p class="party-name" style="text-indent: 0; margin-top: 24pt;">{{ autor_nome | upper }}</p>
<p class="party-qualification" style="text-indent: 0;">{{ autor_qualificacao }}</p>

<p style="text-indent: 0;">vem, por seus advogados, com fundamento no art. 186 e 927 do Código Civil, propor a presente</p>

<h1>AÇÃO DE INDENIZAÇÃO POR DANOS MATERIAIS E MORAIS</h1>

<p style="text-indent: 0;">em face de <strong>{{ reu_nome | upper }}</strong>, {{ reu_qualificacao }}, pelos fatos e fundamentos a seguir expostos:</p>

<h2>I - DOS FATOS</h2>

<p style="text-indent: 0;">No dia {{ data_acidente.strftime('%d/%m/%Y') if data_acidente else 'data do acidente' }}, por volta das {{ hora_acidente.strftime('%H:%M') if hora_acidente else 'horário' }}, na {{ local_acidente }}, ocorreu um acidente de trânsito envolvendo:</p>

<ul>
<li><strong>Veículo do Autor:</strong> {{ veiculo_autor }}</li>
<li><strong>Veículo do Réu:</strong> {{ veiculo_reu }}</li>
</ul>

<p style="text-indent: 0;">O acidente foi do tipo "{{ {
    'colisao_traseira': 'colisão traseira',
    'colisao_lateral': 'colisão lateral',
    'atropelamento': 'atropelamento',
    'capotamento': 'capotamento',
    'saida_pista': 'saída de pista',
    'outro': 'outro'
}.get(tipo_acidente, tipo_acidente) }}", sendo que o Réu é responsável pela colisão.</p>

{% if seguradora_reu %}
<p style="text-indent: 0;">O veículo do Réu estava segurado pela {{ seguradora_reu }}{% if numero_sinistro %}, sinistro nº {{ numero_sinistro }}{% endif %}.</p>
{% endif %}

{{ fatos_adicionais or 'Conforme será demonstrado no curso do processo, o acidente ocorreu por culpa exclusiva do Réu.' }}

<h2>II - DOS DANOS MATERIAIS E MORAIS</h2>

<h3>Danos Materiais</h3>
{{ danos_materiais }}

<p style="text-indent: 0;">O valor dos danos materiais perfaz a quantia de <strong>R$ {{ "%.2f"|format(valor_danos_materiais) }}</strong> ({{ valor_danos_materiais | int }} reais).</p>

<h3>Danos Morais</h3>
{{ danos_morais }}

<p style="text-indent: 0;">Considerando a gravidade do acidente e suas consequências, pleiteia-se a condenação do Réu ao pagamento de danos morais no valor de <strong>R$ {{ "%.2f"|format(valor_danos_morais) }}</strong> ({{ valor_danos_morais | int }} reais).</p>

<h2>III - DO DIREITO</h2>

<p style="text-indent: 0;">O Código Civil, em seu art. 186, estabelece que "aquele que, por ação ou omissão voluntária, negligência ou imprudência, violar direito e causar dano a outrem, ainda que exclusivamente moral, comete ato ilícito".</p>

<p style="text-indent: 0;">Já o art. 927 do mesmo diploma legal determina que "aquele que, por ato ilícito (arts. 186 e 187), causar dano a outrem, fica obrigado a repará-lo".</p>

<p style="text-indent: 0;">A responsabilidade civil no acidente de trânsito decorre da culpa do condutor, conforme estabelecido no art. 929 do Código Civil.</p>

{{ fundamentacao_juridica_adicional or '' }}

<h2>IV - DOS PEDIDOS</h2>

<p style="text-indent: 0;">Ante o exposto, requer a Vossa Excelência:</p>

<ol>
<li>A citação do Réu para, querendo, contestar a presente ação, sob pena de revelia;</li>
<li>A procedência da ação para condenar o Réu ao pagamento de:</li>
<ul>
<li>Danos materiais: R$ {{ "%.2f"|format(valor_danos_materiais) }}</li>
<li>Danos morais: R$ {{ "%.2f"|format(valor_danos_morais) }}</li>
<li>Total: R$ {{ "%.2f"|format(valor_total_pretendido) }}</li>
</ul>
<li>A condenação do Réu ao pagamento de custas processuais e honorários advocatícios;</li>
<li>A produção de todos os meios de prova em direito admitidos, especialmente perícia técnica, testemunhal e documental.</li>
</ol>

<h2>V - DO VALOR DA CAUSA</h2>

<p class="valor-causa">Dá-se à causa o valor de <strong>R$ {{ "%.2f"|format(valor_total_pretendido) }}</strong> ({{ valor_total_pretendido | int }} reais).</p>

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
                    "foro": "Foro Regional de Santana - Comarca de São Paulo",
                    "vara": "2ª Vara Cível",
                    "tipo_acidente": "colisao_traseira"
                }
            },
            {
                "petition_slug": "acao-trabalhista-rescisao-indireta",
                "template_name": "Modelo Real - Rescisão Indireta por Assédio Moral",
                "template_slug": "modelo-real-rescisao-indireta-assedio",
                "content": """
<div class="header">
<p class="header-forum">{{ foro | upper }}</p>
<p class="header-vara">{{ vara }}</p>
</div>

<p style="text-indent: 0;">Processo nº: {{ processo_numero or 'a ser definido' }}</p>

<p class="party-name" style="text-indent: 0; margin-top: 24pt;">{{ autor_nome | upper }}</p>
<p class="party-qualification" style="text-indent: 0;">{{ autor_qualificacao }}</p>

<p style="text-indent: 0;">vem, por seus advogados, com fundamento no art. 483 da CLT, propor a presente</p>

<h1>RECLAMAÇÃO TRABALHISTA</h1>

<p style="text-indent: 0;">em face de <strong>{{ reu_nome | upper }}</strong>, {{ reu_qualificacao }}, pelos fatos e fundamentos a seguir expostos:</p>

<h2>I - DA RELAÇÃO DE EMPREGO</h2>

<p style="text-indent: 0;">O Autor foi admitido em {{ data_admissao.strftime('%d/%m/%Y') if data_admissao else 'data de admissão' }} para exercer a função de {{ cargo_funcao }}, com salário inicial de R$ {{ "%.2f"|format(salario_base) }} ({{ salario_base | int }} reais).</p>

<p style="text-indent: 0;">O contrato de trabalho era {{ {
    'experiencia': 'de experiência',
    'determinado': 'por prazo determinado',
    'indeterminado': 'por prazo indeterminado',
    'temporario': 'temporário'
}.get(tipo_contrato, tipo_contrato) }}.</p>

<h2>II - DOS FATOS</h2>

<p style="text-indent: 0;">Durante o período de vigência do contrato de trabalho, o Autor foi submetido a constantes situações de assédio moral praticadas pelos superiores hierárquicos e colegas de trabalho, tornando o ambiente laboral insalubre e prejudicial à sua saúde física e mental.</p>

<p style="text-indent: 0;">Dentre os episódios de assédio moral sofridos, destacam-se:</p>

{{ fatos_detalhados or 'Conforme será demonstrado no curso do processo, as práticas de assédio moral se tornaram insustentáveis, justificando a rescisão indireta do contrato de trabalho.' }}

<p style="text-indent: 0;">Diante da impossibilidade de continuar trabalhando em tais condições, o Autor viu-se compelido a rescindir indiretamente o contrato de trabalho em {{ data_demissao.strftime('%d/%m/%Y') if data_demissao else 'data da rescisão' }}.</p>

<h2>III - DAS VERBAS RESCISÓRIAS</h2>

<p style="text-indent: 0;">Com a rescisão indireta do contrato de trabalho, fazem jus ao Autor as seguintes verbas rescisórias:</p>

{{ verbas_rescisorias }}

<h2>IV - DO DIREITO</h2>

<p style="text-indent: 0;">A Consolidação das Leis do Trabalho, em seu art. 483, prevê a rescisão indireta quando:</p>

<blockquote>"a) forem exigidos serviços superiores às suas forças, defesos por lei, contrários aos bons costumes, ou alheios ao contrato; b) for tratado pelo empregador ou por seus superiores hierárquicos com rigor excessivo; c) correr sério perigo manifestado de mal considerável; d) não cumprir o empregador as obrigações do contrato."</blockquote>

<p style="text-indent: 0;">O assédio moral, consistente em condutas abusivas que atingem a dignidade do trabalhador, configura justa causa para a rescisão indireta do contrato de trabalho.</p>

<p style="text-indent: 0;">A Constituição Federal, em seu art. 7º, XXII, assegura ao trabalhador ambiente de trabalho saudável e digno.</p>

{{ fundamentacao_juridica_adicional or '' }}

<h2>V - DOS PEDIDOS</h2>

<p style="text-indent: 0;">Ante o exposto, requer a Vossa Excelência:</p>

<ol>
<li>A citação do Réu para, querendo, contestar a presente reclamação, sob pena de revelia;</li>
<li>A declaração de rescisão indireta do contrato de trabalho;</li>
<li>A condenação do Réu ao pagamento das verbas rescisórias devidas;</li>
<li>A condenação do Réu ao pagamento de indenização por danos morais decorrentes do assédio sofrido;</li>
<li>A condenação do Réu ao pagamento de custas processuais e honorários advocatícios;</li>
<li>A produção de todos os meios de prova em direito admitidos, especialmente testemunhal e documental.</li>
</ol>

<h2>VI - DO VALOR DA CAUSA</h2>

<p class="valor-causa">{% if valor_causa %}Dá-se à causa o valor de <strong>R$ {{ "%.2f"|format(valor_causa) }}</strong> ({{ valor_causa | int }} reais).{% else %}Requer a atribuição do valor que Vossa Excelência entender pertinente.{% endif %}</p>

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
                    "foro": "Forum Trabalhista de São Paulo",
                    "vara": "Vara do Trabalho de São Paulo",
                    "tipo_contrato": "indeterminado",
                    "tipo_rescisao": "rescisao_indireta"
                }
            },
            {
                "petition_slug": "acao-despejo-fim-contrato",
                "template_name": "Modelo Real - Despejo por Fim de Contrato Residencial",
                "template_slug": "modelo-real-despejo-fim-contrato-residencial",
                "content": """
<div class="header">
<p class="header-forum">{{ foro | upper }}</p>
<p class="header-vara">{{ vara }}</p>
</div>

<p style="text-indent: 0;">Processo nº: {{ processo_numero or 'a ser definido' }}</p>

<p class="party-name" style="text-indent: 0; margin-top: 24pt;">{{ autor_nome | upper }}</p>
<p class="party-qualification" style="text-indent: 0;">{{ autor_qualificacao }}</p>

<p style="text-indent: 0;">vem, por seus advogados, com fundamento no art. 46, § 2º, da Lei nº 8.245/91, propor a presente</p>

<h1>AÇÃO DE DESPEJO</h1>

<p style="text-indent: 0;">em face de <strong>{{ reu_nome | upper }}</strong>, {{ reu_qualificacao }}, pelos fatos e fundamentos a seguir expostos:</p>

<h2>I - DO CONTRATO DE LOCAÇÃO</h2>

<p style="text-indent: 0;">O Autor é proprietário do imóvel {{ {
    'apartamento': 'apartamento',
    'casa': 'casa',
    'terreno': 'terreno',
    'sala_comercial': 'sala comercial',
    'galpao': 'galpão',
    'outro': 'imóvel'
}.get(tipo_imovel, tipo_imovel) }} localizado à {{ endereco_imovel }}.</p>

{% if matricula_imovel %}
<p style="text-indent: 0;">O imóvel possui matrícula nº {{ matricula_imovel }}.</p>
{% endif %}

<p style="text-indent: 0;">O contrato de locação foi firmado em {{ data_inicio_contrato.strftime('%d/%m/%Y') if data_inicio_contrato else 'data de início' }}, com prazo determinado findo em {{ data_fim_contrato.strftime('%d/%m/%Y') if data_fim_contrato else 'data de fim' }}.</p>

<p style="text-indent: 0;">O valor do aluguel pactuado era de R$ {{ "%.2f"|format(valor_aluguel) }} ({{ valor_aluguel | int }} reais) mensais.</p>

<h2>II - DOS FATOS</h2>

<p style="text-indent: 0;">Findo o prazo contratual em {{ data_fim_contrato.strftime('%d/%m/%Y') if data_fim_contrato else 'data de término' }}, o Réu permanece no imóvel sem qualquer justificativa legal, mantendo-se em situação de esbulho possessório.</p>

<p style="text-indent: 0;">Apesar das notificações extrajudiciais enviadas ao Réu, este se recusa a desocupar o imóvel voluntariamente.</p>

{{ fatos_adicionais or 'O Autor necessita reaver a posse do imóvel para uso próprio/familiar.' }}

<h2>III - DO DIREITO</h2>

<p style="text-indent: 0;">A Lei do Inquilinato (Lei nº 8.245/91), em seu art. 46, § 2º, prevê que "findo o prazo contratual, resolve-se automaticamente o contrato de locação, passando o locatário a ocupar o imóvel por força da lei, sujeitando-se às normas legais pertinentes".</p>

<p style="text-indent: 0;">O art. 5º do mesmo diploma legal estabelece que "não se aplicam as disposições desta lei às locações residenciais de temporada, assim consideradas as que visem a períodos não superiores a noventa dias, ressalvadas as disposições legais específicas".</p>

<p style="text-indent: 0;">Findo o prazo do contrato, o locatário deve restituir o imóvel ao locador, sob pena de caracterizar-se a ocupação como esbulho possessório.</p>

{{ fundamentacao_juridica_adicional or '' }}

<h2>IV - DOS PEDIDOS</h2>

<p style="text-indent: 0;">Ante o exposto, requer a Vossa Excelência:</p>

<ol>
<li>A citação do Réu para, querendo, contestar a presente ação, sob pena de revelia;</li>
<li>A procedência da ação para:</li>
<ul>
<li>Condenar o Réu à desocupação do imóvel no prazo de 30 (trinta) dias;</li>
<li>Condenar o Réu ao pagamento dos aluguéis vencidos e vincendos até a efetiva desocupação;</li>
<li>Condenar o Réu ao pagamento das custas processuais e honorários advocatícios;</li>
</ul>
<li>A expedição de mandado de despejo, com fixação de data para desocupação;</li>
<li>A produção de todos os meios de prova em direito admitidos, especialmente documental e testemunhal.</li>
</ol>

<h2>V - DO VALOR DA CAUSA</h2>

<p class="valor-causa">Dá-se à causa o valor de <strong>R$ {{ "%.2f"|format(valor_aluguel * 12) }}</strong> ({{ (valor_aluguel * 12) | int }} reais), correspondente a 12 (doze) meses de aluguel.</p>

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
                    "vara": "3ª Vara Cível",
                    "tipo_imovel": "apartamento"
                }
            },
            {
                "petition_slug": "acao-consumidor-fornecedor",
                "template_name": "Modelo Real - Vício do Produto - Celular com Defeito",
                "template_slug": "modelo-real-consumidor-vicio-produto",
                "content": """
<div class="header">
<p class="header-forum">{{ foro | upper }}</p>
<p class="header-vara">{{ vara }}</p>
</div>

<p style="text-indent: 0;">Processo nº: {{ processo_numero or 'a ser definido' }}</p>

<p class="party-name" style="text-indent: 0; margin-top: 24pt;">{{ autor_nome | upper }}</p>
<p class="party-qualification" style="text-indent: 0;">{{ autor_qualificacao }}</p>

<p style="text-indent: 0;">vem, por seus advogados, com fundamento no art. 18, § 1º, do Código de Defesa do Consumidor, propor a presente</p>

<h1>AÇÃO DE RESPONSABILIDADE CIVIL DO FORNECEDOR</h1>

<p style="text-indent: 0;">em face de <strong>{{ reu_nome | upper }}</strong>, {{ reu_qualificacao }}, pelos fatos e fundamentos a seguir expostos:</p>

<h2>I - DA COMPRA DO PRODUTO</h2>

<p style="text-indent: 0;">Em {{ data_compra_contratacao.strftime('%d/%m/%Y') if data_compra_contratacao else 'data da compra' }}, o Autor adquiriu do Réu o produto {{ nome_produto_servico }}, pelo valor de R$ {{ "%.2f"|format(valor_pago) }} ({{ valor_pago | int }} reais).</p>

<h2>II - DOS FATOS</h2>

<p style="text-indent: 0;">Após breve período de uso, o produto apresentou os seguintes defeitos:</p>

{{ defeito_problema }}

<p style="text-indent: 0;">O Autor tentou solucionar o problema junto ao fornecedor, realizando as seguintes tentativas:</p>

{{ tentativas_solucao or 'Apesar das tentativas de contato, o fornecedor não solucionou o problema de forma adequada.' }}

<p style="text-indent: 0;">Diante da ineficácia das tentativas de solução amigável, o Autor viu-se obrigado a ajuizar a presente ação.</p>

<h2>III - DO DIREITO</h2>

<p style="text-indent: 0;">O Código de Defesa do Consumidor, em seu art. 18, estabelece que "os fornecedores de produtos de consumo duráveis ou não duráveis respondem solidariamente pelos vícios de qualidade ou quantidade que os tornem impróprios ou inadequados ao consumo a que se destinam ou lhes diminuam o valor".</p>

<p style="text-indent: 0;">O § 1º do mesmo artigo prevê que "não sendo o vício sanado no prazo máximo de trinta dias, pode o consumidor exigir, alternativamente e à sua escolha: I - a substituição do produto por outro da mesma espécie, em perfeitas condições de uso; II - a restituição imediata da quantia paga, monetariamente atualizada, sem prejuízo de eventuais perdas e danos; III - o abatimento proporcional do preço."</p>

<p style="text-indent: 0;">O art. 20 do CDC prevê a responsabilidade objetiva do fornecedor pelos vícios do produto.</p>

{{ fundamentacao_juridica_adicional or '' }}

<h2>IV - DOS PEDIDOS</h2>

<p style="text-indent: 0;">Ante o exposto, requer a Vossa Excelência:</p>

<ol>
<li>A citação do Réu para, querendo, contestar a presente ação, sob pena de revelia;</li>
<li>A procedência da ação para condenar o Réu a:</li>
<ul>
<li>Restituir o valor pago de R$ {{ "%.2f"|format(valor_pago) }}, devidamente corrigido;</li>
<li>Pagar indenização por danos morais no valor de R$ 5.000,00 (cinco mil reais);</li>
<li>Pagar custas processuais e honorários advocatícios;</li>
</ul>
<li>A produção de todos os meios de prova em direito admitidos, especialmente perícia técnica, testemunhal e documental.</li>
</ol>

<h2>V - DO VALOR DA CAUSA</h2>

<p class="valor-causa">Dá-se à causa o valor de <strong>R$ {{ "%.2f"|format(valor_pago + 5000) }}</strong> ({{ (valor_pago + 5000) | int }} reais).</p>

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
                    "vara": "Vara Especializada em Defesa do Consumidor",
                    "tipo_produto_servico": "produto"
                }
            }
        ]

        # Criar templates realistas
        for template_data in real_templates:
            # Verificar se já existe
            existing = PetitionTemplate.query.filter_by(slug=template_data['template_slug']).first()
            if existing:
                print(f"⚠ Template já existe: {template_data['template_name']}")
                continue

            # Buscar o tipo de petição
            pt = PetitionType.query.filter_by(slug=template_data['petition_slug']).first()
            if not pt:
                print(f"⚠ Tipo de petição não encontrado: {template_data['petition_slug']}")
                continue

            # Criar template
            template = PetitionTemplate(
                petition_type=pt,
                name=template_data['template_name'],
                slug=template_data['template_slug'],
                content=template_data['content'],
                default_values=json.dumps(template_data['default_values']),
                is_active=True
            )
            db.session.add(template)
            print(f"✓ Criado template realista: {template.name}")

        db.session.commit()
        print(f"\n📄 Criados {len(real_templates)} templates realistas!")

if __name__ == "__main__":
    create_real_case_templates()
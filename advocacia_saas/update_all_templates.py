"""
Script para atualizar todos os templates existentes com formatação HTML profissional.
"""

from app import create_app, db
from app.models import PetitionTemplate

app = create_app()

# Template de Petição Cível
PETICAO_CIVEL = """
<div class="header">
<p class="header-forum">{{ forum | upper }}</p>
<p class="header-vara">{{ vara }}</p>
</div>

<p style="text-indent: 0;">Processo nº: {{ process_number or 'a ser definido' }}</p>

<p class="party-name" style="text-indent: 0; margin-top: 24pt;">{{ author_name | upper }}</p>
<p class="party-qualification" style="text-indent: 0;">{{ author_qualification }}</p>

<p style="text-indent: 0;">vem, por seus advogados, com fundamento nos artigos 186, 187 e 927 do Código Civil e demais dispositivos aplicáveis, propor a presente</p>

<h1>AÇÃO CÍVEL</h1>

<p style="text-indent: 0;">em face de <strong>{{ defendant_name | upper }}</strong>, {{ defendant_qualification }}, pelos fatos e fundamentos a seguir expostos:</p>

<h2>I - DOS FATOS</h2>
{{ facts }}

<h2>II - DO DIREITO</h2>
{{ fundamentos }}

<h2>III - DOS PEDIDOS</h2>
<p style="text-indent: 0;">Ante o exposto, requer:</p>
{{ pedidos }}

<h2>IV - DO VALOR DA CAUSA</h2>
<p class="valor-causa">{% if valor_causa %}Dá-se à causa o valor de <strong>R$ {{ "%.2f" | format(valor_causa) }}</strong>.{% else %}Requer a atribuição do valor que Vossa Excelência entender pertinente.{% endif %}</p>

<p style="text-indent: 0; margin-top: 18pt;">Nestes termos,<br>Pede deferimento.</p>

<div class="signature-block">
<p class="signature-city-date">{{ cidade }}, {{ data_assinatura }}</p>
<div class="signature-line">
<p class="signature-name">{{ advogado_nome }}</p>
<p class="signature-oab">OAB {{ advogado_oab }}</p>
</div>
</div>
"""

# Template de Contestação
CONTESTACAO = """
<div class="header">
<p class="header-forum">{{ forum | upper }}</p>
<p class="header-vara">{{ vara }}</p>
</div>

<p style="text-indent: 0;">Processo nº: {{ process_number or '0000000-00.0000.0.00.0000' }}</p>

<p class="party-name" style="text-indent: 0; margin-top: 24pt;">{{ defendant_name | upper }}</p>
<p class="party-qualification" style="text-indent: 0;">{{ defendant_qualification }}</p>

<p style="text-indent: 0;">vem, respeitosamente, à presença de Vossa Excelência, por intermédio de seus advogados, apresentar</p>

<h1>CONTESTAÇÃO</h1>

<p style="text-indent: 0;">à ação proposta por <strong>{{ author_name | upper }}</strong>, {{ author_qualification }}, expondo o que segue:</p>

<h2>I - SÍNTESE DOS FATOS</h2>
{{ facts }}

<h2>II - PRELIMINARES</h2>
{{ fundamentos }}

<h2>III - DO MÉRITO</h2>
{{ pedidos }}

<h2>IV - DOS PEDIDOS FINAIS</h2>
<p style="text-indent: 0;">Ante o exposto, requer:</p>
<ol type="a">
<li>A rejeição total dos pedidos iniciais;</li>
<li>A condenação do autor ao pagamento das custas processuais e honorários advocatícios;</li>
<li>A produção de todos os meios de prova admitidos em direito, especialmente o depoimento pessoal do autor, oitiva de testemunhas e prova pericial.</li>
</ol>

<p style="text-indent: 0; margin-top: 18pt;">Nestes termos,<br>Pede deferimento.</p>

<div class="signature-block">
<p class="signature-city-date">{{ cidade }}, {{ data_assinatura }}</p>
<div class="signature-line">
<p class="signature-name">{{ advogado_nome }}</p>
<p class="signature-oab">OAB {{ advogado_oab }}</p>
</div>
</div>
"""

# Template de Divórcio Consensual
DIVORCIO_CONSENSUAL = """
<div class="header">
<p class="header-forum">{{ forum | upper }}</p>
<p class="header-vara">{{ vara }}</p>
</div>

<p style="text-indent: 0;">Processo nº: {{ process_number or 'a atribuir' }}</p>

<p class="party-name" style="text-indent: 0; margin-top: 24pt;">{{ spouse_one_name | upper }}</p>
<p class="party-qualification" style="text-indent: 0;">{{ spouse_one_qualification }}</p>

<p style="text-indent: 0; margin: 12pt 0;"><strong>e</strong></p>

<p class="party-name" style="text-indent: 0;">{{ spouse_two_name | upper }}</p>
<p class="party-qualification" style="text-indent: 0;">{{ spouse_two_qualification }}</p>

<p style="text-indent: 0; margin-top: 18pt;">vêm, por seus advogados, propor a presente</p>

<h1>{{ action_type | upper }}</h1>

<p>em razão do término da união celebrada em {{ marriage_city or '...' }}{% if marriage_date %} em {{ marriage_date }}{% endif %}, sob o regime de <strong>{{ marriage_regime or 'comunhão parcial de bens' }}</strong>.{% if prenup_summary %} Pacto antenupcial: {{ prenup_summary }}.{% endif %}</p>

<h2>I - DOS FATOS</h2>
{{ facts }}

<h2>II - DOS FILHOS E DA GUARDA</h2>
<p>{{ children_info or 'Não há filhos menores ou incapazes.' }}</p>
<p><strong>Proposta de guarda e convivência:</strong> {{ custody_plan or 'Guarda compartilhada conforme acordo anexo.' }}</p>

<h2>III - DOS ALIMENTOS</h2>
<p>{{ alimony_plan or 'As partes renunciam aos alimentos recíprocos.' }}</p>

<h2>IV - DO PATRIMÔNIO</h2>
<p>{{ property_description or 'Não há bens a partilhar ou os bens serão objeto de ação própria.' }}</p>

<h2>V - DO DIREITO</h2>
{{ fundamentos }}

<h2>VI - DOS PEDIDOS</h2>
<p style="text-indent: 0;">Ante o exposto, requerem:</p>
{{ pedidos }}

<p style="text-indent: 0; margin-top: 18pt;">Nestes termos,<br>Pedem deferimento.</p>

<div class="signature-block">
<p class="signature-city-date">{{ cidade }}, {{ data_assinatura }}</p>
<div class="signature-line">
<p class="signature-name">{{ advogado_nome }}</p>
<p class="signature-oab">OAB {{ advogado_oab }}</p>
</div>
</div>
"""

TEMPLATES_TO_UPDATE = {
    "modelo-padrao-peticao-inicial": PETICAO_CIVEL,
    "modelo-padrao-contestacao": CONTESTACAO,
    "modelo-familia-divorcio": DIVORCIO_CONSENSUAL,
}


def update_all_templates():
    with app.app_context():
        for slug, content in TEMPLATES_TO_UPDATE.items():
            template = PetitionTemplate.query.filter_by(slug=slug).first()
            if template:
                template.content = content.strip()
                db.session.commit()
                print(f"✓ Atualizado: {template.name} (ID: {template.id})")
            else:
                print(f"✗ Template não encontrado: {slug}")

        print("\n✓ Todos os templates foram atualizados!")


if __name__ == "__main__":
    update_all_templates()

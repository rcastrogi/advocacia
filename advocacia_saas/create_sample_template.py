#!/usr/bin/env python3
"""
Script para criar um template básico para o tipo de petição de exemplo.
"""

from app import create_app, db
from app.models import PetitionTemplate, PetitionType


def create_sample_template():
    """Cria um template básico para o tipo de petição de exemplo"""

    app = create_app()
    with app.app_context():
        # Buscar o tipo de petição
        petition_type = PetitionType.query.filter_by(
            slug="acao-civel-indenizatoria"
        ).first()
        if not petition_type:
            print("❌ Tipo de petição não encontrado")
            return

        # Template content
        template_content = """
<div class="header">
<p class="header-forum">{{ foro | upper }}</p>
<p class="header-vara">{{ vara }}</p>
</div>

<p style="text-indent: 0;">Processo nº: {{ processo_numero or 'a ser definido' }}</p>

<p class="party-name" style="text-indent: 0; margin-top: 24pt;">{{ autor_nome | upper }}</p>
<p class="party-qualification" style="text-indent: 0;">{{ autor_qualificacao }}</p>

<p style="text-indent: 0;">vem, por seus advogados, com fundamento nos artigos 186, 187 e 927 do Código Civil e demais dispositivos aplicáveis, propor a presente</p>

<h1>AÇÃO INDENIZATÓRIA CÍVEL</h1>

<p style="text-indent: 0;">em face de <strong>{{ reu_nome | upper }}</strong>, {{ reu_qualificacao }}, pelos fatos e fundamentos a seguir expostos:</p>

<h2>I - DOS FATOS</h2>
{{ fatos }}

<h2>II - DO DIREITO</h2>
{{ fundamentacao_juridica }}

<h2>III - DOS PEDIDOS</h2>
<p style="text-indent: 0;">Ante o exposto, requer:</p>
{{ pedidos }}

<h2>IV - DO VALOR DA CAUSA</h2>
<p class="valor-causa">{% if valor_causa %}Dá-se à causa o valor de <strong>R$ {{ "%.2f"|format(valor_causa) }}</strong> ({{ valor_causa | int }} reais).{% else %}Requer a atribuição do valor que Vossa Excelência entender pertinente.{% endif %}</p>

<p style="text-indent: 0; margin-top: 18pt;">Nestes termos,<br>Pede deferimento.</p>

<div class="signature-block">
<p class="signature-city-date">{{ cidade_assinatura }}, {{ data_assinatura.strftime('%d de %B de %Y') if data_assinatura else 'data' }}</p>
<div class="signature-line">
<p class="signature-name">{{ advogado_nome }}</p>
<p class="signature-oab">OAB {{ advogado_oab }}</p>
</div>
</div>
"""

        # Valores padrão
        default_values = {
            "foro": "Foro Central da Comarca de São Paulo",
            "vara": "1ª Vara Cível",
            "comarca": "São Paulo/SP",
        }

        # Criar template
        template = PetitionTemplate(
            name="Modelo Padrão - Ação Indenizatória",
            slug="modelo-padrao-acao-indenizatoria",
            description="Template básico para ações indenizatórias cíveis",
            content=template_content,
            default_values=json.dumps(default_values),
            is_global=True,
            petition_type_id=petition_type.id,
        )

        db.session.add(template)
        db.session.commit()

        print(f"✓ Template criado: {template.name}")
        print(f"📝 Slug: {template.slug}")
        print("🎉 Template associado ao tipo de petição com sucesso!")


if __name__ == "__main__":
    import json

    create_sample_template()

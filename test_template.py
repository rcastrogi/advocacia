#!/usr/bin/env python3
"""
Test template syntax
"""

from jinja2 import Template, TemplateSyntaxError

template = """EXCELENTÍSSIMO(A) SENHOR(A) DOUTOR(A) JUIZ(ÍZA) DE DIREITO DA {{ vara }}

{{ autor_nome }}, {{ autor_qualificacao }}, vem propor:

{{ tipo_acao }}

em face de {{ reu_nome }}, {{ reu_qualificacao }}

{{ CABEÇALHO / ENDEREÇAMENTO }}

{{ AUTOR / REQUERENTE }}

{{ RÉU / REQUERIDO }}

{{ dos_fatos }}

{{ DO DIREITO / FUNDAMENTAÇÃO }}

{{ DOS PEDIDOS }}

{{ VALOR DA CAUSA }}

{{ PROVAS }}

{{ LOCAL E DATA }}

{{ local }}, {{ data }}

{{ advogado_nome }}
{{ advogado_oab }}"""

lines = template.split("\n")
for i, line in enumerate(lines, 1):
    print(f"{i}: {repr(line)}")

try:
    Template(template)
    print("Template syntax is valid.")
except TemplateSyntaxError as e:
    print(f"Syntax error at line {e.lineno}: {e.message}")
except Exception as e:
    print(f"Other error: {e}")

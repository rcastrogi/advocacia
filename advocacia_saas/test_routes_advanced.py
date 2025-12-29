#!/usr/bin/env python3
"""
Teste das rotas das funcionalidades avançadas
"""

import requests
import sys

base_url = "http://127.0.0.1:5000"

def test_route(route, description):
    try:
        response = requests.get(f"{base_url}{route}", timeout=5)
        status = "✅" if response.status_code == 200 else "❌"
        print(f"{status} {description}: {route} (Status: {response.status_code})")
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"❌ {description}: {route} (Erro: {e})")
        return False

print("🧪 Testando rotas das funcionalidades avançadas...")
print("=" * 50)

routes = [
    ("/advanced/calendar", "Calendário Jurídico"),
    ("/advanced/automation", "Automação de Processos"),
    ("/advanced/reports", "Relatórios Avançados"),
]

all_working = True
for route, description in routes:
    if not test_route(route, description):
        all_working = False

print("=" * 50)
if all_working:
    print("🎉 Todas as rotas das funcionalidades avançadas estão funcionando!")
else:
    print("⚠️  Algumas rotas podem precisar de autenticação ou ter problemas.")
    print("💡 As rotas devem estar acessíveis após login no sistema.")
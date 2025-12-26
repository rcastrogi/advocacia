import requests
from bs4 import BeautifulSoup

print("🔍 TESTANDO LOGS DAS SEÇÕES DE PETIÇÕES")
print("=" * 50)

# Criar sessão
session = requests.Session()

try:
    # 1. Fazer login diretamente (CSRF desabilitado)
    print("1. Fazendo login...")
    login_data = {
        "email": "admin@petitio.com",
        "password": "admin123",
        "remember_me": "y",
    }

    login_response = session.post(
        "http://127.0.0.1:5000/auth/login", data=login_data, timeout=10
    )
    print(f"   Login status: {login_response.status_code}")

    if login_response.status_code in [200, 302]:
        print("   ✅ Login bem-sucedido")

        # 2. Acessar página de seções
        print("2. Acessando página de seções...")
        sections_response = session.get(
            "http://127.0.0.1:5000/admin/petitions/sections", timeout=10
        )
        print(f"   Seções status: {sections_response.status_code}")

        if sections_response.status_code == 200:
            print("✅ SUCESSO: Página de seções carregada!")
            print("📋 Verifique os logs no terminal do servidor Flask.")
            print("🔍 Procure por mensagens com [SECTIONS]")
        else:
            print(f"❌ ERRO: Status inesperado {sections_response.status_code}")
            print(f"Resposta: {sections_response.text[:300]}...")
    else:
        print("❌ ERRO: Login falhou")
        print(f"Resposta: {login_response.text[:300]}...")

except Exception as e:
    print(f"❌ ERRO de conexão: {e}")

print()
print("💡 INSTRUÇÕES:")
print("1. Verifique o terminal onde o Flask está rodando")
print("2. Procure por mensagens como:")
print("   - [SECTIONS] Iniciando petition_sections_list")
print("   - [SECTIONS] Usuário admin autenticado")
print("   - [SECTIONS] Encontradas X seções no banco")

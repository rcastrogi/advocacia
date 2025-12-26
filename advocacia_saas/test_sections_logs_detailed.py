import requests
from bs4 import BeautifulSoup

print("🔍 TESTANDO LOGS DAS SEÇÕES DE PETIÇÕES (DETALHADO)")
print("=" * 55)

# Criar sessão
session = requests.Session()

try:
    # 1. Acessar página de login
    print("1. Acessando página de login...")
    login_page = session.get("http://127.0.0.1:5000/auth/login", timeout=10)
    print(f"   Status: {login_page.status_code}")

    if login_page.status_code == 200:
        # 2. Fazer login
        print("2. Fazendo login...")
        login_data = {
            "email": "admin@petitio.com",
            "password": "admin123",
            "remember_me": "y",
        }

        login_response = session.post(
            "http://127.0.0.1:5000/auth/login", data=login_data, timeout=10
        )
        print(f"   Login status: {login_response.status_code}")
        print(f"   Login URL final: {login_response.url}")

        if "dashboard" in login_response.url or login_response.status_code in [
            200,
            302,
        ]:
            print("   ✅ Login aparentemente bem-sucedido")

            # 3. Tentar acessar página de seções diretamente
            print("3. Acessando /admin/petitions/sections...")
            sections_response = session.get(
                "http://127.0.0.1:5000/admin/petitions/sections",
                timeout=10,
                allow_redirects=True,
            )
            print(f"   Seções status: {sections_response.status_code}")
            print(f"   Seções URL final: {sections_response.url}")

            if sections_response.status_code == 200:
                print("✅ SUCESSO: Página de seções carregada!")
                print("📋 Verifique os logs no terminal do servidor Flask.")
                print("🔍 Procure por mensagens com [SECTIONS]")

                # Verificar se há erros na página
                if (
                    "Erro" in sections_response.text
                    or "error" in sections_response.text.lower()
                ):
                    print("⚠️  AVISO: Página contém mensagens de erro")
            else:
                print(f"❌ ERRO: Status inesperado {sections_response.status_code}")
                print(f"Resposta: {sections_response.text[:300]}...")
        else:
            print("❌ ERRO: Login falhou")
            print(f"Resposta: {login_response.text[:300]}...")
    else:
        print("❌ ERRO: Não conseguiu acessar página de login")

except Exception as e:
    print(f"❌ ERRO de conexão: {e}")

print()
print("💡 PRÓXIMOS PASSOS:")
print("1. Verifique o terminal do Flask para logs [SECTIONS]")
print("2. Se não houver logs, pode ser que a rota não exista")
print("3. Verifique se o usuário admin tem permissões")

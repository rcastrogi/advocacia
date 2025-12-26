import requests

base_url = "http://127.0.0.1:5000"

try:
    session = requests.Session()

    print("🔍 Testando aplicação...")

    # Testar página inicial
    response = session.get(base_url, timeout=10)
    print(f"📄 Página inicial: {response.status_code}")

    if response.status_code == 200:
        print("✅ Aplicação rodando!")

        # Testar login
        login_data = {
            "email": "admin@petitio.com",
            "password": "admin123",
            "submit": "Entrar",
        }
        response = session.post(
            f"{base_url}/auth/login", data=login_data, allow_redirects=True, timeout=10
        )
        print(f"🔑 Login: {response.status_code}")

        if "admin" in response.text.lower():
            print("✅ Login OK!")

            # Testar seções
            response = session.get(f"{base_url}/admin/petitions/sections", timeout=10)
            print(f"🧩 Seções: {response.status_code}")

            if response.status_code == 200 and "Seções de Petição" in response.text:
                print("✅ SEÇÕES FUNCIONANDO PERFEITAMENTE!")
                print(
                    "🎉 Você pode acessar em: http://127.0.0.1:5000/admin/petitions/sections"
                )
            else:
                print("❌ Problema nas seções")
                print(f"Status: {response.status_code}")
        else:
            print("❌ Login falhou")
            print("Verifique se as credenciais estão corretas")
    else:
        print("❌ Aplicação não responde")

except Exception as e:
    print(f"❌ Erro: {e}")

#!/usr/bin/env python3
import sys

import requests

# URL base do servidor
BASE_URL = "http://localhost:5000"


def test_with_login():
    """Testa a página fazendo login primeiro"""
    session = requests.Session()

    try:
        print("1. Testando página inicial...")
        response = session.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print("✅ Página inicial OK")
        else:
            print(f"❌ Página inicial falhou: {response.status_code}")
            return False

        print("\n2. Tentando acessar página de admin sem login...")
        response = session.get(f"{BASE_URL}/admin/petitions/models")
        if response.status_code == 302:  # Redirect para login
            print("✅ Redirecionamento para login (esperado)")
        else:
            print(f"❌ Resposta inesperada: {response.status_code}")

        print("\n3. Fazendo login...")
        login_data = {"username": "admin", "password": "admin123"}
        response = session.post(f"{BASE_URL}/auth/login", data=login_data)

        if "dashboard" in response.url or response.status_code == 302:
            print("✅ Login bem-sucedido")
        else:
            print(f"❌ Login falhou: {response.status_code}")
            print("Conteúdo:", response.text[:200])
            return False

        print("\n4. Acessando página de Modelos de Petição...")
        response = session.get(f"{BASE_URL}/admin/petitions/models")

        if response.status_code == 200:
            if "Modelos de Petição" in response.text:
                print("✅ SUCESSO TOTAL: Página de Modelos de Petição funcionando!")
                print("✅ Título encontrado no HTML")

                # Verificar se há modelos na página
                if "Modelo -" in response.text:
                    print("✅ Modelos encontrados na página")
                else:
                    print("⚠️  Nenhum modelo encontrado (pode estar vazio)")

                return True
            else:
                print("❌ ERRO: Título não encontrado no HTML")
                print("Conteúdo parcial:", response.text[:500])
                return False
        else:
            print(f"❌ ERRO HTTP: {response.status_code}")
            print("Conteúdo:", response.text[:300])
            return False

    except requests.exceptions.ConnectionError:
        print("❌ ERRO: Não foi possível conectar ao servidor")
        print("Verifique se o servidor está rodando em http://localhost:5000")
        return False
    except Exception as e:
        print(f"❌ ERRO inesperado: {e}")
        return False


if __name__ == "__main__":
    success = test_with_login()
    sys.exit(0 if success else 1)

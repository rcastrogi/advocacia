"""
Script para obter credenciais de usuários de teste do Mercado Pago via OAuth.

Este script ajuda a:
1. Gerar a URL de autorização OAuth
2. Trocar o código de autorização por Access Token

Uso:
1. Execute sem argumentos para ver a URL de autorização
2. Execute com --code=CODIGO para trocar por Access Token
"""

import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()


def get_app_credentials():
    """Obtém as credenciais da aplicação do .env"""
    access_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")

    if not access_token:
        print("❌ MERCADOPAGO_ACCESS_TOKEN não configurado no .env")
        sys.exit(1)

    # Extrair APP_ID do access token
    # Formato: TEST-{app_id}-{date}-{hash}-{user_id}
    parts = access_token.split("-")
    app_id = parts[1]

    # O client_secret precisa ser obtido do painel do desenvolvedor
    # Ou você pode configurá-lo no .env
    client_secret = os.getenv("MERCADOPAGO_CLIENT_SECRET")

    return app_id, client_secret


def show_authorization_url():
    """Mostra a URL de autorização OAuth"""
    app_id, _ = get_app_credentials()

    # URL de callback - pode ser qualquer URL válida para capturar o code
    redirect_uri = os.getenv(
        "MERCADOPAGO_REDIRECT_URI", "https://petitio.com.br/payments/callback"
    )

    auth_url = (
        f"https://auth.mercadopago.com/authorization?"
        f"client_id={app_id}&"
        f"response_type=code&"
        f"platform_id=mp&"
        f"state=test_user_auth&"
        f"redirect_uri={redirect_uri}"
    )

    print("=" * 70)
    print("  PASSO 1: AUTORIZAÇÃO DO USUÁRIO DE TESTE")
    print("=" * 70)
    print(f"\n📱 APP_ID: {app_id}")
    print(f"🔗 Redirect URI: {redirect_uri}")
    print("\n🌐 URL DE AUTORIZAÇÃO:")
    print("-" * 70)
    print(auth_url)
    print("-" * 70)

    print("""
📋 INSTRUÇÕES:
──────────────
1. Abra a URL acima em uma janela ANÔNIMA do navegador
2. Faça login com as credenciais do usuário de teste:
   - Usuário: TESTUSER4665501206944275531
   - Senha: CEIBWcVdOK

3. Se pedir código de verificação, use os últimos 6 dígitos do User ID 
   do usuário de teste

4. Autorize o acesso da aplicação

5. Você será redirecionado para a redirect_uri com um parâmetro 'code'
   Exemplo: https://petitio.com.br/payments/callback?code=TG-XXXXX&state=test_user_auth

6. Copie APENAS o valor do parâmetro 'code' (ex: TG-XXXXX...)

7. Execute novamente este script com:
   python get_test_user_credentials.py --code=TG-XXXXX-XXXXX
""")

    return auth_url


def exchange_code_for_token(code: str):
    """Troca o código de autorização por Access Token"""
    app_id, client_secret = get_app_credentials()

    if not client_secret:
        print("=" * 70)
        print("  ⚠️  CLIENT_SECRET NÃO CONFIGURADO")
        print("=" * 70)
        print("""
Para trocar o código por Access Token, você precisa do client_secret.

Você pode obtê-lo no painel do desenvolvedor:
1. Acesse: https://www.mercadopago.com.br/developers/panel/app
2. Clique na sua aplicação
3. Vá em "Credenciais de produção" ou "Credenciais de teste"
4. Copie o "Client Secret"
5. Adicione ao .env: MERCADOPAGO_CLIENT_SECRET=seu_client_secret

Ou execute com --secret=SEU_CLIENT_SECRET
""")
        secret_input = input("Cole o Client Secret aqui (ou Enter para sair): ").strip()
        if not secret_input:
            sys.exit(1)
        client_secret = secret_input

    redirect_uri = os.getenv(
        "MERCADOPAGO_REDIRECT_URI", "https://petitio.com.br/payments/callback"
    )

    print("=" * 70)
    print("  PASSO 2: TROCANDO CÓDIGO POR ACCESS TOKEN")
    print("=" * 70)
    print(f"\n🔑 Code: {code[:20]}...")
    print(f"📱 App ID: {app_id}")

    # Fazer a requisição OAuth
    response = requests.post(
        "https://api.mercadopago.com/oauth/token",
        json={
            "client_id": app_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "test_token": True,  # Importante para gerar token de teste
        },
    )

    print(f"\n📡 Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print("\n" + "=" * 70)
        print("  ✅ CREDENCIAIS OBTIDAS COM SUCESSO!")
        print("=" * 70)
        print("\n🔐 ACCESS TOKEN:")
        print(f"   {data.get('access_token')}")
        print("\n🔑 PUBLIC KEY:")
        print(f"   {data.get('public_key', 'N/A')}")
        print("\n🔄 REFRESH TOKEN:")
        print(f"   {data.get('refresh_token', 'N/A')}")
        print("\n👤 USER ID:")
        print(f"   {data.get('user_id')}")
        print("\n⏰ EXPIRA EM:")
        print(f"   {data.get('expires_in', 'N/A')} segundos")
        print("\n📝 SCOPE:")
        print(f"   {data.get('scope', 'N/A')}")
        print("\n🌐 LIVE MODE:")
        print(f"   {data.get('live_mode', 'N/A')}")

        print("\n" + "-" * 70)
        print("Adicione estas variáveis ao seu .env para usar o usuário de teste:")
        print("-" * 70)
        print("# Credenciais do usuário de teste")
        print(f"MERCADOPAGO_TEST_USER_ACCESS_TOKEN={data.get('access_token')}")
        if data.get("public_key"):
            print(f"MERCADOPAGO_TEST_USER_PUBLIC_KEY={data.get('public_key')}")
        print(f"MERCADOPAGO_TEST_USER_ID={data.get('user_id')}")

        return data
    else:
        print("\n❌ ERRO:")
        print(f"   {response.text}")
        return None


def main():
    args = sys.argv[1:]

    code = None
    secret = None

    for arg in args:
        if arg.startswith("--code="):
            code = arg.split("=", 1)[1]
        elif arg.startswith("--secret="):
            secret = arg.split("=", 1)[1]
            os.environ["MERCADOPAGO_CLIENT_SECRET"] = secret

    if code:
        exchange_code_for_token(code)
    else:
        show_authorization_url()


if __name__ == "__main__":
    main()

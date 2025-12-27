#!/usr/bin/env python3
import sys
import urllib.request

try:
    print("Testando conexão com o servidor...")
    # Primeiro testar a página inicial
    response = urllib.request.urlopen("http://localhost:5000/")
    html = response.read().decode("utf-8")

    if "Petitio" in html:
        print("✅ SUCESSO: Página inicial está funcionando!")
    else:
        print("❌ ERRO: Página inicial não contém 'Petitio'")

    # Agora testar a página de admin (que pode requerer login)
    print("\nTestando página de admin...")
    try:
        response = urllib.request.urlopen(
            "http://localhost:5000/admin/petitions/models"
        )
        html = response.read().decode("utf-8")

        if "Modelos de Petição" in html:
            print("✅ SUCESSO: Página de Modelos de Petição está funcionando!")
        elif "login" in html.lower():
            print("⚠️  AVISO: Página requer login (normal)")
        else:
            print("❌ ERRO: Conteúdo inesperado na página de admin")
            print("Conteúdo parcial:", html[:300])

    except urllib.error.HTTPError as e:
        if e.code == 302:  # Redirect (provavelmente para login)
            print("⚠️  AVISO: Redirecionamento (provavelmente para login) - normal")
        else:
            print(f"❌ ERRO HTTP: {e.code}")

except Exception as e:
    print(f"❌ ERRO: Não foi possível conectar ao servidor: {e}")
    sys.exit(1)

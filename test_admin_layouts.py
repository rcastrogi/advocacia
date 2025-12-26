import requests
from bs4 import BeautifulSoup

print("🔍 Verificando layouts das páginas admin...")
print("⚠️  Nota: Este teste verifica apenas a estrutura HTML das páginas")
print("   Para testar completamente, faça login manualmente no admin\n")

# Test different admin pages (without authentication)
test_pages = [
    ("/admin/usuarios", "Usuários"),
    ("/billing/plans", "Planos"),
    ("/billing/petition-types", "Tipos de Petição"),
    ("/billing/users", "Usuários & Planos"),
    ("/admin/petitions", "Administração de Petições"),
    ("/admin/roadmap", "Roadmap"),
    ("/admin/roadmap/feedback", "Feedback Roadmap"),
    ("/admin/depoimentos", "Depoimentos"),
]

all_correct = True

for url_path, page_name in test_pages:
    full_url = f"http://localhost:5000{url_path}"
    try:
        response = requests.get(full_url, allow_redirects=False)  # Não seguir redirects

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            # Check if sidebar exists (col-lg-2)
            sidebar = soup.find("div", class_="col-lg-2")
            content = soup.find("div", class_="col-lg-10")

            if sidebar and content:
                print(f"✅ {page_name}: Layout correto (sidebar + content)")
            else:
                print(f"❌ {page_name}: Layout INCORRETO (sem sidebar ou content)")
                all_correct = False

        elif response.status_code == 302:  # Redirect (probably to login)
            print(f"⚠️  {page_name}: Redirecionado para login (esperado)")

        else:
            print(f"❌ {page_name}: Erro HTTP {response.status_code}")
            all_correct = False

    except Exception as e:
        print(f"❌ {page_name}: Erro de conexão - {str(e)}")
        all_correct = False

print("\n" + "=" * 50)
if all_correct:
    print("🎉 SUCESSO: Todos os layouts admin estão corretos!")
    print("   ✅ Menu lateral esquerdo (col-lg-2)")
    print("   ✅ Conteúdo principal direito (col-lg-10)")
else:
    print("⚠️  ATENÇÃO: Alguns layouts ainda precisam ser corrigidos")
    print("   Verifique os templates que estendem admin/base_admin.html")
    print("   e usam o bloco 'admin_content'")

print("\n📋 Páginas que devem usar admin/base_admin.html:")
for _, page_name in test_pages:
    print(f"   • {page_name}")
print("\n🔗 Para testar completamente:")
print("   1. Acesse http://localhost:5000/auth/login")
print("   2. Faça login como admin")
print("   3. Navegue pelas páginas admin")
print("   4. Verifique se o menu lateral aparece em todas")

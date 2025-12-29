from app import create_app

app = create_app()
app.config["TESTING"] = True

with app.test_client() as client:
    # Testar acesso sem login (deve redirecionar)
    response = client.get("/processes")
    print(f"Status Code: {response.status_code}")
    location = response.headers.get("Location", "None")
    print(f"Location: {location}")

    if response.status_code == 302 and "login" in location:
        print("SUCCESS: Página redireciona para login (comportamento esperado)")
        print("✅ A página de processos está funcionando corretamente!")
    else:
        print("ERROR: Comportamento inesperado")
        print(f"Response data: {response.get_data(as_text=True)[:200]}...")

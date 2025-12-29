from app import create_app

app = create_app()

with app.test_client() as client:
    # Testar login
    login_response = client.post(
        "/auth/login", data={"email": "admin@petitio.com", "password": "admin123"}
    )

    print(f"Login Status: {login_response.status_code}")
    print(
        "Login response location:",
        login_response.headers.get("Location", "No redirect"),
    )

    # Verificar se estamos logados acessando uma página protegida
    response = client.get("/processes/", follow_redirects=False)
    print(f"Processes Status (no redirect): {response.status_code}")
    if response.status_code == 200:
        print("SUCCESS: Processes dashboard accessible after login!")
    elif response.status_code == 302:
        print("Still redirecting to login - authentication failed")
    else:
        print(f"Unexpected status: {response.status_code}")

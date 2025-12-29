import requests

try:
    response = requests.get("http://localhost:5000/processes", allow_redirects=False)
    print(f"Status Code: {response.status_code}")
    print(f"Location: {response.headers.get('Location', 'None')}")

    if response.status_code == 302 and "login" in response.headers.get("Location", ""):
        print("SUCCESS: Página redireciona para login (comportamento esperado)")
    else:
        print("ERROR: Comportamento inesperado")

except Exception as e:
    print(f"ERROR: {e}")

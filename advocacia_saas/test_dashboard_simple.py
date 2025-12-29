import os

from app import create_app
from flask import g

app = create_app()


# Simular um usuário logado
class MockUser:
    def __init__(self, id):
        self.id = id
        self.is_authenticated = True


with app.test_client() as client:
    # Simular login definindo o usuário na sessão
    with client.session_transaction() as sess:
        sess["_user_id"] = "1"  # ID do usuário admin

    print("Testing dashboard access...")

    try:
        response = client.get("/processes/")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("SUCCESS: Dashboard accessible!")
        else:
            print(f"Failed with status: {response.status_code}")
            print("Response:", response.data.decode()[:500])
    except Exception as e:
        print(f"Exception: {e}")
        import traceback

        traceback.print_exc()

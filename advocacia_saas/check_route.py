import requests

# Criar sessão e fazer login
session = requests.Session()
login_data = {'email': 'admin@petitio.com', 'password': 'admin123', 'remember_me': 'y'}
session.post('http://127.0.0.1:5000/auth/login', data=login_data)

# Tentar acessar a rota
response = session.get('http://127.0.0.1:5000/admin/petitions/sections')
print(f'Status: {response.status_code}')
print(f'Content-Type: {response.headers.get("content-type")}')
print(f'Content-Length: {len(response.text)}')

if response.status_code == 200:
    print('✅ Rota acessível')
    if 'Seções de Petição' in response.text:
        print('✅ Página contém título esperado')
    else:
        print('❌ Página não contém título esperado')
elif response.status_code == 403:
    print('❌ Acesso negado (403)')
elif response.status_code == 404:
    print('❌ Rota não encontrada (404)')
elif response.status_code == 500:
    print('❌ Erro interno do servidor (500)')
else:
    print(f'❌ Status inesperado: {response.status_code}')
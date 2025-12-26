import requests

session = requests.Session()

# Login
login_data = {'email': 'admin@petitio.com', 'password': 'admin123', 'remember_me': 'y'}
session.post('http://127.0.0.1:5000/auth/login', data=login_data)

# Acessar seções
response = session.get('http://127.0.0.1:5000/admin/petitions/sections')

print('CONTEÚDO DA PÁGINA DE SEÇÕES:')
print('=' * 40)
print(response.text[:2000])
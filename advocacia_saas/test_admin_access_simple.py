import requests
import time

# Aguardar o servidor iniciar
time.sleep(3)

try:
    # Testar acesso sem autenticação
    response = requests.get('http://127.0.0.1:5000/admin/users', timeout=10, allow_redirects=False)
    print(f'Status Code: {response.status_code}')
    if 'Location' in response.headers:
        print(f'Redirect to: {response.headers["Location"]}')

    # Verificar se redireciona para login
    if response.status_code == 302 and 'login' in response.headers.get('Location', ''):
        print('✅ Rota protegida - redireciona para login como esperado')
    else:
        print('❌ Rota não está protegida adequadamente')

except Exception as e:
    print(f'Erro: {e}')
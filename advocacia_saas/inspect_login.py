import requests
from bs4 import BeautifulSoup

print('🔍 PROCURANDO INPUT HIDDEN CSRF')
print('=' * 35)

try:
    response = requests.get('http://127.0.0.1:5000/auth/login', timeout=10)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        # Procurar por todos os inputs
        inputs = soup.find_all('input')
        print(f'Encontrados {len(inputs)} inputs:')

        for i, inp in enumerate(inputs):
            name = inp.get('name', 'sem nome')
            type_attr = inp.get('type', 'sem type')
            value = inp.get('value', '')[:20] if inp.get('value') else ''
            print(f'{i+1}. name="{name}" type="{type_attr}" value="{value}..."')

        # Procurar especificamente por csrf_token
        csrf_input = soup.find('input', {'name': 'csrf_token'})
        if csrf_input:
            print()
            print('✅ CSRF input encontrado:')
            print(f'   Name: {csrf_input.get("name")}')
            print(f'   Type: {csrf_input.get("type")}')
            print(f'   Value: {csrf_input.get("value")[:30]}...')
        else:
            print()
            print('❌ Input CSRF não encontrado')

            # Verificar se está em algum outro lugar
            if 'csrf_token' in response.text:
                print('Mas "csrf_token" foi encontrado no HTML em outro lugar')
    else:
        print(f'❌ Erro: {response.status_code}')

except Exception as e:
    print(f'❌ Erro: {e}')
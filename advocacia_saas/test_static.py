import requests

# Test if server is running
try:
    response = requests.get('http://localhost:5000/static/css/style.css', timeout=5)
    print(f'Status: {response.status_code}')
    print(f'Content-Type: {response.headers.get("content-type")}')
    print(f'Content length: {len(response.text)}')
    if response.status_code == 200:
        print('✅ Static file served successfully')
    else:
        print('❌ Static file not found')
except Exception as e:
    print(f'❌ Error: {e}')
    print('Server might not be running')
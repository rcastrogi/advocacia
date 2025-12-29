import requests

try:
    response = requests.get("http://localhost:5000/processes", allow_redirects=False)
    print(f"Status: {response.status_code}")
    print(f"Location: {response.headers.get('Location', 'None')}")
    print("SUCCESS: Server is responding correctly")
except Exception as e:
    print(f"ERROR: {e}")

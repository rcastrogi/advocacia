import requests
from bs4 import BeautifulSoup

# Test login with invalid credentials
url = "http://localhost:5000/auth/login"
data = {"email": "invalid@example.com", "password": "wrongpassword"}

response = requests.post(url, data=data, allow_redirects=False)

print(f"Status Code: {response.status_code}")
print(f"Response Headers: {response.headers}")

# Check if there are flash messages in the response
soup = BeautifulSoup(response.text, "html.parser")
alerts = soup.find_all("div", class_="alert")

print(f"Number of alerts found: {len(alerts)}")
for i, alert in enumerate(alerts):
    print(f"Alert {i + 1}: {alert.get_text(strip=True)}")
    print(f"Alert classes: {alert.get('class')}")

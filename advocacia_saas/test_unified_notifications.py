import requests
from bs4 import BeautifulSoup

# Test unified notification system
url = 'http://localhost:5000/auth/login'
data = {
    'email': 'invalid@example.com',
    'password': 'wrongpassword'
}

response = requests.post(url, data=data, allow_redirects=False)

print(f"Status Code: {response.status_code}")
print(f"Response Headers: {response.headers}")

# Check for flash messages in HTML
soup = BeautifulSoup(response.text, 'html.parser')
alerts = soup.find_all('div', class_='alert')

print(f"Number of Bootstrap alerts found: {len(alerts)}")
for i, alert in enumerate(alerts):
    print(f"Bootstrap Alert {i+1}: {alert.get_text(strip=True)}")
    print(f"Alert classes: {alert.get('class')}")

# Check if notification system script is loaded
notification_script = soup.find('script', src=lambda x: x and 'notification-system.js' in x)
if notification_script:
    print("✅ Unified notification system script is loaded")
else:
    print("❌ Unified notification system script NOT found")

# Check for old toast containers (should be removed)
old_toast_containers = soup.find_all('div', class_='toast-container')
print(f"Old toast containers found: {len(old_toast_containers)} (should be 0)")

# Check for flash messages script (should be removed)
flash_script = soup.find('script', string=lambda text: text and 'window.flashMessages' in text)
if flash_script:
    print("❌ Old flash messages script still present")
else:
    print("✅ Old flash messages script removed")
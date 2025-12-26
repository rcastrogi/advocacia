import http.cookiejar
import urllib.parse
import urllib.request

# Create a cookie jar to maintain session
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# Test login with correct credentials (general auth, not portal)
print("Testing login...")
data = urllib.parse.urlencode(
    {"email": "admin@petitio.com", "password": "admin123"}
).encode()

req = urllib.request.Request(
    "http://localhost:5000/auth/login", data=data, method="POST"
)
response = opener.open(req)
content = response.read().decode("utf-8")
print("Login response contains flashMessages:", "flashMessages" in content)
print("Login response URL:", response.url)

# Now try to access the roadmap feedback page
print("\nTesting roadmap feedback page...")
try:
    req = urllib.request.Request(
        "http://localhost:5000/roadmap/dashboard-analytics-avancado/feedback"
    )
    response = opener.open(req)
    content = response.read().decode("utf-8")
    print("Feedback page loaded successfully!")
    print("Contains flashMessages:", "flashMessages" in content)
    print("Contains form:", "<form" in content)
    print("URL after redirect:", response.url)
except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}: {e.reason}")
    if e.code == 302:  # Redirect (probably back to login)
        print("Redirected - probably not logged in properly")
        redirect_location = e.headers.get("Location")
        print("Redirect location:", redirect_location)

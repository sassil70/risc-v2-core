import requests
import sys

# We hit the NEXT.JS Frontend URL, not the Python Backend directly.
# This proves the Proxy is working.
url = "http://localhost:3000/api/auth/login"

payload = {
    "username": "admin",
    "password": "risc2026"
}
headers = {
    "Content-Type": "application/json"
}

print(f"Testing Full Stack Login...")
print(f"Target: {url} (Frontend Proxy)")

try:
    response = requests.post(url, json=payload, headers=headers)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        if token:
            print(f"SUCCESS: Auth Token Received!")
            print(f"Token Preview: {token[:15]}...")
        else:
            print(f"WARNING: 200 OK but no token found: {data}")
    else:
        print(f"FAILURE: Login Failed.")
        print(f"Response: {response.text}")

except requests.exceptions.ConnectionError:
    print(f"ERROR: Could not connect to localhost:3000. Is Next.js running?")
except Exception as e:
    print(f"ERROR: {e}")

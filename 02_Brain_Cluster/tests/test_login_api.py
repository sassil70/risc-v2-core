import requests

url = "http://localhost:8000/api/auth/login"
payload = {
    "username": "admin",
    "password": "risc2026"
}
headers = {
    "Content-Type": "application/json"
}

try:
    print(f"Testing Login API at {url}...")
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        print("SUCCESS: Login successful!")
        print("Token:", response.json().get("access_token")[:10] + "...")
    else:
        print(f"FAILURE: Status {response.status_code}")
        print("Response:", response.text)
except Exception as e:
    print(f"ERROR: {e}")

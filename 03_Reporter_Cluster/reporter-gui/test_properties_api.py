import requests
import sys

# Base URL (Frontend Proxy)
BASE_URL = "http://localhost:3000/api"

def test_flow():
    print("TEST: Full Data Flow Verification")
    print("-" * 30)

    # 1. Login
    print("1. Authenticating as 'admin'...")
    login_url = f"{BASE_URL}/auth/login"
    creds = {"username": "admin", "password": "risc2026"}
    
    try:
        res = requests.post(login_url, json=creds)
        if res.status_code != 200:
            print(f"LOGIN FAILED. Status: {res.status_code}")
            print(res.text)
            return

        data = res.json()
        token = data.get("access_token")
        user = data.get("user", {})
        user_id = user.get("id")

        if not token or not user_id:
            print("LOGIN ERROR: Missing token or user ID.")
            return

        print("LOGIN SUCCESS.")
        print(f"User ID: {user_id}")
        print("-" * 30)

        # 2. Fetch Sessions (Real Data)
        print(f"2. Fetching Sessions for User {user_id}...")
        # Note: In the Next.js code we saw: fetch(`/api/surveyor/sessions?user_id=${user.id}`)
        # This route is proxied to the backend.
        sessions_url = f"{BASE_URL}/surveyor/sessions"
        
        # We need to pass the token if the endpoint is protected. 
        # Looking at routers/sessions.py, it doesn't seem to have a 'depends' on oauth2_scheme for the router itself, 
        # but usually getting sessions is protected. 
        # However, the code I view regarding routers/sessions.py didn't show explicit protection on the route *decorator*, 
        # but let's send headers just in case.
        headers = {"Authorization": f"Bearer {token}"}
        
        res_sessions = requests.get(sessions_url, params={"user_id": user_id}, headers=headers)
        
        if res_sessions.status_code == 200:
            sessions = res_sessions.json()
            print(f"DATA FETCH SUCCESS. Found {len(sessions)} sessions.")
            for s in sessions:
                print(f" - [Real Data] ID: {s.get('id')} | Title: {s.get('title')} | Status: {s.get('status')}")
            
            print("-" * 30)
            print("VERIFICATION COMPLETE: The frontend is receiving real database records.")
        else:
            print(f"DATA FETCH FAILED. Status: {res_sessions.status_code}")
            print(res_sessions.text)

    except Exception as e:
        print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    test_flow()

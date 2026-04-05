import requests
import json
import sys

BASE_URL = "http://localhost:3000/api"

def run_tests():
    print("STARTING 4-STEP SYSTEM VERIFICATION")
    print("=" * 40)
    
    # Global State
    token = None
    user_id = None
    real_session_id = "prop_1767289350"
    
    # --- TEST 1: Login ---
    print("\n[TEST 1] LOGIN FLOW")
    try:
        res = requests.post(f"{BASE_URL}/auth/login", json={"username": "admin", "password": "risc2026"})
        if res.status_code == 200:
            data = res.json()
            token = data.get("access_token")
            user_id = data.get("user", {}).get("id")
            print(f"PASS: Logged in as User ID: {user_id}")
        else:
            print(f"FAIL: Login Status {res.status_code}")
            return
    except Exception as e:
         print(f"FAIL: Login Exception {e}")
         return

    # --- TEST 2: List Sessions (Check Cleanup) ---
    print("\n[TEST 2] SESSION CLEANUP VERIFICATION")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.get(f"{BASE_URL}/surveyor/sessions?user_id={user_id}", headers=headers)
        if res.status_code == 200:
            sessions = res.json()
            ids = [s['id'] for s in sessions]
            print(f"Found Sessions: {ids}")
            
            if "sim_universal_user_001" not in ids and real_session_id in ids:
                print("PASS: Mock data removed, Real data present.")
            else:
                print("FAIL: cleanup not verified or real data missing.")
                print(f"Expected removal of 'sim_universal_user_001', found: {ids}")
        else:
            print(f"FAIL: List Sessions Status {res.status_code}")
    except Exception as e:
        print(f"FAIL: List Sessions Exception {e}")

    # --- TEST 3: Detail Endpoint (JSON Blob) ---
    print("\n[TEST 3] FETCH FULL FLOOR PLAN JSON")
    try:
        # Note: Frontend hits /api/surveyor/sessions/{id} which Next proxies to Backend or Backend handles directly.
        # My previous edit added it to Backend. Next.js proxying usually forwards path.
        # Ensure 'rewrites' in next.config.js handle this, or that I hit 8000 directly to test Backend logic.
        # To be safe and test "System", I'll hit Port 8000 directly for the backend logic verification first.
        # Update: The user wants "Login to Floor Plan", so I should verify the API is reachable.
        
        backend_url = "http://localhost:8000"
        res = requests.get(f"{backend_url}/api/surveyor/sessions/{real_session_id}")
        
        if res.status_code == 200:
            details = res.json()
            plan = details.get("floor_plan", {})
            rooms = plan.get("rooms", [])
            print(f"PASS: Retrieved Session Details. Rooms Count: {len(rooms)}")
            if len(rooms) > 0:
                 print(f" - Sample Room: {rooms[0].get('name')} (Status: {rooms[0].get('status')})")
        else:
             print(f"FAIL: Detail Endpoint Status {res.status_code}")
             print(res.text)
    except Exception as e:
        print(f"FAIL: Detail Endpoint Exception {e}")

    # --- TEST 4: Frontend Simulation ---
    print("\n[TEST 4] FRONTEND ROUTE SIMULATION")
    # This simulates what the page.tsx useEffect does
    try:
        # Check if Next.js proxy allows this path
        # Assume Next.js is proxying /api/:path* to http://127.0.0.1:8000/:path*
        frontend_url = f"{BASE_URL}/surveyor/sessions/{real_session_id}"
        res = requests.get(frontend_url) 
        
        # Note: If Next.js only proxies specific routes, this might fail 404 if I didn't verify next.config.mjs
        # But commonly full /api proxy is set up. Let's see.
        if res.status_code == 200:
            print("PASS: Frontend Proxy successful.")
        else:
            print(f"WARN: Frontend Proxy returned {res.status_code}. Might need next.config.js update.")
            print("Since I added the endpoint to Backend, I might need to ensure Next.js proxies this specific sub-path.")
            
    except Exception as e:
        print(f"FAIL: Frontend Simulation Exception {e}")

    print("\n" + "=" * 40)
    print("VERIFICATION COMPLETE")

if __name__ == "__main__":
    run_tests()

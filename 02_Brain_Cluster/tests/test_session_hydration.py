import requests
import time
import json
import uuid

BASE_URL = "http://127.0.0.1:8001/api"

def run_test():
    print("Starting Session Hydration Test...")
    
    mock_user_id = str(uuid.uuid4())
    print(f"Mock User ID: {mock_user_id}")

    # 1. Create Project
    project_ref = f"HYDRATE-{int(time.time())}"
    print(f"1. Creating Project: {project_ref}")
    
    project_payload = {
        "reference_number": project_ref,
        "client_name": "Hydration Test Client"
    }
    res = requests.post(f"{BASE_URL}/projects", json=project_payload)
    if res.status_code != 200:
        print(f"Failed to create project: {res.text}")
        return
    
    project = res.json()
    project_id = project['id']
    print(f"   Project ID: {project_id}")

    # 2. Add Rooms to Project
    print("2. Adding Rooms to Project Scope...")
    rooms_to_add = [
        {"name": "Hydration Kitchen", "type": "kitchen"},
        {"name": "Hydration Lounge", "type": "general"}
    ]
    
    for r in rooms_to_add:
        res = requests.post(f"{BASE_URL}/projects/{project_id}/rooms", json=r)
        if res.status_code != 200:
             print(f"Failed to add room {r['name']}: {res.text}")
             return
    
    # 3. Create Session (The Hydration Step)
    print("3. Creating Session for Project...")
    session_payload = {
        "title": f"Inspection of {project_ref}",
        "surveyor_id": mock_user_id, 
        "project_id": project_id
    }
    
    res = requests.post(f"{BASE_URL}/surveyor/sessions", json=session_payload)
    if res.status_code != 200:
        print(f"Failed to create session: {res.text}")
        return
        
    session = res.json()
    session_id = session['id']
    print(f"   Session ID: {session_id}")
    
    # 4. Verify Hydration (Fetch Session Details)
    print("4. Verifying Session Scope (Reading from Disk/DB via API)...")
    res = requests.get(f"{BASE_URL}/sessions/{session_id}")
    if res.status_code != 200:
         print(f"Failed to get session details: {res.text}")
         return
         
    session_details = res.json()
    
    # Check if rooms exist in session_details
    floor_plan = session_details.get('floor_plan', {})
    rooms = floor_plan.get('rooms', [])
    
    print(f"   Rooms found in Session: {len(rooms)}")
    
    found_kitchen = any(r['name'] == "Hydration Kitchen" for r in rooms)
    found_lounge = any(r['name'] == "Hydration Lounge" for r in rooms)
    
    if found_kitchen and found_lounge:
        print("SUCCESS: Session correctly hydrated from Project Scope!")
    else:
        print("FAILURE: Rooms missing from Session Scope.")
        print(f"Actual Rooms: {json.dumps(rooms, indent=2)}")

if __name__ == "__main__":
    run_test()

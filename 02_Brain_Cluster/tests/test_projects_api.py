
import requests
import json
import time

BASE_URL = "http://127.0.0.1:8001/api/projects"

def run_test():
    print("Starting Projects API Test...")

    # 1. Create Project
    payload = {
        "reference_number": f"TEST-{int(time.time())}",
        "client_name": "Test Client Ltd"
    }
    
    try:
        print(f"POST {BASE_URL} with {payload}")
        res = requests.post(BASE_URL, json=payload)
        
        if res.status_code != 200:
            print(f"Creation Failed: {res.status_code} {res.text}")
            return
            
        project = res.json()
        project_id = project['id']
        print(f"Created Project: {project_id} ({project['reference_number']})")
        
        # 2. Add Room
        room_payload = {
            "name": "Master Bedroom",
            "type": "general"
        }
        print(f"POST {BASE_URL}/{project_id}/rooms")
        res = requests.post(f"{BASE_URL}/{project_id}/rooms", json=room_payload)
        
        if res.status_code != 200:
            print(f"Add Room Failed: {res.status_code} {res.text}")
            return
            
        rooms = res.json()
        print(f"Room Added. Current Rooms: {len(rooms)}")
        
        # 3. Verify List
        print(f"GET {BASE_URL}")
        res = requests.get(BASE_URL)
        projects = res.json()
        
        found = False
        for p in projects:
            if p['id'] == project_id:
                found = True
                print(f"Found Project in List. Rooms: {len(p['rooms'])}")
                if len(p['rooms']) > 0 and p['rooms'][0]['name'] == "Master Bedroom":
                     print("Verification Complete: Data persisted correctly.")
                else:
                     print("Data Mismatch in List View.")
                break
        
        if not found:
             print("Project not found in list.")

    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    run_test()

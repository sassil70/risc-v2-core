
import requests
import zipfile
import io
import os

ENDPOINT = "http://127.0.0.1:8001/api/v2/sync/upload_room"
SESSION_ID = "TEST_INTEGRATION_001"
ROOM_ID = "ROOM_TEST_A"

def create_dummy_zip():
    print("Creating Dummy Evidence Zip...")
    mf = io.BytesIO()
    with zipfile.ZipFile(mf, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('test.txt', b'This is a test evidence file.')
        zf.writestr('img_001.jpg', b'fake image data')
    mf.seek(0)
    return mf

def run_test():
    print(f"Launching Integration Test against {ENDPOINT}...")
    
    zip_data = create_dummy_zip()
    
    files = {
        'file': ('evidence.zip', zip_data, 'application/zip')
    }
    data = {
        'session_id': SESSION_ID,
        'room_id': ROOM_ID
    }
    
    try:
        response = requests.post(ENDPOINT, files=files, data=data, timeout=5)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("SUCCESS: Endpoint reachable and processing uploads.")
            # Verify basic response structure
            json_resp = response.json()
            if json_resp.get("status") == "synced" and json_resp.get("room_id") == ROOM_ID:
                 print("VERIFIED: Response payload matches expectations.")
            else:
                 print("WARNING: Response payload unexpected.")
        else:
            print("FAILURE: Non-200 response.")
            
    except requests.exceptions.ConnectionError:
        print("CRITICAL: Connection Refused. Is Docker running on port 8001?")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    run_test()

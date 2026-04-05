import requests
import zipfile
import os

# Configuration
BASE_URL = "http://127.0.0.1:8000/api/v2/sync/upload"
TEST_SESSION_ID = "simulation-test-session-001"
ZIP_FILENAME = f"{TEST_SESSION_ID}.zip"

def create_dummy_zip():
    print(f"📦 Creating dummy package: {ZIP_FILENAME}...")
    with zipfile.ZipFile(ZIP_FILENAME, 'w') as zipf:
        zipf.writestr('manifest.json', '{"session_id": "'+TEST_SESSION_ID+'", "timestamp": "2026-01-06T12:00:00Z"}')
        zipf.writestr('image1.txt', 'This simulates an image file content')
    print("✅ Dummy package created.")

def test_upload(include_header=True):
    header_status = "WITH" if include_header else "WITHOUT"
    print(f"\n🚀 Testing Upload {header_status} Header...")
    
    headers = {}
    if include_header:
        headers = {'session-id': TEST_SESSION_ID}
    
    try:
        with open(ZIP_FILENAME, 'rb') as f:
            files = {'file': (ZIP_FILENAME, f)}
            response = requests.post(BASE_URL, files=files, headers=headers)
            
        print(f"📡 Status Code: {response.status_code}")
        print(f"📄 Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ SUCCESS: Server accepted the file.")
        elif response.status_code == 422:
            print("❌ FAILURE: Server rejected request (Validation Error).")
        else:
            print(f"⚠️ UNEXPECTED: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    create_dummy_zip()
    
    # Test 1: Fail Case (Mimicking Current Mobile App)
    test_upload(include_header=False)
    
    # Test 2: Success Case (Target Fix)
    test_upload(include_header=True)

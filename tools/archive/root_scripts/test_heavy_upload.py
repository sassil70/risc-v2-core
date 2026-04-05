import requests
import zipfile
import os
import time

# Configuration
# Brain API is mapped to 8001 on Host
BASE_URL = "http://127.0.0.1:8001/api/v2/sync/upload" 
TEST_SESSION_ID = "mega-test-session-25-imgs"
ZIP_FILENAME = f"{TEST_SESSION_ID}.zip"
SOURCE_IMAGE = "test_image.jpg"

def create_heavy_zip():
    print(f"[INFO] Creating HEAVY package: {ZIP_FILENAME}...")
    
    if not os.path.exists(SOURCE_IMAGE):
        print("❌ Error: Source image not found!")
        return False

    with zipfile.ZipFile(ZIP_FILENAME, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
        # 1. Manifest
        zipf.writestr('manifest.json', '{"session_id": "'+TEST_SESSION_ID+'", "timestamp": "2026-01-06T12:00:00Z", "assets_count": 25}')
        
        # 2. Add 25 Images
        for i in range(1, 26):
            img_name = f"evidence_{i:02d}.jpg"
            zipf.write(SOURCE_IMAGE, img_name)
            
    size_mb = os.path.getsize(ZIP_FILENAME) / (1024 * 1024)
    print(f"[OK] Package created. Size: {size_mb:.2f} MB")
    return True

def upload_heavy_package():
    print(f"\n[INFO] Sending Heavy Package to {BASE_URL}...")
    
    # REQUIRED HEADER
    headers = {'session-id': TEST_SESSION_ID}
    
    try:
        start_time = time.time()
        with open(ZIP_FILENAME, 'rb') as f:
            files = {'file': (ZIP_FILENAME, f)}
            response = requests.post(BASE_URL, files=files, headers=headers)
            
        duration = time.time() - start_time
        print(f"[STATUS] Status Code: {response.status_code}")
        print(f"[TIME] Time Taken: {duration:.2f} seconds")
        print(f"[RESPONSE] Response: {response.text}")
        
        if response.status_code == 200:
            print("[SUCCESS] Heavy package uploaded.")
        elif response.status_code == 422:
            print("[FAILURE] Validation Error (Did you fix the header?).")
        else:
            print(f"[WARN] UNEXPECTED: {response.status_code}")
            
    except Exception as e:
        print(f"[ERROR] Connection Error: {e}")

if __name__ == "__main__":
    if create_heavy_zip():
        upload_heavy_package()

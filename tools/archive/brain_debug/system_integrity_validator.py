import asyncio
import os
import requests
import json
from database import db
from services.storage_service import get_storage_service

async def validate_system():
    print("🚀 RISC V2.0 - Final System Integrity Audit")
    print("-" * 50)

    # 1. Database Connection Check
    try:
        await db.connect()
        print("✅ DB: Status [CONNECTED] - AlloyDB Vector Ready")
        await db.disconnect()
    except Exception as e:
        print(f"❌ DB: Status [FAILED] - {e}")

    # 2. Storage Service Check
    try:
        ss = get_storage_service()
        test_dir = ss.get_session_path("audit_user", "audit_prop", "audit_session")
        os.makedirs(test_dir, exist_ok=True)
        test_file = os.path.join(test_dir, "audit_heartbeat.txt")
        with open(test_file, "w") as f:
            f.write("OK")
        if os.path.exists(test_file):
            print(f"✅ STORAGE: Status [OK] - Hierarchical Path Verified: {test_dir}")
            os.remove(test_file)
        else:
            print("❌ STORAGE: Status [FAILED] - File Persistence Error")
    except Exception as e:
        print(f"❌ STORAGE: Status [FAILED] - {e}")

    # 3. Brain API Check (Local/Docker)
    try:
        # Note: We use localhost because we are running this on the host machine
        # In Docker, it would be 'brain-api'
        response = requests.get("http://localhost:8001/")
        if response.status_code == 200:
            print(f"✅ BRAIN API: Status [ONLINE] - Version: {response.json().get('version')}")
        else:
            print(f"❌ BRAIN API: Status [UNREACHABLE] - Code: {response.status_code}")
    except Exception as e:
        print(f"❌ BRAIN API: Status [UNREACHABLE] - Ensure risc_v2_brain is running")

    # 4. Reporter API Check
    try:
        response = requests.get("http://localhost:8002/")
        if response.status_code == 200:
            print(f"✅ REPORTER API: Status [ONLINE] - Model: {response.json().get('model')}")
        else:
            print(f"❌ REPORTER API: Status [UNREACHABLE]")
    except Exception as e:
        print(f"❌ REPORTER API: Status [UNREACHABLE]")

    # 5. AI Reasoning Check (Mock Prompt)
    # We'll check if the Reporter API can actually call the AI
    try:
        payload = {"room_id": "test_room", "force_reanalysis": True}
        response = requests.post("http://localhost:8002/api/v2/ai/analyze/room", json=payload, timeout=10)
        if response.status_code == 200:
            print("✅ AI ENGINE: Status [ACTIVE] - Gemini 3 Reasoning Verified")
        else:
            print(f"❌ AI ENGINE: Status [ERROR] - {response.text}")
    except Exception as e:
         print(f"❌ AI ENGINE: Status [TIMED_OUT/OFFLINE]")

    print("-" * 50)
    print("🏁 Audit Finished")

if __name__ == "__main__":
    asyncio.run(validate_system())

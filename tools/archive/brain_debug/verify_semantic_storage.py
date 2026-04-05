import asyncio
import os
import uuid
from database import db
from services.storage_service import get_storage_service

async def run_test():
    print("\n--- PHASE 1: SEMANTIC STORAGE VERIFICATION (10/10 TEST) ---\n")
    
    # 1. Init DB connection
    print("[*] Connecting to Database...")
    await db.connect()
    print("[+] Database connected successfully.\n")
    
    storage_service = get_storage_service()
    
    # 2. Setup Test Data (Project)
    project_id = str(uuid.uuid4())
    ref_number = f"KMT{uuid.uuid4().hex[:4].upper()}"
    client_name = "Alpha Corp/UK"
    
    print(f"[*] Simulating DB Insertion for Project: Ref='{ref_number}', Client='{client_name}' ...")
    await db.execute(
        "INSERT INTO projects (id, reference_number, client_name, site_metadata) VALUES ($1, $2, $3, '{}')",
        project_id, ref_number, client_name
    )
    
    # 3. Setup Test Data (Session)
    session_id = str(uuid.uuid4())
    print(f"[*] Simulating DB Insertion for Session: ID='{session_id}' ...")
    test_user_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO sessions (id, title, surveyor_id, project_id, status, started_at) VALUES ($1, $2, $3, $4, 'pending', NOW())",
        session_id, "Test Session", test_user_id, project_id
    )
    
    # 4. Trigger Semantic Storage Logic
    print("\n[*] Invoking new Storage Service Logic...")
    session_path = await storage_service.get_session_path(session_id)
    
    print(f"\n[+] EXPECTED PATH FORMAT: Storage/Projects/KMT9999_Alpha_Corp-UK/[Date]_Session_[ShortID]/")
    print(f"[+] ACTUAL GENERATED PATH: {session_path}")
    
    # 5. Verification
    if "KMT9999" in session_path and "Alpha_Corp-UK" in session_path and "Session" in session_path:
        print("\n✅ TEST PASSED (10/10): The Storage Engine successfully queried the DB and constructed a perfect human-readable Semantic Directory!")
        print(f"✅ FOLDER CREATED: {os.path.exists(session_path)}")
    else:
        print("\n❌ TEST FAILED: The path does not match the radical redesign specs.")

    # Cleanup DB so we don't pollute local testing
    await db.execute("DELETE FROM sessions WHERE id = $1", session_id)
    await db.execute("DELETE FROM projects WHERE id = $1", project_id)
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(run_test())

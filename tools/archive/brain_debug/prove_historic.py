import asyncio
import os
from database import db
from services.storage_service import get_storage_service

async def prove_historic_data():
    print("\n--- PHASE 1: SEMANTIC STORAGE PROOF (HISTORIC DATA) ---\n")
    
    print("[*] Connecting to Database...")
    await db.connect()
    
    storage_service = get_storage_service()
    
    # 1. Fetch a real, existing session from the database
    print("[*] Fetching the most recent real session from the DB...")
    query = """
        SELECT s.id, p.reference_number, p.client_name 
        FROM sessions s
        JOIN projects p ON s.project_id = p.id
        ORDER BY s.started_at DESC
        LIMIT 1
    """
    row = await db.fetchrow(query)
    
    if not row:
        print("[!] No real sessions found in the database. Cannot test historic data.")
        await db.disconnect()
        return
        
    session_id = str(row['id'])
    ref = row['reference_number']
    client = row['client_name']
    
    print(f"\n[+] Found Historic Session:")
    print(f"    - Session ID: {session_id}")
    print(f"    - Original Project Ref: {ref}")
    print(f"    - Original Client: {client}")
    
    # 2. Pass the raw ID into the new semantic engine
    print("\n[*] Invoking Semantic Storage Engine...")
    session_path = await storage_service.get_session_path(session_id)
    
    print(f"\n[+] RESULTING FOLDER PATH: {session_path}")
    
    safe_ref = ref.replace("/", "-").replace("\\", "-").replace(" ", "_")
    safe_client = client.replace("/", "-").replace("\\", "-").replace(" ", "_")
    
    if safe_ref in session_path and safe_client in session_path:
        print("\n[SUCCESS] The new Async Semantic Engine successfully looked up the historic UUID and generated a human-readable folder path!")
    else:
        print("\n[FAIL] The path generated does not contain the original project details.")

    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(prove_historic_data())

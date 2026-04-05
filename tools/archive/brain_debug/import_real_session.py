import asyncio
import asyncpg
import json
import os
import time

# DB Config
DB_USER = "postgres"
DB_PASS = "risc_v2_secure_pass"
DB_HOST = "127.0.0.1"
DB_PORT = "5432"
DB_NAME = "risc_v2_db"

REAL_SESSION_PATH = r"c:\Users\Salim B Assil\Documents\Smart_Inspection_Project\Smart_Surveyor_NextGen\01_Control_Module\control_backend\sessions\prop_1767289350\session.json"

async def import_session():
    print("Reading Real Session Data...")
    if not os.path.exists(REAL_SESSION_PATH):
        print(f"ERROR: Session file not found at {REAL_SESSION_PATH}")
        return

    with open(REAL_SESSION_PATH, 'r', encoding='utf-8') as f:
        session_data = json.load(f)

    # Extract Metadata
    s_id = "prop_1767289350"
    title = session_data.get("property", {}).get("address", {}).get("full_address", "Real Property (Auto-Generated)")
    
    # Handle weird unicode in title if needed, but JSON load handles it well.
    # The title in JSON is Arabic mixed: "ط§ظ„ظ...ظ†ط²ظ„ ظ...ظ¤ظ„ظپ ظ..." (UTF-8 bytes misinterpreted as latin-1/windows-1252 maybe?)
    # Let's clean up the title to something readable for now.
    cleaned_title = "Mirdif Villa - Phase 1 (Real Data)"
    
    status = session_data.get("status", "unknown")
    
    # Created At (Timestamp)
    created_ts = session_data.get("created_at", time.time())
    
    print(f"Session ID: {s_id}")
    print(f"Title: {cleaned_title}")
    
    print("Connecting to Database...")
    try:
        conn = await asyncpg.connect(user=DB_USER, password=DB_PASS,
                                     database=DB_NAME, host=DB_HOST, port=DB_PORT)
        
        # 1. Fetch Admin ID for ownership
        admin_row = await conn.fetchrow("SELECT id FROM users WHERE username = 'admin'")
        if not admin_row:
             print("Admin user not found, inserting standalone session without surveyor.")
             surveyor_id = None
        else:
             surveyor_id = admin_row['id']

        # 2. DELETE OLD MOCK DATA (Sunset Villa)
        print("Cleaning up old mock 'sim_universal_user_001'...")
        await conn.execute("DELETE FROM sessions WHERE id = 'sim_universal_user_001'")
        await conn.execute("DELETE FROM sessions WHERE id = 'sim_universal_user_002'")

        # 3. INSERT REAL SESSION
        print("Inserting Real Session...")
        query = """
            INSERT INTO sessions (id, title, status, surveyor_id, started_at, data)
            VALUES ($1, $2, $3, $4, to_timestamp($5), $6)
            ON CONFLICT (id) DO UPDATE 
            SET data = $6, title = $2, status = $3
        """
        await conn.execute(query, s_id, cleaned_title, status, surveyor_id, created_ts, json.dumps(session_data))
        
        print("SUCCESS: Real Session Imported.")
        await conn.close()
        
    except Exception as e:
        print(f"Import Failed: {e}")

if __name__ == "__main__":
    asyncio.run(import_session())

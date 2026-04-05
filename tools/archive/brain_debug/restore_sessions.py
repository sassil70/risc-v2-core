import asyncio
import asyncpg
import json
import os
import time
from pathlib import Path

# DB Config (Internal Docker Defaults)
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASSWORD", "risc_v2_secure_pass")
DB_HOST = os.getenv("DB_HOST", "alloydb")
DB_NAME = os.getenv("DB_NAME", "risc_v2_db")
DB_PORT = os.getenv("DB_PORT", "5432")

STORAGE_PATH = "/app/storage/sessions"

async def restore_sessions():
    print(f"🔄 Starting Verification & Restoration Scan...")
    print(f"📁 Scanning Storage: {STORAGE_PATH}")
    
    if not os.path.exists(STORAGE_PATH):
        print(f"❌ Error: Storage path {STORAGE_PATH} not found.")
        return

    # 1. Connect to DB
    try:
        conn = await asyncpg.connect(user=DB_USER, password=DB_PASS, database=DB_NAME, host=DB_HOST, port=DB_PORT)
        print("✅ Database Connected")
        
        # 1.5 Ensure Schema Exists (Fixing missing/wrong init.sql)
        print("🛠️ Verifying Schema...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT,
                status TEXT,
                started_at TIMESTAMP WITH TIME ZONE,
                data JSONB,
                surveyor_id TEXT,
                project_id TEXT
            );
        """)
    except Exception as e:
        print(f"❌ DB Connection/Schema Error: {e}")
        return

    # 2. Scan Folders
    restored_count = 0
    sessions_found = [f for f in os.scandir(STORAGE_PATH) if f.is_dir()]
    
    print(f"🔎 Found {len(sessions_found)} potential session folders.")

    for entry in sessions_found:
        s_id = entry.name
        folder_path = Path(entry.path)
        
        # Try to find metadata
        meta_file = folder_path / "session.json"
        if not meta_file.exists():
            meta_file = folder_path / "session_init.json"
            
        if not meta_file.exists():
            # Skip empty/junk folders
            continue
            
        try:
            with open(meta_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"⚠️ Skipped {s_id}: Invalid JSON ({e})")
            continue

        # Extract Fields
        # Title: Try multiple sources
        candidate_title = data.get("title") or \
                          data.get("property", {}).get("address", {}).get("full_address") or \
                          data.get("address")
        
        if isinstance(candidate_title, dict):
            # If address is a dict, format it nicely
            title = f"{candidate_title.get('street', 'Unknown St')}, {candidate_title.get('postcode', '')}"
        elif isinstance(candidate_title, str):
            title = candidate_title
        else:
            title = f"Recovered Session {s_id[:8]}"
        
        # Status
        status = data.get("status", "pending")
        
        # Timestamp
        started_at = data.get("created_at") or data.get("started_at") or time.time()
        
        # Ensure ID matches folder (SSOT)
        data['id'] = s_id
        
        # 3. UPSERT into DB
        query = """
            INSERT INTO sessions (id, title, status, started_at, data, surveyor_id)
            VALUES ($1, $2, $3, to_timestamp($4), $5, NULL)
            ON CONFLICT (id) DO UPDATE 
            SET title = $2, status = $3, data = $5
            RETURNING id
        """
        
        try:
            # Handle timestamp if it's explicitly ISO format string, but simpler to rely on float/int if available.
            # If started_at is string iso, to_timestamp might fail if we pass string.
            # Let's simple-cast if it looks like a float/int, else use NOW() if strictly necessary, 
            # but let's assume it's a float timestamp from previous systems.
            
            ts_val = 0.0
            if isinstance(started_at, (int, float)):
                 ts_val = float(started_at)
            else:
                 ts_val = time.time() # Fallback
            
            await conn.execute(query, s_id, title, status, ts_val, json.dumps(data))
            # print(f"   RESTORED: {title[:30]}...")
            restored_count += 1
            
        except Exception as e:
            print(f"❌ Failed to insert {s_id}: {e}")

    await conn.close()
    print("-" * 50)
    print(f"🎉 Restoration Complete: {restored_count} sessions imported.")

if __name__ == "__main__":
    asyncio.run(restore_sessions())

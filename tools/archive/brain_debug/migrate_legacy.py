import os
import asyncio
import uuid
from datetime import datetime
from database import Database

# Path to sessions storage (Inside Container)
STORAGE_ROOT = "/app/storage/sessions"

async def migrate():
    print("🚀 Starting Legacy Migration (Disk -> DB)...")
    
    # 1. Connect
    db = Database()
    try:
        await db.connect()
        print("✅ DB Connected.")
    except Exception as e:
        print(f"❌ DB Connection Failed: {e}")
        return

    # 2. Get User (Sassil)
    user = await db.fetchrow("SELECT id FROM users WHERE username = 'sassil'")
    if not user:
        print("❌ User 'sassil' not found. Run init.sql first.")
        return
    user_id = user['id']
    print(f"👤 Found User: sassil ({user_id})")

    # 3. Get or Create Legacy Project
    project = await db.fetchrow("SELECT id FROM projects WHERE client_name = 'Legacy Import'")
    if not project:
        print("🛠️ Creating 'Legacy Import' Project...")
        project_id = str(uuid.uuid4())
        await db.execute(
            "INSERT INTO projects (id, reference_number, client_name) VALUES ($1, 'LEGACY-001', 'Legacy Import')",
            project_id
        )
    else:
        project_id = project['id']
    print(f"wb️ Project Context: {project_id}")

    # 4. Scan Disk
    if not os.path.exists(STORAGE_ROOT):
        print(f"❌ Storage path not found: {STORAGE_ROOT}")
        return

    folders = [f for f in os.listdir(STORAGE_ROOT) if os.path.isdir(os.path.join(STORAGE_ROOT, f))]
    print(f"📂 Found {len(folders)} folders on disk.")

    count = 0
    for folder_name in folders:
        # Validate UUID
        try:
            session_uuid = str(uuid.UUID(folder_name))
        except ValueError:
            print(f"⚠️ Skipping non-UUID folder: {folder_name}")
            continue

        # Check if exists in DB
        exists = await db.fetchrow("SELECT id FROM sessions WHERE id = $1", session_uuid)
        if exists:
            # Update connection if missing
            await db.execute("UPDATE sessions SET surveyor_id = $1 WHERE id = $2 AND surveyor_id IS NULL", user_id, session_uuid)
            print(f"🔄 Updated existing session: {folder_name}")
        else:
            # Insert New
            folder_path = os.path.join(STORAGE_ROOT, folder_name)
            has_floor_plan = os.path.exists(os.path.join(folder_path, "floor_plan.jpg"))
            status = 'completed' if has_floor_plan else 'in_progress'
            
            # Use file date as started_at
            try:
                stat = os.stat(folder_path)
                started_at = datetime.fromtimestamp(stat.st_ctime)
            except:
                started_at = datetime.now()

            await db.execute(
                """
                INSERT INTO sessions (id, project_id, surveyor_id, started_at, status)
                VALUES ($1, $2, $3, $4, $5)
                """,
                session_uuid, project_id, user_id, started_at, status
            )
            print(f"➕ Imported Session: {folder_name} (Status: {status})")
            count += 1

    print(f"✅ Migration Complete. Imported {count} sessions.")
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(migrate())

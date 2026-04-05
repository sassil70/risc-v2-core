import asyncio
import json
from db.database import db

async def test():
    await db.connect()
    
    # Let us query the craher project
    pid = "5d1f84b1-7a66-4126-9c15-adce3bf8acfc"
    row = await db.fetchrow("SELECT site_metadata FROM projects WHERE id = $1", pid)
    print("BEFORE UPDATE:", row["site_metadata"])
    
    metadata = json.loads(row["site_metadata"]) if isinstance(row["site_metadata"], str) else row["site_metadata"]
    if not metadata: metadata = {}
    metadata["rooms"] = [{"test": "room"}]
    
    try:
        await db.execute("UPDATE projects SET site_metadata = $1 WHERE id = $2", json.dumps(metadata), pid)
        print("UPDATE EXECUTED WITHOUT CAST! (This should theoretically fail or do something weird)")
    except Exception as e:
        print("UPDATE EXCEPTION (No Cast):", e)
        
    row2 = await db.fetchrow("SELECT site_metadata FROM projects WHERE id = $1", pid)
    print("AFTER FIRST UPDATE:", row2["site_metadata"])

    try:
        await db.execute("UPDATE projects SET site_metadata = $1::jsonb WHERE id = $2", json.dumps(metadata), pid)
        print("UPDATE EXECUTED WITH CAST!")
    except Exception as e:
        print("UPDATE EXCEPTION (With Cast):", e)
        
    row3 = await db.fetchrow("SELECT site_metadata FROM projects WHERE id = $1", pid)
    print("AFTER SECOND UPDATE:", row3["site_metadata"])
    
    await db.disconnect()

asyncio.run(test())

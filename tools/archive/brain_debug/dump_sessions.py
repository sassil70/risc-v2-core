import asyncio
import asyncpg
import json

# DB Config
DB_USER = "postgres"
DB_PASS = "mysecretpassword"
DB_HOST = "127.0.0.1"
DB_PORT = "5432"
DB_NAME = "risc_v2_db"

async def list_sessions():
    print("Connecting to Database...")
    try:
        conn = await asyncpg.connect(user=DB_USER, password=DB_PASS,
                                     database=DB_NAME, host=DB_HOST, port=DB_PORT)
        
        rows = await conn.fetch("SELECT id, title, started_at FROM sessions ORDER BY started_at DESC LIMIT 50")
        
        print(f"Found {len(rows)} sessions:")
        for r in rows:
            print(f"ID: {r['id']} | Title: {r['title']} | Date: {r['started_at']}")
            
        await conn.close()
    except Exception as e:
        print(f"Query Failed: {e}")

if __name__ == "__main__":
    asyncio.run(list_sessions())

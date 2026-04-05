import asyncio
import asyncpg
import json

# DB Config
DB_USER = "postgres"
DB_PASS = "mysecretpassword"
DB_HOST = "127.0.0.1"
DB_PORT = "5432"
DB_NAME = "risc_v2_db"

async def check_session():
    print("Connecting to Database...")
    try:
        conn = await asyncpg.connect(user=DB_USER, password=DB_PASS,
                                     database=DB_NAME, host=DB_HOST, port=DB_PORT)
        
        print("Checking for 'prop_1767289350'...")
        row = await conn.fetchrow("SELECT id, title, data FROM sessions WHERE id = 'prop_1767289350'")
        
        if row:
            print(f"FOUND: {row['id']}")
            print(f"Title: {row['title']}")
            if row['data']:
                print("Data Column: Present (JSONB)")
            else:
                print("Data Column: NULL")
        else:
            print("NOT FOUND via Exact Match.")
            
            # Fuzzy check
            rows = await conn.fetch("SELECT id FROM sessions")
            print(f"All Session IDs in DB: {[r['id'] for r in rows]}")
        
        await conn.close()
    except Exception as e:
        print(f"Check Failed: {e}")

if __name__ == "__main__":
    asyncio.run(check_session())

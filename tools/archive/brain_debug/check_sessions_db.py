import asyncio
import asyncpg
import os

# DB Config (matching .env)
DB_USER = "postgres"
DB_PASS = "risc2026" # Or use the password from your .env if different
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "risc_v2_db"

async def check_sessions():
    try:
        conn = await asyncpg.connect(user=DB_USER, password='mysecretpassword',
                                     database=DB_NAME, host='127.0.0.1', port=DB_PORT)
        
        # Check Sessions Table
        rows = await conn.fetch("SELECT * FROM sessions")
        print(f"Total Sessions: {len(rows)}")
        for row in rows:
            print(f" - ID: {row['id']} | Title: {row['title']} | Status: {row['status']}")
            
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_sessions())

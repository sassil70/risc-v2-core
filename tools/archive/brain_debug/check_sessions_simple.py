import asyncio
import asyncpg
import os

# DB Config from .env
DB_USER = "postgres"
DB_PASS = "mysecretpassword" 
DB_HOST = "127.0.0.1"
DB_PORT = "5432"
DB_NAME = "risc_v2_db"

async def check_sessions():
    print("Connecting to database...")
    try:
        conn = await asyncpg.connect(user=DB_USER, password=DB_PASS,
                                     database=DB_NAME, host=DB_HOST, port=DB_PORT)
        
        # Check Sessions Table
        print("Querying sessions table...")
        rows = await conn.fetch("SELECT * FROM sessions")
        
        print(f"Total Sessions Found: {len(rows)}")
        print("-" * 30)
        
        if len(rows) == 0:
            print("No sessions found in the database.")
        else:
            for row in rows:
                # Handle potential None values safely
                s_id = str(row['id'])
                title = row['title'] if row['title'] else "Untitled"
                status = row['status'] if row['status'] else "Unknown"
                print(f"ID: {s_id}")
                print(f"Title: {title}")
                print(f"Status: {status}")
                print("-" * 15)
            
        await conn.close()
        print("Database connection closed.")
        
    except Exception as e:
        print(f"Critical Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_sessions())

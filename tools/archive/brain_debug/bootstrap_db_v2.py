import asyncio
import asyncpg
import os

# DB Config
DB_USER = "postgres"
DB_PASS = "mysecretpassword"
DB_HOST = "127.0.0.1"
DB_PORT = "5432"
DB_NAME = "risc_v2_db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    id VARCHAR(50) PRIMARY KEY,
    title VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    project_id VARCHAR(50),
    surveyor_id UUID REFERENCES users(id) -- Link to real user
);
"""

async def bootstrap():
    print("Connecting to Database...")
    try:
        conn = await asyncpg.connect(user=DB_USER, password=DB_PASS,
                                     database=DB_NAME, host=DB_HOST, port=DB_PORT)
        
        # 1. Fetch Admin ID
        print("Fetching Admin User...")
        admin_row = await conn.fetchrow("SELECT id FROM users WHERE username = 'admin'")
        if not admin_row:
            print("ERROR: Admin user 'admin' not found. Please run seed_auth.py first.")
            return
        
        admin_id = admin_row['id']
        print(f"Admin ID: {admin_id}")

        # 2. Reset & Create Schema
        print("Resetting Sessions Table...")
        await conn.execute("DROP TABLE IF EXISTS sessions CASCADE")
        await conn.execute(SCHEMA_SQL)
        print("Table 'sessions' created.")

        # 3. Insert Real Data (Simulated Session)
        print("Injecting Session: Sunset Villa Estate...")
        await conn.execute("""
            INSERT INTO sessions (id, title, status, surveyor_id, started_at)
            VALUES ($1, $2, 'completed', $3, NOW())
        """, "sim_universal_user_001", "Sunset Villa Estate", admin_id)
        
        # 4. Insert Use Case 2 (Horizon Tower)
        await conn.execute("""
            INSERT INTO sessions (id, title, status, surveyor_id, started_at)
            VALUES ($1, $2, 'in_progress', $3, NOW())
        """, "sim_universal_user_002", "Horizon Tower Apt 4B", admin_id)

        print("SUCCESS: Database Bootstrapped & Data Injected.")
        await conn.close()
        
    except Exception as e:
        print(f"Bootstrap Failed: {e}")

if __name__ == "__main__":
    asyncio.run(bootstrap())

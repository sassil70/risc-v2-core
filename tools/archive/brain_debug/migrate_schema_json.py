import asyncio
import asyncpg

# DB Config
DB_USER = "postgres"
DB_PASS = "mysecretpassword"
DB_HOST = "127.0.0.1"
DB_PORT = "5432"
DB_NAME = "risc_v2_db"

async def migrate_schema():
    print("Connecting to Database...")
    try:
        conn = await asyncpg.connect(user=DB_USER, password=DB_PASS,
                                     database=DB_NAME, host=DB_HOST, port=DB_PORT)
        
        print("Adding 'data' JSONB column to 'sessions' table...")
        await conn.execute("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS data JSONB")
        
        print("SUCCESS: Schema Updated.")
        await conn.close()
    except Exception as e:
        print(f"Migration Failed: {e}")

if __name__ == "__main__":
    asyncio.run(migrate_schema())

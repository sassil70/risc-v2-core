import asyncio
import asyncpg
import os

async def test_conn():
    user = "postgres"
    password = "risc_v2_secure_pass"
    database = "risc_v2_db"
    
    print(f"Testing IPv4 (127.0.0.1)...")
    try:
        conn = await asyncpg.connect(user=user, password=password, database=database, host="127.0.0.1")
        print("[SUCCESS] Connected to 127.0.0.1")
        await conn.close()
    except Exception as e:
        print(f"[FAIL] 127.0.0.1: {e}")

    print(f"\nTesting localhost...")
    try:
        conn = await asyncpg.connect(user=user, password=password, database=database, host="localhost")
        print("[SUCCESS] Connected to localhost")
        await conn.close()
    except Exception as e:
        print(f"[FAIL] localhost: {e}")

if __name__ == "__main__":
    asyncio.run(test_conn())

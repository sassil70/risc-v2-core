import os
import asyncpg
from typing import Optional

class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        try:
            # Fallback values match docker-compose.yml
            self.pool = await asyncpg.create_pool(
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", "risc_v2_secure_pass"),
                database=os.getenv("DB_NAME", "risc_v2_db"),
                host=os.getenv("DB_HOST", "localhost"),
                port=os.getenv("DB_PORT", "5432"),
                timeout=5 # Short timeout for fail-fast
            )
            print("[SUCCESS] Database Connected")
        except Exception as e:
            print(f"[WARN] Database Connection Failed: {e}. Running in OFFLINE MODE.")
            self.pool = None

    async def disconnect(self):
        if self.pool:
            await self.pool.close()

    async def execute(self, query: str, *args):
        if not self.pool: raise Exception("Database Offline Mode")
        async with self.pool.acquire() as connection:
            return await connection.execute(query, *args)

    async def fetchrow(self, query: str, *args):
        if not self.pool: raise Exception("Database Offline Mode")
        async with self.pool.acquire() as connection:
            return await connection.fetchrow(query, *args)

    async def fetch(self, query: str, *args):
        if not self.pool: raise Exception("Database Offline Mode")
        async with self.pool.acquire() as connection:
            return await connection.fetch(query, *args)

    async def fetchval(self, query: str, *args):
        if not self.pool: raise Exception("Database Offline Mode")
        async with self.pool.acquire() as connection:
            return await connection.fetchval(query, *args)

db = Database()

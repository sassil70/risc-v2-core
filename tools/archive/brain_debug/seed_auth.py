import asyncio
import os
import asyncpg
from database import db
from core.security import get_password_hash

async def seed():
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "5432")
    user = os.getenv("DB_USER", "postgres")
    password = "risc_v2_secure_pass"
    
    # 0. Create Database if strictly necessary
    print("   [INFO] Checking Database existence...")
    conn = await asyncpg.connect(user=user, password=password, database="postgres", host=host, port=port)
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname='risc_v2_db'")
        if not exists:
            print("   [WARN] Database 'risc_v2_db' not found. Creating...")
            await conn.execute('CREATE DATABASE risc_v2_db')
            print("   [OK] Database Created.")
        else:
            print("   [OK] Database 'risc_v2_db' exists.")
    finally:
        await conn.close()

    print(f"[INFO] Connecting to {user}@{host}:{port}/risc_v2_db...")
    await db.connect()

    # 1. Enable Extensions (IMPORTANT for UUID)
    await db.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # 2. Create Users Table
    print("   Checking 'users' table...")
    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(100),
            role VARCHAR(20) DEFAULT 'surveyor',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)

    # 3. Check for Admin
    admin_user = "admin"
    admin_pass = "risc2026"
    # admin_hash = get_password_hash(admin_pass)
    # Bypass passlib issue: Hash for 'risc2026' generated via pure bcrypt
    admin_hash = "$2b$12$jcEzfOyhfrCNyEAwx/8KPOhJ2vgDh7QZ5xtPdVswAYd5WHNFkaEMu"

    existing = await db.fetchrow("SELECT * FROM users WHERE username = $1", admin_user)
    
    if not existing:
        print(f"   Creating Default User: {admin_user}")
        await db.execute("""
            INSERT INTO users (username, password_hash, full_name, role)
            VALUES ($1, $2, 'System Administrator', 'admin')
        """, admin_user, admin_hash)
        print("   [OK] User Created Successfully")
    else:
        print("   [OK] User 'admin' already exists")
        # Optional: Update password to ensure it matches known default
        await db.execute("UPDATE users SET password_hash = $1 WHERE username = $2", admin_hash, admin_user)
        print("   [INFO] Password Reset to Default")

    await db.disconnect()
    print("[DONE] Seed Complete.")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(seed())

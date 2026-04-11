from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import db
from core.security import verify_password, create_access_token, get_password_hash

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(creds: LoginRequest):
    """Authenticate user against PostgreSQL users table."""
    username_clean = creds.username.strip()

    # 1. Fetch User by Username (Case Insensitive)
    query = "SELECT id, username, password_hash, full_name, role FROM users WHERE LOWER(username) = LOWER($1)"
    user = await db.fetchrow(query, username_clean)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # 2. Verify Password (bcrypt)
    if not verify_password(creds.password, user['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # 3. Success — Create JWT Token
    token = create_access_token(data={"sub": str(user['id']), "role": user['role']})

    # 4. Log Success Event
    try:
        await db.execute(
            "INSERT INTO access_events (user_id, event_type, metadata) VALUES ($1, $2, $3)",
            user['id'], 'LOGIN_SUCCESS', '{"source": "mobile"}'
        )
    except Exception as e:
        print(f"Audit Log Error: {e}")

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user['id']),
            "username": user['username'],
            "full_name": user['full_name'],
            "role": user['role']
        }
    }


@router.post("/seed")
async def seed_users():
    """Create default demo users for Apple App Review and testing.
    Safe to call multiple times — uses ON CONFLICT DO NOTHING."""
    try:
        # Ensure tables exist
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                username VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(200),
                role VARCHAR(50) DEFAULT 'surveyor',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS access_events (
                id BIGSERIAL PRIMARY KEY,
                user_id UUID NOT NULL,
                event_type VARCHAR(50) NOT NULL,
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)

        # Hash passwords
        demo_password_hash = get_password_hash("demo1234")
        admin_password_hash = get_password_hash("risc2026")
        surveyor_password_hash = get_password_hash("risc2026")

        # Insert demo users
        await db.execute("""
            INSERT INTO users (username, password_hash, full_name, role)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (username) DO NOTHING
        """, "demo", demo_password_hash, "Apple Review Demo Account", "surveyor")

        await db.execute("""
            INSERT INTO users (username, password_hash, full_name, role)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (username) DO NOTHING
        """, "admin", admin_password_hash, "System Administrator", "admin")

        await db.execute("""
            INSERT INTO users (username, password_hash, full_name, role)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (username) DO NOTHING
        """, "surveyor", surveyor_password_hash, "RICS Surveyor", "surveyor")

        # Verify
        count = await db.fetchval("SELECT COUNT(*) FROM users")
        return {"status": "success", "message": f"Seed complete. Total users: {count}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Seed failed: {str(e)}")

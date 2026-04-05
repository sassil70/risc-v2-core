from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import db
from core.security import verify_password, create_access_token

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

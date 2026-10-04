from datetime import datetime, timedelta, timezone
import jwt
from jwt import PyJWTError
from bcrypt import hashpw, gensalt, checkpw
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings
from app.database import get_db

ALGORITHM = "HS256"
bearer_scheme = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    return hashpw(password.encode(), gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return checkpw(password.encode(), hashed.encode())

def create_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db=Depends(get_db),
) -> int:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        payload = jwt.decode(
            credentials.credentials, settings.secret_key, algorithms=[ALGORITHM]
        )
        user_id = int(payload["sub"])
        cursor = await db.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except (PyJWTError, KeyError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token") from None

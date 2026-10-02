import asyncio
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from app.auth import hash_password, verify_password, create_token, get_current_user
from app.database import get_db
from app.rate_limit import auth_allowed

router = APIRouter(prefix="/api/auth", tags=["auth"])

_DUMMY_HASH = hash_password("timing-safe-dummy")


def _normalize_email(value: str) -> str:
    return value.strip().lower()


class SignupRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=8)
    name: str = ""

    @field_validator("email")
    @classmethod
    def email_normalized(cls, value: str) -> str:
        return _normalize_email(value)


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def email_normalized(cls, value: str) -> str:
        return _normalize_email(value)


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    efka_category: int = 1
    years_active: int = 1
    charges_vat: bool = False


class ProfileUpdate(BaseModel):
    efka_category: int | None = Field(default=None, ge=1, le=6)
    years_active: int | None = Field(default=None, ge=1, le=50)
    name: str | None = None
    charges_vat: bool | None = None


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


def _user_from_row(row) -> UserResponse:
    return UserResponse(
        id=row["id"],
        email=row["email"],
        name=row["name"],
        efka_category=row["efka_category"] if "efka_category" in row.keys() else 1,
        years_active=row["years_active"] if "years_active" in row.keys() else 1,
        charges_vat=bool(row["charges_vat"]) if "charges_vat" in row.keys() else False,
    )


@router.post("/signup")
async def signup(req: SignupRequest, db=Depends(get_db)):
    if not auth_allowed(f"signup:{req.email}"):
        raise HTTPException(status_code=429, detail="Too many attempts")
    cursor = await db.execute("SELECT id FROM users WHERE email = ?", (req.email,))
    if await cursor.fetchone():
        raise HTTPException(status_code=400, detail="Registration failed")
    hashed = await asyncio.to_thread(hash_password, req.password)
    cursor = await db.execute(
        "INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)",
        (req.email, hashed, req.name),
    )
    await db.commit()
    user_id = cursor.lastrowid
    token = create_token(user_id)
    return AuthResponse(
        token=token,
        user=UserResponse(id=user_id, email=req.email, name=req.name),
    )


@router.post("/login")
async def login(req: LoginRequest, db=Depends(get_db)):
    if not auth_allowed(f"login:{req.email}"):
        raise HTTPException(status_code=429, detail="Too many attempts")
    cursor = await db.execute(
        "SELECT id, email, name, password_hash, efka_category, years_active, charges_vat FROM users WHERE email = ?",
        (req.email,),
    )
    row = await cursor.fetchone()
    if not row:
        await asyncio.to_thread(verify_password, req.password, _DUMMY_HASH)
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not await asyncio.to_thread(verify_password, req.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token(row["id"])
    return AuthResponse(token=token, user=_user_from_row(row))


@router.get("/me")
async def get_me(user_id: int = Depends(get_current_user), db=Depends(get_db)):
    cursor = await db.execute(
        "SELECT id, email, name, efka_category, years_active, charges_vat FROM users WHERE id = ?",
        (user_id,),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_from_row(row)


@router.post("/refresh")
async def refresh(user_id: int = Depends(get_current_user), db=Depends(get_db)):
    cursor = await db.execute(
        "SELECT id, email, name, efka_category, years_active, charges_vat FROM users WHERE id = ?",
        (user_id,),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid token")
    return AuthResponse(token=create_token(user_id), user=_user_from_row(row))


@router.patch("/me")
async def update_me(
    req: ProfileUpdate,
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
    cursor = await db.execute(
        "SELECT id, email, name, efka_category, years_active, charges_vat FROM users WHERE id = ?",
        (user_id,),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    efka_category = req.efka_category if req.efka_category is not None else row["efka_category"]
    years_active = req.years_active if req.years_active is not None else row["years_active"]
    name = req.name if req.name is not None else row["name"]
    charges_vat = row["charges_vat"] if req.charges_vat is None else (1 if req.charges_vat else 0)
    await db.execute(
        "UPDATE users SET efka_category = ?, years_active = ?, name = ?, charges_vat = ? WHERE id = ?",
        (efka_category, years_active, name, charges_vat, user_id),
    )
    await db.commit()
    return UserResponse(
        id=user_id,
        email=row["email"],
        name=name,
        efka_category=efka_category,
        years_active=years_active,
        charges_vat=bool(charges_vat),
    )

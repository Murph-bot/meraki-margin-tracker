from app.auth import hash_password, verify_password, create_token


def test_hash_and_verify():
    hashed = hash_password("hello123")
    assert verify_password("hello123", hashed)
    assert not verify_password("wrong", hashed)


async def test_signup_and_login(db):
    hashed = hash_password("secret123")
    await db.execute(
        "INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)",
        ("test@test.com", hashed, "Test"),
    )
    await db.commit()
    cursor = await db.execute("SELECT id FROM users WHERE email = ?", ("test@test.com",))
    row = await cursor.fetchone()
    assert row is not None
    token = create_token(row["id"])
    assert isinstance(token, str) and len(token) > 20


async def test_signup_login_me_roundtrip(client):
    signup = await client.post(
        "/api/auth/signup",
        json={"email": "ada@example.com", "password": "secret123", "name": "Ada"},
    )
    assert signup.status_code == 200
    body = signup.json()
    assert body["user"]["email"] == "ada@example.com"
    assert body["token"]

    login = await client.post(
        "/api/auth/login",
        json={"email": "ada@example.com", "password": "secret123"},
    )
    assert login.status_code == 200
    token = login.json()["token"]

    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "ada@example.com"
    assert me.json()["name"] == "Ada"


async def test_refresh_issues_new_usable_token(client):
    signup = await client.post(
        "/api/auth/signup",
        json={"email": "refresh@example.com", "password": "secret123", "name": "R"},
    )
    token = signup.json()["token"]
    refreshed = await client.post(
        "/api/auth/refresh",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert refreshed.status_code == 200
    new_token = refreshed.json()["token"]
    assert new_token
    me = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "refresh@example.com"


async def test_refresh_requires_auth(client):
    assert (await client.post("/api/auth/refresh")).status_code == 401


async def test_signup_duplicate_email(client):
    payload = {"email": "dup@example.com", "password": "secret123", "name": "Dup"}
    assert (await client.post("/api/auth/signup", json=payload)).status_code == 200
    duplicate = await client.post("/api/auth/signup", json=payload)
    assert duplicate.status_code == 400


async def test_login_wrong_password(client):
    await client.post(
        "/api/auth/signup",
        json={"email": "wrong@example.com", "password": "secret123", "name": "W"},
    )
    response = await client.post(
        "/api/auth/login",
        json={"email": "wrong@example.com", "password": "nope-nope"},
    )
    assert response.status_code == 401


async def test_me_rejects_invalid_token(client):
    response = await client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401


async def test_signup_normalizes_email(client):
    response = await client.post(
        "/api/auth/signup",
        json={"email": "  Ada@Example.COM ", "password": "secret123", "name": "Ada"},
    )
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "ada@example.com"


async def test_signup_rejects_short_password(client):
    response = await client.post(
        "/api/auth/signup",
        json={"email": "short@example.com", "password": "123", "name": "S"},
    )
    assert response.status_code == 422


async def test_token_without_sub_is_401_not_500(client):
    from datetime import datetime, timedelta, timezone

    import jwt as pyjwt

    from app.config import settings

    token = pyjwt.encode(
        {"exp": datetime.now(timezone.utc) + timedelta(minutes=5)}, settings.secret_key, algorithm="HS256"
    )
    r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


async def test_tampered_token_is_401(client):
    from app.auth import create_token

    token = create_token(1)[:-2] + "xx"
    r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401

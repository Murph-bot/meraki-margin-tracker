from app.crypto import encrypt_secret, decrypt_secret


def test_encrypt_roundtrip():
    token = encrypt_secret("sk_test_secret")
    assert token != "sk_test_secret"
    assert decrypt_secret(token) == "sk_test_secret"


def test_encryption_key_is_independent_of_jwt_secret(monkeypatch):
    """Rotating SECRET_KEY (JWT) must not brick stored Stripe keys once ENCRYPTION_KEY is set."""
    from cryptography.fernet import Fernet

    from app.config import settings

    legacy_token = encrypt_secret("sk_test_legacy")  # written before ENCRYPTION_KEY existed
    monkeypatch.setattr(settings, "encryption_key", Fernet.generate_key().decode(), raising=False)
    new_token = encrypt_secret("sk_test_new")
    assert decrypt_secret(legacy_token) == "sk_test_legacy"  # legacy still readable
    monkeypatch.setattr(settings, "secret_key", "rotated-jwt-secret-0123456789abcdef")
    assert decrypt_secret(new_token) == "sk_test_new"  # survives JWT secret rotation


async def test_reencrypt_connections_survives_secret_rotation(db, monkeypatch):
    from cryptography.fernet import Fernet

    from app.config import settings
    from app.scripts.reencrypt_connections import reencrypt_all

    await db.execute("INSERT INTO users (email, password_hash, name) VALUES ('r@x.y', 'h', 'R')")
    await db.execute(
        "INSERT INTO connections (user_id, processor, label, api_key_encrypted) VALUES (1, 'stripe', 'm', ?)",
        (encrypt_secret("sk_test_old"),),
    )
    await db.commit()
    monkeypatch.setattr(settings, "encryption_key", Fernet.generate_key().decode(), raising=False)
    assert await reencrypt_all(db) == 1
    monkeypatch.setattr(settings, "secret_key", "rotated-jwt-secret-0123456789abcdef")
    row = await (await db.execute("SELECT api_key_encrypted FROM connections")).fetchone()
    assert decrypt_secret(row["api_key_encrypted"]) == "sk_test_old"

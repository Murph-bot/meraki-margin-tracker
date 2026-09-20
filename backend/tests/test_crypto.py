from app.crypto import encrypt_secret, decrypt_secret


def test_encrypt_roundtrip():
    token = encrypt_secret("sk_test_secret")
    assert token != "sk_test_secret"
    assert decrypt_secret(token) == "sk_test_secret"

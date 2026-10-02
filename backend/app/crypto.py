import base64
import hashlib

from cryptography.fernet import Fernet, MultiFernet

from app.config import settings


def _legacy_fernet() -> Fernet:
    # Pre-ENCRYPTION_KEY scheme: key derived from the JWT SECRET_KEY.
    digest = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _fernet() -> MultiFernet | Fernet:
    """Encrypt with ENCRYPTION_KEY when set; still decrypt legacy tokens.

    Keeping the Fernet key separate from SECRET_KEY means rotating the JWT
    secret no longer makes every stored Stripe key undecryptable.
    """
    key = getattr(settings, "encryption_key", "") or ""
    if not key:
        return _legacy_fernet()
    return MultiFernet([Fernet(key.encode("utf-8")), _legacy_fernet()])


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")


def rotate_secret(token: str) -> str:
    """Re-encrypt a token under the primary key (ENCRYPTION_KEY when set)."""
    f = _fernet()
    if isinstance(f, MultiFernet):
        return f.rotate(token.encode("utf-8")).decode("utf-8")
    return token

"""Password hashing (PBKDF2-SHA256) and JWT (HS256) using only the Python standard library."""
import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Optional

from app.config import settings

PBKDF2_ITERATIONS = 310_000
REVOKED_TOKEN_IDS = set()   # tokens invalidated by logout (in-memory, fine for a student project)


# ---------- passwords ----------
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        scheme, iterations, salt, expected = stored_hash.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(digest.hex(), expected)
    except (ValueError, TypeError):
        return False


# ---------- JWT ----------
def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(signing_input: str) -> str:
    return _b64(hmac.new(settings.SECRET_KEY.encode(), signing_input.encode(), hashlib.sha256).digest())


def create_access_token(user_id: int, expires_minutes: Optional[int] = None) -> str:
    minutes = settings.TOKEN_EXPIRE_MINUTES if expires_minutes is None else expires_minutes
    now = int(time.time())
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64(json.dumps({"sub": str(user_id), "iat": now, "exp": now + minutes * 60,
                               "jti": secrets.token_hex(8)}).encode())
    return f"{header}.{payload}.{_sign(header + '.' + payload)}"


def decode_token(token: str) -> Optional[dict]:
    """Return the token payload, or None if the token is invalid, tampered with, expired or revoked."""
    try:
        header, payload, signature = token.split(".")
        if not hmac.compare_digest(signature, _sign(f"{header}.{payload}")):
            return None
        data = json.loads(_unb64(payload))
        if data.get("exp", 0) < time.time() or data.get("jti") in REVOKED_TOKEN_IDS:
            return None
        return data
    except (ValueError, TypeError, json.JSONDecodeError):
        return None

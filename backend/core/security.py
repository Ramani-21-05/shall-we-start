"""
core/security.py
────────────────
Production-Grade Password Hashing (passlib + bcrypt) and JWT Access Token Handling (PyJWT).
"""

import os
import datetime
import jwt
import hashlib
import bcrypt

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "pharmacast-super-secret-production-key-2026-xyz!")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


def hash_password(password: str) -> str:
    """Hashes password with bcrypt and salt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies plain text password against hashed password.
    Supports bcrypt hashes ($2b$) and SHA256 demo fallback hashes.
    """
    if hashed_password.startswith("$2b$") or hashed_password.startswith("$2a$"):
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
        except Exception:
            return False
    
    # Fallback check for initial SHA256 demo hashes
    sha_hash = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
    return sha_hash == hashed_password


def create_access_token(user_id: str | int, username: str, role: str) -> str:
    """Creates signed JWT token with user_id, username, role, and 24-hour expiration."""
    now = datetime.datetime.now(datetime.timezone.utc)
    expire = now + datetime.timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "exp": expire,
        "iat": now,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Decodes and validates JWT token signature and expiration."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        print("Notice: JWT token expired (time up).")
        return None
    except jwt.PyJWTError as e:
        print(f"Notice: Invalid JWT token signature: {e}")
        return None

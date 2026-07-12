"""
Authentication service for GIIPS.

Handles JWT token generation, verification, password hashing,
and httpOnly cookie management for cross-origin auth (Vercel <-> Render).
"""

import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Response

SECRET_KEY = os.environ.get("GIIPS_JWT_SECRET")
if not SECRET_KEY:
    raise RuntimeError("GIIPS_JWT_SECRET environment variable is not set. Backend startup aborted.")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
COOKIE_MAX_AGE = ACCESS_TOKEN_EXPIRE_MINUTES * 60


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        return None


# --- httpOnly cookie helpers (cross-origin: Vercel -> Render) ---

COOKIE_KWARGS = dict(
    httponly=True,
    secure=True,
    samesite="none",
    path="/",
    max_age=COOKIE_MAX_AGE,
)


def set_auth_cookie(response: Response, access_token: str) -> None:
    """Set the JWT as an httpOnly cookie.

    Uses SameSite=None + Secure so the browser sends it on cross-origin
    requests from giips.vercel.app to giips-backend.onrender.com.
    """
    response.set_cookie(key="access_token", value=access_token, **COOKIE_KWARGS)


def clear_auth_cookie(response: Response) -> None:
    """Clear the auth cookie (logout)."""
    response.set_cookie(
        key="access_token", value="", httponly=True, secure=True,
        samesite="none", path="/", max_age=0,
    )

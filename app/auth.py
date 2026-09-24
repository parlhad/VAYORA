"""
VAYORA — Authentication Utilities
Phase 3B

This module handles:
- Password hashing
- Password verification
- JWT access tokens
- JWT decoding

It does NOT modify VAYORA environmental intelligence.
"""

import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from dotenv import load_dotenv
from pwdlib import PasswordHash


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# PASSWORD HASHING
# ============================================================

password_hash = PasswordHash.recommended()


# ============================================================
# JWT CONFIGURATION
# ============================================================

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

if not JWT_SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY is not configured. "
        "Add JWT_SECRET_KEY to the VAYORA .env file."
    )


JWT_ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


# ============================================================
# PASSWORD FUNCTIONS
# ============================================================

def hash_password(password: str) -> str:

    return password_hash.hash(password)


def verify_password(
    password: str,
    hashed_password: str,
) -> bool:

    return password_hash.verify(
        password,
        hashed_password,
    )


# ============================================================
# JWT TOKEN
# ============================================================

def create_access_token(
    user_id: UUID,
) -> str:

    expire = datetime.now(
        timezone.utc
    ) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "exp": expire,
    }

    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


# ============================================================
# JWT VERIFICATION
# ============================================================

def decode_access_token(
    token: str,
) -> UUID:

    payload = jwt.decode(
        token,
        JWT_SECRET_KEY,
        algorithms=[JWT_ALGORITHM],
    )

    user_id = payload.get("sub")

    if not user_id:
        raise ValueError(
            "Token does not contain a user ID."
        )

    return UUID(user_id)
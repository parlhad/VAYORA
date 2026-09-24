"""
VAYORA — PostgreSQL Database
Phase 3A — Database Foundation

This module only provides the database connection/session layer.

IMPORTANT:
- Does not modify VAYORA AI logic.
- Does not modify existing session_memory.py.
- Does not call Gemini.
- Does not call AQI/Weather APIs.
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# DATABASE URL
# ============================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL"
)

if not DATABASE_URL:

    raise RuntimeError(
        "DATABASE_URL is not configured. "
        "Add DATABASE_URL to the VAYORA .env file."
    )

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1
    )
# ============================================================
# ENGINE
# ============================================================

engine = create_engine(
    DATABASE_URL,

    pool_pre_ping=True,

    future=True,
)


# ============================================================
# SESSION FACTORY
# ============================================================

SessionLocal = sessionmaker(
    bind=engine,

    autoflush=False,

    autocommit=False,

    expire_on_commit=False,
)


# ============================================================
# BASE MODEL
# ============================================================

class Base(DeclarativeBase):

    pass


# ============================================================
# DATABASE SESSION HELPER
# ============================================================

def get_db():

    db = SessionLocal()

    try:

        yield db

    finally:

        db.close()
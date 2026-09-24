"""
VAYORA — PostgreSQL Database Initializer
Phase 3A

Creates the initial VAYORA database tables.

Run from the VAYORA project root:

    python scripts/init_db.py
"""

from app.database import Base, engine

# Import models so SQLAlchemy knows about every table.
from app.models import User, Conversation, Message


def init_database():

    print()
    print("=" * 60)
    print("VAYORA — PostgreSQL Database Initialization")
    print("=" * 60)

    print()
    print("Connecting to PostgreSQL...")

    with engine.connect() as connection:

        print("PostgreSQL connection successful.")

    print()
    print("Creating VAYORA tables...")

    Base.metadata.create_all(
        bind=engine
    )

    print()
    print("Database tables created successfully.")

    print()
    print("Created:")
    print("  ✓ users")
    print("  ✓ conversations")
    print("  ✓ messages")

    print()
    print("Phase 3A database foundation is ready.")
    print("=" * 60)
    print()


if __name__ == "__main__":

    init_database()
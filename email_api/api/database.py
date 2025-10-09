"""Database connection and session management."""
import os
from typing import Generator

from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine, select

# Load environment variables
load_dotenv()

# Get database URL from environment or use default SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./email.db")

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)


def create_db_and_tables() -> None:
    """Create database and all tables."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """
    Get database session for dependency injection.

    Yields:
        Database session
    """
    with Session(engine) as session:
        yield session


def create_default_admin() -> None:
    """
    Create default admin user if no users exist.

    Only runs if the users table is empty.
    Uses DEFAULT_ADMIN_EMAIL and DEFAULT_ADMIN_PASSWORD from environment.
    """
    from .auth import hash_password
    from .models import User, UserRole

    with Session(engine) as session:
        # Check if any users exist
        statement = select(User)
        existing_users = session.exec(statement).first()

        if existing_users:
            # Users already exist, skip
            return

        # Get admin credentials from environment
        admin_email = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@example.com")
        admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "ChangeMe123!")

        # Create default admin user
        admin_user = User(
            email=admin_email,
            hashed_password=hash_password(admin_password),
            role=UserRole.ADMIN,
            domain=None,  # Admins have no domain restriction
            is_active=True,
        )

        session.add(admin_user)
        session.commit()

        print(f"✅ Created default admin user: {admin_email}")
        print(f"⚠️  Please change the default password immediately!")

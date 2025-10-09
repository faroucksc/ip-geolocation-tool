"""Data models for email management API."""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class UserRole(str, Enum):
    """User role enumeration."""

    ADMIN = "admin"
    DOMAIN_ADMIN = "domain_admin"
    USER = "user"


class User(SQLModel, table=True):
    """User account database model."""

    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, nullable=False)
    hashed_password: str = Field(nullable=False)
    role: UserRole = Field(default=UserRole.DOMAIN_ADMIN)
    domain: Optional[str] = Field(default=None, description="Assigned domain for domain_admin")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        """SQLModel config."""

        json_schema_extra = {
            "example": {
                "email": "admin@example.com",
                "role": "admin",
                "is_active": True,
            }
        }


class EmailAccount(SQLModel, table=True):
    """Email account database model."""

    __tablename__ = "email_accounts"
    __table_args__ = (UniqueConstraint("username", "domain", name="uq_username_domain"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, nullable=False)
    domain: str = Field(index=True, nullable=False)
    quota_mb: int = Field(default=1000, description="Email quota in megabytes")
    created_by_user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = Field(
        default=None,
        description="Soft delete timestamp",
    )

    class Config:
        """SQLModel config."""

        json_schema_extra = {
            "example": {
                "username": "john",
                "domain": "example.com",
                "quota_mb": 1000,
            }
        }


# Pydantic Request/Response Models


class EmailAccountResponse(SQLModel):
    """Response model for email account."""

    id: int
    username: str
    domain: str
    quota_mb: int
    created_at: datetime
    updated_at: datetime

    @property
    def email(self) -> str:
        """Get full email address."""
        return f"{self.username}@{self.domain}"


class CreateEmailRequest(SQLModel):
    """Request model for creating email account."""

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8)
    quota_mb: int = Field(default=1000, ge=1, le=50000)
    domain: Optional[str] = Field(default=None, description="Target domain (admin only)")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "username": "john",
                "password": "SecurePass123!",
                "quota_mb": 1000,
                "domain": "example.com",
            }
        }


class ChangePasswordRequest(SQLModel):
    """Request model for changing password."""

    new_password: str = Field(min_length=8)

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "new_password": "NewSecurePass456!",
            }
        }


# Authentication Request/Response Models


class UserResponse(SQLModel):
    """Response model for user (excludes password)."""

    id: int
    email: str
    role: UserRole
    domain: Optional[str]
    is_active: bool
    created_at: datetime


class LoginRequest(SQLModel):
    """Request model for user login."""

    email: str = Field(min_length=1)
    password: str = Field(min_length=1)

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "email": "admin@example.com",
                "password": "SecurePass123!",
            }
        }


class RegisterRequest(SQLModel):
    """Request model for user registration."""

    email: str = Field(min_length=1)
    password: str = Field(min_length=8)
    role: UserRole = Field(default=UserRole.DOMAIN_ADMIN)
    domain: Optional[str] = Field(default=None)

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "email": "newuser@example.com",
                "password": "SecurePass123!",
                "role": "domain_admin",
                "domain": "xseller.io",
            }
        }


class TokenResponse(SQLModel):
    """Response model for authentication token."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 86400,
            }
        }


# Admin Request/Response Models


class UpdateUserRoleRequest(SQLModel):
    """Request model for updating user role and domain."""

    role: UserRole
    domain: Optional[str] = Field(default=None, description="Assigned domain (for domain_admin)")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "role": "domain_admin",
                "domain": "example.com",
            }
        }

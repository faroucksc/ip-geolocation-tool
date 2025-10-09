"""Tests for authentication endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from email_api.api.auth import hash_password, verify_password
from email_api.api.database import get_session
from email_api.api.main import app
from email_api.api.models import User, UserRole


@pytest.fixture(name="session")
def session_fixture():
    """Create in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Create test client with database session override."""

    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="test_user")
def test_user_fixture(session: Session):
    """Create a test user in the database."""
    user = User(
        email="test@example.com",
        hashed_password=hash_password("TestPass123!"),
        role=UserRole.DOMAIN_ADMIN,
        domain="example.com",
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="admin_user")
def admin_user_fixture(session: Session):
    """Create an admin user in the database."""
    user = User(
        email="admin@example.com",
        hashed_password=hash_password("AdminPass123!"),
        role=UserRole.ADMIN,
        domain=None,
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(client: TestClient, test_user: User):
    """Get authentication headers with valid token."""
    response = client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "TestPass123!"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# Password hashing tests


def test_hash_password():
    """Test password hashing."""
    password = "TestPass123!"
    hashed = hash_password(password)

    # Hash should be different from password
    assert hashed != password
    # Hash should be bcrypt format
    assert hashed.startswith("$2b$")
    # Same password should produce different hash
    hashed2 = hash_password(password)
    assert hashed != hashed2


def test_verify_password():
    """Test password verification."""
    password = "TestPass123!"
    hashed = hash_password(password)

    # Correct password should verify
    assert verify_password(password, hashed)
    # Incorrect password should not verify
    assert not verify_password("WrongPass123!", hashed)


# Login tests (T6)


def test_login_valid_credentials(client: TestClient, test_user: User):
    """Test login with valid credentials returns token."""
    response = client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "TestPass123!"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


def test_login_invalid_email(client: TestClient, test_user: User):
    """Test login with invalid email returns 401."""
    response = client.post(
        "/auth/login",
        json={"email": "wrong@example.com", "password": "TestPass123!"},
    )

    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_login_invalid_password(client: TestClient, test_user: User):
    """Test login with invalid password returns 401."""
    response = client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "WrongPass123!"},
    )

    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_login_inactive_user(client: TestClient, session: Session):
    """Test login with inactive user returns 400."""
    # Create inactive user
    inactive_user = User(
        email="inactive@example.com",
        hashed_password=hash_password("TestPass123!"),
        role=UserRole.USER,
        is_active=False,
    )
    session.add(inactive_user)
    session.commit()

    response = client.post(
        "/auth/login",
        json={"email": "inactive@example.com", "password": "TestPass123!"},
    )

    assert response.status_code == 400
    assert "Inactive user" in response.json()["detail"]


# Token tests (T7)


def test_token_contains_correct_claims(client: TestClient, test_user: User):
    """Test that JWT token includes correct user claims."""
    from email_api.api.auth import decode_access_token

    response = client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "TestPass123!"},
    )

    token = response.json()["access_token"]
    payload = decode_access_token(token)

    assert payload["user_id"] == test_user.id
    assert payload["email"] == test_user.email
    assert payload["role"] == test_user.role.value
    assert "exp" in payload


def test_invalid_token_returns_401(client: TestClient):
    """Test that invalid token returns 401."""
    headers = {"Authorization": "Bearer invalid_token_here"}
    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 401


def test_missing_token_returns_403(client: TestClient):
    """Test that missing token returns 403."""
    response = client.get("/auth/me")

    assert response.status_code == 403


# Registration tests


def test_register_valid_user(client: TestClient):
    """Test user registration with valid data."""
    response = client.post(
        "/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "NewPass123!",
            "role": "domain_admin",
            "domain": "example.com",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["role"] == "domain_admin"
    assert data["domain"] == "example.com"
    assert data["is_active"] is True
    assert "hashed_password" not in data  # Should not expose password


def test_register_duplicate_email(client: TestClient, test_user: User):
    """Test registration with duplicate email returns 409."""
    response = client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "NewPass123!",
            "role": "domain_admin",
            "domain": "example.com",
        },
    )

    assert response.status_code == 409
    assert "already registered" in response.json()["detail"]


def test_register_weak_password(client: TestClient):
    """Test registration with weak password returns 400."""
    response = client.post(
        "/auth/register",
        json={
            "email": "weak@example.com",
            "password": "weak",
            "role": "domain_admin",
            "domain": "example.com",
        },
    )

    assert response.status_code in [400, 422]


def test_register_password_hashed(client: TestClient, session: Session):
    """Test that registered user's password is hashed."""
    client.post(
        "/auth/register",
        json={
            "email": "hashed@example.com",
            "password": "HashedPass123!",
            "role": "user",
        },
    )

    from sqlmodel import select

    from email_api.api.models import User

    statement = select(User).where(User.email == "hashed@example.com")
    user = session.exec(statement).first()

    assert user is not None
    assert user.hashed_password != "HashedPass123!"
    assert user.hashed_password.startswith("$2b$")


# Get current user tests


def test_get_current_user_valid_token(
    client: TestClient, test_user: User, auth_headers: dict
):
    """Test getting current user info with valid token."""
    response = client.get("/auth/me", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
    assert data["role"] == test_user.role.value
    assert data["domain"] == test_user.domain
    assert "hashed_password" not in data


def test_get_current_user_no_token(client: TestClient):
    """Test getting current user without token returns 403."""
    response = client.get("/auth/me")

    assert response.status_code == 403


def test_get_current_user_invalid_token(client: TestClient):
    """Test getting current user with invalid token returns 401."""
    headers = {"Authorization": "Bearer invalid_token"}
    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 401


# Protected endpoint tests


def test_protected_email_endpoint_requires_auth(client: TestClient):
    """Test that email endpoints require authentication."""
    # GET /emails
    response = client.get("/emails")
    assert response.status_code == 403

    # POST /emails
    response = client.post(
        "/emails",
        json={"username": "test", "password": "TestPass123!", "quota_mb": 1000},
    )
    assert response.status_code == 403

    # DELETE /emails/{username}
    response = client.delete("/emails/test")
    assert response.status_code == 403

    # PUT /emails/{username}/password
    response = client.put(
        "/emails/test/password", json={"new_password": "NewPass123!"}
    )
    assert response.status_code == 403


def test_protected_endpoints_work_with_auth(
    client: TestClient, auth_headers: dict, test_user: User
):
    """Test that protected endpoints work with valid auth."""
    # GET /emails should work
    response = client.get("/emails", headers=auth_headers)
    # May return 200 or 500 depending on DirectAdmin, but shouldn't be 401/403
    assert response.status_code != 403
    assert response.status_code != 401

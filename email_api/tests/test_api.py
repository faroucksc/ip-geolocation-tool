"""Tests for email management API endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from email_api.api.auth import hash_password
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
    """Create a test user for authentication."""
    user = User(
        email="test@example.com",
        hashed_password=hash_password("TestPass123!"),
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


# T1: Test list emails endpoint
def test_list_emails_empty(client: TestClient, auth_headers: dict):
    """Test listing emails when DirectAdmin returns empty list."""
    response = client.get("/emails", headers=auth_headers)
    assert response.status_code == 200
    # Note: This will actually call DirectAdmin API
    # In production tests, we'd mock the DirectAdmin client


def test_list_emails_syncs_database(client: TestClient, auth_headers: dict):
    """Test that list endpoint syncs with DirectAdmin."""
    response = client.get("/emails", headers=auth_headers)
    assert response.status_code == 200
    emails = response.json()
    # Verify it's a list
    assert isinstance(emails, list)
    # Each email should have required fields
    if emails:
        email = emails[0]
        assert "id" in email
        assert "username" in email
        assert "domain" in email
        assert "quota_mb" in email
        assert "created_at" in email
        assert "updated_at" in email


# T2: Test create email success
def test_create_email_success(client: TestClient, auth_headers: dict):
    """Test creating a new email account."""
    email_data = {
        "username": "pytest_user",
        "password": "TestPass123!",
        "quota_mb": 500,
    }
    response = client.post("/emails", json=email_data, headers=auth_headers)

    # Clean up
    if response.status_code == 201:
        client.delete("/emails/pytest_user", headers=auth_headers)

    assert response.status_code == 201
    created = response.json()
    assert created["username"] == "pytest_user"
    assert created["domain"] == "xseller.io"
    assert created["quota_mb"] == 500


# T3: Test create email with duplicate username
def test_create_email_duplicate(client: TestClient, auth_headers: dict):
    """Test that duplicate email creation fails with 409."""
    email_data = {
        "username": "pytest_dup",
        "password": "TestPass123!",
        "quota_mb": 500,
    }

    # Create first email
    response1 = client.post("/emails", json=email_data, headers=auth_headers)
    assert response1.status_code == 201

    # Try to create duplicate
    response2 = client.post("/emails", json=email_data, headers=auth_headers)
    assert response2.status_code == 409
    assert "already exists" in response2.json()["detail"]

    # Clean up
    client.delete("/emails/pytest_dup", headers=auth_headers)


# T4: Test delete email
def test_delete_email(client: TestClient, auth_headers: dict):
    """Test deleting an email account."""
    # Create email first
    email_data = {
        "username": "pytest_delete",
        "password": "TestPass123!",
        "quota_mb": 500,
    }
    client.post("/emails", json=email_data, headers=auth_headers)

    # Delete it
    response = client.delete("/emails/pytest_delete", headers=auth_headers)
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]

    # Verify it's gone (404)
    response2 = client.delete("/emails/pytest_delete", headers=auth_headers)
    assert response2.status_code == 404


def test_delete_nonexistent_email(client: TestClient, auth_headers: dict):
    """Test deleting non-existent email returns 404."""
    response = client.delete("/emails/nonexistent_user", headers=auth_headers)
    assert response.status_code == 404


# T5: Test password change
def test_change_password_success(client: TestClient, auth_headers: dict):
    """Test changing password for existing email."""
    # Create email first
    email_data = {
        "username": "pytest_pw",
        "password": "TestPass123!",
        "quota_mb": 500,
    }
    client.post("/emails", json=email_data, headers=auth_headers)

    # Change password
    password_data = {"new_password": "NewPass456!"}
    response = client.put("/emails/pytest_pw/password", json=password_data, headers=auth_headers)
    assert response.status_code == 200
    assert "Password updated" in response.json()["message"]

    # Clean up
    client.delete("/emails/pytest_pw", headers=auth_headers)


def test_change_password_nonexistent(client: TestClient, auth_headers: dict):
    """Test changing password for non-existent email returns 404."""
    password_data = {"new_password": "NewPass456!"}
    response = client.put("/emails/nonexistent/password", json=password_data, headers=auth_headers)
    assert response.status_code == 404


# Password validation tests
def test_create_email_weak_password_too_short(client: TestClient, auth_headers: dict):
    """Test that password < 8 characters is rejected."""
    email_data = {
        "username": "pytest_weak",
        "password": "Short1!",  # Only 7 chars
        "quota_mb": 500,
    }
    response = client.post("/emails", json=email_data, headers=auth_headers)
    assert response.status_code in [400, 422]  # Pydantic validation or custom


def test_create_email_weak_password_no_uppercase(client: TestClient, auth_headers: dict):
    """Test that password without uppercase is rejected."""
    email_data = {
        "username": "pytest_weak",
        "password": "testpass123!",  # No uppercase
        "quota_mb": 500,
    }
    response = client.post("/emails", json=email_data, headers=auth_headers)
    assert response.status_code == 400
    assert "uppercase" in response.json()["detail"].lower()


def test_create_email_weak_password_no_lowercase(client: TestClient, auth_headers: dict):
    """Test that password without lowercase is rejected."""
    email_data = {
        "username": "pytest_weak",
        "password": "TESTPASS123!",  # No lowercase
        "quota_mb": 500,
    }
    response = client.post("/emails", json=email_data, headers=auth_headers)
    assert response.status_code == 400
    assert "lowercase" in response.json()["detail"].lower()


def test_create_email_weak_password_no_number(client: TestClient, auth_headers: dict):
    """Test that password without number is rejected."""
    email_data = {
        "username": "pytest_weak",
        "password": "TestPass!",  # No number
        "quota_mb": 500,
    }
    response = client.post("/emails", json=email_data, headers=auth_headers)
    assert response.status_code == 400
    assert "number" in response.json()["detail"].lower()


def test_health_check(client: TestClient):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

"""Tests for role-based access control and permissions."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from email_api.api.auth import hash_password
from email_api.api.database import get_session
from email_api.api.main import app
from email_api.api.models import User, UserRole
from email_api.api.permissions import (
    can_access_domain,
    can_manage_email,
    get_effective_domain,
    get_user_domains,
)


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


@pytest.fixture(name="admin_user")
def admin_user_fixture(session: Session):
    """Create admin user for testing."""
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


@pytest.fixture(name="domain_admin_user")
def domain_admin_user_fixture(session: Session):
    """Create domain admin user for xseller.io."""
    user = User(
        email="domainadmin@xseller.io",
        hashed_password=hash_password("DomainPass123!"),
        role=UserRole.DOMAIN_ADMIN,
        domain="xseller.io",
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="other_domain_admin")
def other_domain_admin_fixture(session: Session):
    """Create domain admin user for other.com."""
    user = User(
        email="otheradmin@other.com",
        hashed_password=hash_password("OtherPass123!"),
        role=UserRole.DOMAIN_ADMIN,
        domain="other.com",
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="admin_headers")
def admin_headers_fixture(client: TestClient, admin_user: User):
    """Get authentication headers with admin token."""
    response = client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass123!"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(name="domain_admin_headers")
def domain_admin_headers_fixture(client: TestClient, domain_admin_user: User):
    """Get authentication headers with domain admin token."""
    response = client.post(
        "/auth/login",
        json={"email": "domainadmin@xseller.io", "password": "DomainPass123!"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(name="other_domain_headers")
def other_domain_headers_fixture(client: TestClient, other_domain_admin: User):
    """Get authentication headers with other domain admin token."""
    response = client.post(
        "/auth/login",
        json={"email": "otheradmin@other.com", "password": "OtherPass123!"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# T8: Test domain_admin can only access their domain


def test_domain_admin_can_list_their_domain(
    client: TestClient,
    domain_admin_headers: dict,
):
    """Domain admin can list emails for their domain."""
    response = client.get("/emails", headers=domain_admin_headers)
    assert response.status_code == 200


def test_domain_admin_cannot_list_other_domain(
    client: TestClient,
    domain_admin_headers: dict,
):
    """Domain admin cannot list emails for other domain."""
    # Try to access other.com (domain admin is for xseller.io)
    response = client.get("/emails?domain=other.com", headers=domain_admin_headers)
    assert response.status_code == 403
    assert "Access denied" in response.json()["detail"]


def test_domain_admin_can_create_in_their_domain(
    client: TestClient,
    domain_admin_headers: dict,
):
    """Domain admin can create email in their domain."""
    email_data = {
        "username": "test_user",
        "password": "TestPass123!",
        "quota_mb": 500,
    }
    response = client.post("/emails", json=email_data, headers=domain_admin_headers)

    # Clean up if created
    if response.status_code == 201:
        client.delete("/emails/test_user", headers=domain_admin_headers)

    assert response.status_code == 201
    created = response.json()
    assert created["domain"] == "xseller.io"


def test_domain_admin_cannot_create_in_other_domain(
    client: TestClient,
    domain_admin_headers: dict,
):
    """Domain admin cannot create email in other domain."""
    email_data = {
        "username": "test_user",
        "password": "TestPass123!",
        "quota_mb": 500,
        "domain": "other.com",  # Try to specify other domain
    }
    response = client.post("/emails", json=email_data, headers=domain_admin_headers)
    assert response.status_code == 403


def test_domain_admin_can_delete_in_their_domain(
    client: TestClient,
    domain_admin_headers: dict,
):
    """Domain admin can delete email in their domain."""
    # Create email first
    email_data = {
        "username": "test_delete",
        "password": "TestPass123!",
        "quota_mb": 500,
    }
    client.post("/emails", json=email_data, headers=domain_admin_headers)

    # Delete it
    response = client.delete("/emails/test_delete", headers=domain_admin_headers)
    assert response.status_code == 200


def test_domain_admin_cannot_delete_in_other_domain(
    client: TestClient,
    domain_admin_headers: dict,
):
    """Domain admin cannot delete email in other domain."""
    response = client.delete(
        "/emails/someuser?domain=other.com",
        headers=domain_admin_headers,
    )
    assert response.status_code == 403


# T9: Test admin can access all domains


def test_admin_can_list_any_domain(
    client: TestClient,
    admin_headers: dict,
):
    """Admin can list emails for any domain."""
    # List default domain
    response1 = client.get("/emails", headers=admin_headers)
    assert response1.status_code == 200

    # List specific domain
    response2 = client.get("/emails?domain=xseller.io", headers=admin_headers)
    assert response2.status_code == 200


def test_admin_can_create_in_any_domain(
    client: TestClient,
    admin_headers: dict,
):
    """Admin can create email in any domain."""
    email_data = {
        "username": "admin_test",
        "password": "TestPass123!",
        "quota_mb": 500,
        "domain": "xseller.io",
    }
    response = client.post("/emails", json=email_data, headers=admin_headers)

    # Clean up
    if response.status_code == 201:
        client.delete("/emails/admin_test?domain=xseller.io", headers=admin_headers)

    assert response.status_code == 201


def test_admin_can_delete_in_any_domain(
    client: TestClient,
    admin_headers: dict,
):
    """Admin can delete email in any domain."""
    # Create email first
    email_data = {
        "username": "admin_delete",
        "password": "TestPass123!",
        "quota_mb": 500,
        "domain": "xseller.io",
    }
    client.post("/emails", json=email_data, headers=admin_headers)

    # Delete it
    response = client.delete(
        "/emails/admin_delete?domain=xseller.io",
        headers=admin_headers,
    )
    assert response.status_code == 200


def test_admin_can_change_password_any_domain(
    client: TestClient,
    admin_headers: dict,
):
    """Admin can change password in any domain."""
    # Create email first
    email_data = {
        "username": "admin_pw",
        "password": "TestPass123!",
        "quota_mb": 500,
        "domain": "xseller.io",
    }
    client.post("/emails", json=email_data, headers=admin_headers)

    # Change password
    password_data = {"new_password": "NewPass456!"}
    response = client.put(
        "/emails/admin_pw/password?domain=xseller.io",
        json=password_data,
        headers=admin_headers,
    )
    assert response.status_code == 200

    # Clean up
    client.delete("/emails/admin_pw?domain=xseller.io", headers=admin_headers)


# Test permission helper functions


def test_can_access_domain_admin(admin_user: User):
    """Test admin can access any domain."""
    assert can_access_domain(admin_user, "xseller.io")
    assert can_access_domain(admin_user, "other.com")
    assert can_access_domain(admin_user, "any.domain")


def test_can_access_domain_domain_admin(domain_admin_user: User):
    """Test domain admin can only access their domain."""
    assert can_access_domain(domain_admin_user, "xseller.io")
    assert not can_access_domain(domain_admin_user, "other.com")


def test_can_manage_email(admin_user: User, domain_admin_user: User):
    """Test can_manage_email respects roles."""
    # Admin can manage any domain
    assert can_manage_email(admin_user, "xseller.io")
    assert can_manage_email(admin_user, "other.com")

    # Domain admin only their domain
    assert can_manage_email(domain_admin_user, "xseller.io")
    assert not can_manage_email(domain_admin_user, "other.com")


def test_get_user_domains(admin_user: User, domain_admin_user: User):
    """Test get_user_domains returns correct domains."""
    # Admin gets default domain
    admin_domains = get_user_domains(admin_user, "xseller.io")
    assert "xseller.io" in admin_domains

    # Domain admin gets their domain
    domain_admin_domains = get_user_domains(domain_admin_user, "xseller.io")
    assert domain_admin_domains == ["xseller.io"]


def test_get_effective_domain_admin(admin_user: User):
    """Test admin gets requested domain or default."""
    # Requested domain
    assert get_effective_domain(admin_user, "other.com", "xseller.io") == "other.com"

    # Default when not requested
    assert get_effective_domain(admin_user, None, "xseller.io") == "xseller.io"


def test_get_effective_domain_domain_admin(domain_admin_user: User):
    """Test domain admin always gets their assigned domain."""
    # Ignores requested domain
    assert (
        get_effective_domain(domain_admin_user, "other.com", "xseller.io")
        == "xseller.io"
    )

    # Uses assigned domain
    assert get_effective_domain(domain_admin_user, None, "default.com") == "xseller.io"


# Test admin endpoints


def test_non_admin_cannot_list_users(
    client: TestClient,
    domain_admin_headers: dict,
):
    """Non-admin cannot access /admin/users."""
    response = client.get("/admin/users", headers=domain_admin_headers)
    assert response.status_code == 403


def test_admin_can_list_all_users(
    client: TestClient,
    admin_headers: dict,
    admin_user: User,
    domain_admin_user: User,
):
    """Admin can list all users."""
    response = client.get("/admin/users", headers=admin_headers)
    assert response.status_code == 200
    users = response.json()
    assert len(users) >= 2  # At least admin and domain_admin


def test_admin_can_update_user_role(
    client: TestClient,
    admin_headers: dict,
    domain_admin_user: User,
):
    """Admin can update user roles."""
    update_data = {
        "role": "admin",
        "domain": None,
    }
    response = client.put(
        f"/admin/users/{domain_admin_user.id}/role",
        json=update_data,
        headers=admin_headers,
    )
    assert response.status_code == 200
    updated_user = response.json()
    assert updated_user["role"] == "admin"


def test_admin_can_deactivate_user(
    client: TestClient,
    admin_headers: dict,
    domain_admin_user: User,
):
    """Admin can deactivate users."""
    response = client.put(
        f"/admin/users/{domain_admin_user.id}/deactivate",
        headers=admin_headers,
    )
    assert response.status_code == 200
    updated_user = response.json()
    assert updated_user["is_active"] is False


def test_admin_can_reactivate_user(
    client: TestClient,
    admin_headers: dict,
    domain_admin_user: User,
):
    """Admin can reactivate users."""
    # Deactivate first
    client.put(
        f"/admin/users/{domain_admin_user.id}/deactivate",
        headers=admin_headers,
    )

    # Reactivate
    response = client.put(
        f"/admin/users/{domain_admin_user.id}/deactivate?activate=true",
        headers=admin_headers,
    )
    assert response.status_code == 200
    updated_user = response.json()
    assert updated_user["is_active"] is True


# Edge cases


def test_deactivated_user_cannot_login(
    client: TestClient,
    admin_headers: dict,
    domain_admin_user: User,
):
    """Deactivated user cannot login."""
    # Deactivate user
    client.put(
        f"/admin/users/{domain_admin_user.id}/deactivate",
        headers=admin_headers,
    )

    # Try to login
    response = client.post(
        "/auth/login",
        json={"email": "domainadmin@xseller.io", "password": "DomainPass123!"},
    )
    assert response.status_code == 400
    assert "Inactive" in response.json()["detail"]

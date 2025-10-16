"""FastAPI application for email management."""
import logging
import os
import re
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure templates
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

from .auth import (
    JWT_EXPIRE_MINUTES,
    create_access_token,
    get_current_active_user,
    hash_password,
    verify_password,
)
from .client import DirectAdminClient, DirectAdminError
from .database import create_db_and_tables, create_default_admin, get_session
from .email_service import email_service
from .models import (
    ChangePasswordRequest,
    CreateEmailRequest,
    EmailAccount,
    EmailAccountResponse,
    LoginRequest,
    PasswordResetToken,
    RegisterRequest,
    TokenResponse,
    UpdateUserRoleRequest,
    User,
    UserResponse,
)
from .permissions import (
    check_domain_access,
    check_domain_param_tampering,
    get_effective_domain,
    require_admin,
)

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Email Provisioning API",
    description="API for managing email accounts via DirectAdmin",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DirectAdmin client
da_client = DirectAdminClient(
    host=os.getenv("DIRECTADMIN_HOST"),
    user=os.getenv("DIRECTADMIN_USER"),
    key=os.getenv("DIRECTADMIN_KEY"),
    domain=os.getenv("DEFAULT_DOMAIN"),
)


def get_da_client(domain: str) -> DirectAdminClient:
    """
    Get DirectAdmin client for specific domain.

    Args:
        domain: Domain to manage emails for

    Returns:
        DirectAdminClient instance configured for the domain
    """
    return DirectAdminClient(
        host=os.getenv("DIRECTADMIN_HOST"),
        user=os.getenv("DIRECTADMIN_USER"),
        key=os.getenv("DIRECTADMIN_KEY"),
        domain=domain,
    )


@app.on_event("startup")
def on_startup():
    """Create database tables and default admin user on startup."""
    create_db_and_tables()
    create_default_admin()


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "email-provisioning-api"}


# Authentication Endpoints


@app.post("/auth/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    session: Annotated[Session, Depends(get_session)],
):
    """
    Login endpoint - authenticate user and return JWT token.

    Returns access token valid for 24 hours (default).
    """
    # Find user by email
    statement = select(User).where(User.email == request.email)
    user = session.exec(statement).first()

    # Validate credentials
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account",
        )

    # Create access token
    token_data = {
        "user_id": user.id,
        "email": user.email,
        "role": user.role.value,
    }
    access_token = create_access_token(
        data=token_data,
        expires_delta=timedelta(minutes=JWT_EXPIRE_MINUTES),
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=JWT_EXPIRE_MINUTES * 60,  # Convert to seconds
    )


@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    request: RegisterRequest,
    session: Annotated[Session, Depends(get_session)],
):
    """
    Register new user.

    Creates new user account with hashed password.
    """
    # Validate password strength
    validate_password(request.password)

    # Check if email already exists
    statement = select(User).where(User.email == request.email)
    existing_user = session.exec(statement).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email {request.email} already registered",
        )

    # Create new user
    new_user = User(
        email=request.email,
        hashed_password=hash_password(request.password),
        role=request.role,
        domain=request.domain,
        recovery_email=request.recovery_email,
        must_change_password=request.must_change_password,
        is_active=True,
    )

    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    # Generate reset token if password change required
    reset_token = None
    if request.must_change_password and request.recovery_email:
        try:
            reset_token = email_service.generate_reset_token(new_user.id, session)
        except Exception as e:
            logger.error(f"Failed to generate reset token: {e}", exc_info=True)

    # Send welcome email if recovery_email provided
    if request.recovery_email:
        try:
            email_service.send_user_credentials(
                to_email=request.recovery_email,
                login_email=new_user.email,
                password=request.password,
                role=new_user.role.value,
                must_change_password=new_user.must_change_password,
                reset_token=reset_token,
            )
        except Exception as e:
            # Log error but don't fail user creation
            logger.error(f"Failed to send welcome email: {e}", exc_info=True)

    return new_user


@app.get("/auth/me", response_model=UserResponse)
def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Get current authenticated user information.

    Requires valid JWT token in Authorization header.
    """
    return current_user


@app.post("/auth/change-password")
def change_password(
    request: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """
    Change current user's password.

    Requires valid JWT token. User must provide current password for verification.
    """
    # Verify current password
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    # Validate new password strength
    validate_password(request.new_password)

    # Update password
    current_user.hashed_password = hash_password(request.new_password)
    current_user.must_change_password = False
    current_user.updated_at = datetime.utcnow()

    session.add(current_user)
    session.commit()

    return {"message": "Password changed successfully"}


@app.get("/reset-password", response_class=HTMLResponse)
def get_reset_password_form(
    token: str,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
):
    """
    Serve password reset HTML form.

    Validates token and displays form if valid.
    """
    # Find token in database
    statement = select(PasswordResetToken).where(PasswordResetToken.token == token)
    reset_token = session.exec(statement).first()

    # Validate token
    if not reset_token:
        return templates.TemplateResponse(
            "reset_error.html",
            {"request": request, "title": "Invalid Link", "message": "This password reset link is invalid. Please contact your administrator."}
        )

    if reset_token.used:
        return templates.TemplateResponse(
            "reset_error.html",
            {"request": request, "title": "Link Already Used", "message": "This password reset link has already been used. Please contact your administrator if you need a new link."}
        )

    if datetime.utcnow() > reset_token.expires_at:
        return templates.TemplateResponse(
            "reset_error.html",
            {"request": request, "title": "Link Expired", "message": "This password reset link has expired. Please contact your administrator for a new link."}
        )

    # Token valid - show form
    return templates.TemplateResponse(
        "reset_password.html",
        {"request": request, "token": token, "error": None}
    )


@app.post("/reset-password", response_class=HTMLResponse)
def process_reset_password(
    request: Request,
    token: Annotated[str, Form()],
    new_password: Annotated[str, Form()],
    confirm_password: Annotated[str, Form()],
    session: Annotated[Session, Depends(get_session)],
):
    """
    Process password reset form submission.

    Validates passwords, updates user, and redirects to webmail.
    """
    # Find token
    statement = select(PasswordResetToken).where(PasswordResetToken.token == token)
    reset_token = session.exec(statement).first()

    # Validate token (same checks as GET)
    if not reset_token or reset_token.used or datetime.utcnow() > reset_token.expires_at:
        return templates.TemplateResponse(
            "reset_error.html",
            {"request": request, "title": "Invalid Request", "message": "This password reset link is no longer valid."}
        )

    # Validate passwords match
    if new_password != confirm_password:
        return templates.TemplateResponse(
            "reset_password.html",
            {"request": request, "token": token, "error": "Passwords do not match"}
        )

    # Validate password strength
    try:
        validate_password(new_password)
    except HTTPException as e:
        return templates.TemplateResponse(
            "reset_password.html",
            {"request": request, "token": token, "error": e.detail}
        )

    # Get user
    statement = select(User).where(User.id == reset_token.user_id)
    user = session.exec(statement).first()

    if not user:
        return templates.TemplateResponse(
            "reset_error.html",
            {"request": request, "title": "User Not Found", "message": "Associated user account not found."}
        )

    # Update password in database
    user.hashed_password = hash_password(new_password)
    user.must_change_password = False
    user.updated_at = datetime.utcnow()

    # Check if email account exists in DirectAdmin and update password there too
    if user.domain:
        try:
            username = user.email.split('@')[0]
            domain = user.email.split('@')[1]

            # Check if email account exists in our database
            email_statement = select(EmailAccount).where(
                EmailAccount.username == username,
                EmailAccount.domain == domain,
                EmailAccount.deleted_at.is_(None)
            )
            email_account = session.exec(email_statement).first()

            if email_account:
                # Update DirectAdmin password
                client = get_da_client(domain)
                client.change_password(username, new_password, email_account.quota_mb)
                logger.info(f"Also updated DirectAdmin password for email {user.email}")
        except Exception as e:
            # Don't fail password reset if DirectAdmin update fails
            logger.warning(f"Failed to update DirectAdmin password for {user.email}: {e}")

    # Mark token as used
    reset_token.used = True

    session.add(user)
    session.add(reset_token)
    session.commit()

    logger.info(f"Password reset successful for user {user.email}")

    # Redirect to webmail (use domain-specific webmail URL)
    domain = user.email.split('@')[1] if '@' in user.email else os.getenv("DEFAULT_DOMAIN", "xseller.io")
    webmail_url = os.getenv("WEBMAIL_URL", f"https://webmail.{domain}")
    return RedirectResponse(
        url=f"{webmail_url}?message=password_changed",
        status_code=status.HTTP_302_FOUND
    )


# Email Management Endpoints


def validate_password(password: str) -> None:
    """
    Validate password strength.

    Args:
        password: Password to validate

    Raises:
        HTTPException: If password doesn't meet requirements
    """
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long",
        )

    if not re.search(r"[A-Z]", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one uppercase letter",
        )

    if not re.search(r"[a-z]", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one lowercase letter",
        )

    if not re.search(r"\d", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one number",
        )


@app.get("/emails", response_model=list[EmailAccountResponse])
def list_emails(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    domain: str | None = None,
):
    """
    List all email accounts for a domain.

    Syncs with DirectAdmin and returns all active email accounts.
    Requires authentication.

    - Admins: Can specify domain parameter, defaults to DEFAULT_DOMAIN
    - Domain admins: Always use their assigned domain (domain param ignored)
    """
    try:
        # Check for domain parameter tampering
        check_domain_param_tampering(current_user, domain)

        # Determine effective domain based on user role
        default_domain = os.getenv("DEFAULT_DOMAIN")
        effective_domain = get_effective_domain(current_user, domain, default_domain)

        # Check domain access permission
        check_domain_access(current_user, effective_domain)

        # Get DirectAdmin client for this domain
        client = get_da_client(effective_domain)

        # Get emails from DirectAdmin
        da_emails = client.list_emails()

        # Sync with database
        for da_email in da_emails:
            username = da_email["username"]

            # Check if exists in DB
            statement = select(EmailAccount).where(
                EmailAccount.username == username,
                EmailAccount.domain == effective_domain,
            )
            db_email = session.exec(statement).first()

            if not db_email:
                # Create new record
                db_email = EmailAccount(
                    username=username,
                    domain=effective_domain,
                    quota_mb=1000,  # Default quota
                )
                session.add(db_email)

            # Ensure not soft-deleted
            if db_email.deleted_at:
                db_email.deleted_at = None
                db_email.updated_at = datetime.utcnow()

        session.commit()

        # Return all active emails
        statement = select(EmailAccount).where(
            EmailAccount.domain == effective_domain,
            EmailAccount.deleted_at.is_(None),
        )
        emails = session.exec(statement).all()

        return emails

    except DirectAdminError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DirectAdmin error: {e.message}",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@app.post("/emails", response_model=EmailAccountResponse, status_code=status.HTTP_201_CREATED)
def create_email(
    request: CreateEmailRequest,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Create new email account.

    Validates password strength, creates account in DirectAdmin,
    and saves to database.
    Requires authentication - tracks which user created the email.

    - Admins: Can specify domain in request, defaults to DEFAULT_DOMAIN
    - Domain admins: Always use their assigned domain (request domain ignored)
    """
    try:
        # Validate password
        validate_password(request.password)

        # Check for domain parameter tampering
        check_domain_param_tampering(current_user, request.domain)

        # Determine effective domain based on user role
        default_domain = os.getenv("DEFAULT_DOMAIN")
        effective_domain = get_effective_domain(current_user, request.domain, default_domain)

        # Check domain access permission
        check_domain_access(current_user, effective_domain)

        # Get DirectAdmin client for this domain
        client = get_da_client(effective_domain)

        # Check if email already exists in DB
        statement = select(EmailAccount).where(
            EmailAccount.username == request.username,
            EmailAccount.domain == effective_domain,
            EmailAccount.deleted_at.is_(None),
        )
        existing = session.exec(statement).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email {request.username}@{effective_domain} already exists",
            )

        # Create in DirectAdmin
        client.create_email(
            username=request.username,
            password=request.password,
            quota_mb=request.quota_mb,
        )

        # Save to database
        db_email = EmailAccount(
            username=request.username,
            domain=effective_domain,
            quota_mb=request.quota_mb,
            created_by_user_id=current_user.id,
        )
        session.add(db_email)
        session.commit()
        session.refresh(db_email)

        # Send notification email if requested
        if request.notify_email:
            try:
                email_service.send_email_account_credentials(
                    to_email=request.notify_email,
                    email_address=f"{request.username}@{effective_domain}",
                    password=request.password,
                    quota_mb=request.quota_mb,
                )
            except Exception as e:
                # Log error but don't fail email creation
                logger.error(f"Failed to send notification email: {e}", exc_info=True)

        return db_email

    except DirectAdminError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DirectAdmin error: {e.message}",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@app.delete("/emails/{username}")
def delete_email(
    username: str,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    domain: str | None = None,
):
    """
    Delete email account.

    Deletes from DirectAdmin and soft-deletes in database.
    Requires authentication.

    - Admins: Can specify domain parameter, defaults to DEFAULT_DOMAIN
    - Domain admins: Always use their assigned domain (domain param ignored)
    """
    try:
        # Check for domain parameter tampering
        check_domain_param_tampering(current_user, domain)

        # Determine effective domain based on user role
        default_domain = os.getenv("DEFAULT_DOMAIN")
        effective_domain = get_effective_domain(current_user, domain, default_domain)

        # Check domain access permission
        check_domain_access(current_user, effective_domain)

        # Get DirectAdmin client for this domain
        client = get_da_client(effective_domain)

        # Check if email exists
        statement = select(EmailAccount).where(
            EmailAccount.username == username,
            EmailAccount.domain == effective_domain,
            EmailAccount.deleted_at.is_(None),
        )
        db_email = session.exec(statement).first()

        if not db_email:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Email {username}@{effective_domain} not found",
            )

        # Delete from DirectAdmin
        client.delete_email(username)

        # Soft delete in database
        db_email.deleted_at = datetime.utcnow()
        db_email.updated_at = datetime.utcnow()
        session.add(db_email)
        session.commit()

        return {"message": f"Email {username}@{effective_domain} deleted successfully"}

    except DirectAdminError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DirectAdmin error: {e.message}",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@app.put("/emails/{username}/password")
def change_password(
    username: str,
    request: ChangePasswordRequest,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    domain: str | None = None,
):
    """
    Change email account password.

    Validates password strength and updates in DirectAdmin.
    Requires authentication.

    - Admins: Can specify domain parameter, defaults to DEFAULT_DOMAIN
    - Domain admins: Always use their assigned domain (domain param ignored)
    """
    try:
        # Validate password
        validate_password(request.new_password)

        # Check for domain parameter tampering
        check_domain_param_tampering(current_user, domain)

        # Determine effective domain based on user role
        default_domain = os.getenv("DEFAULT_DOMAIN")
        effective_domain = get_effective_domain(current_user, domain, default_domain)

        # Check domain access permission
        check_domain_access(current_user, effective_domain)

        # Get DirectAdmin client for this domain
        client = get_da_client(effective_domain)

        # Check if email exists
        statement = select(EmailAccount).where(
            EmailAccount.username == username,
            EmailAccount.domain == effective_domain,
            EmailAccount.deleted_at.is_(None),
        )
        db_email = session.exec(statement).first()

        if not db_email:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Email {username}@{effective_domain} not found",
            )

        # Change password in DirectAdmin
        client.change_password(username, request.new_password)

        # Update timestamp in database
        db_email.updated_at = datetime.utcnow()
        session.add(db_email)
        session.commit()

        return {"message": f"Password updated for {username}@{effective_domain}"}

    except DirectAdminError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DirectAdmin error: {e.message}",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# Admin Endpoints


@app.get("/admin/users", response_model=list[UserResponse])
def list_users(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    List all users.

    Admin only. Returns all user accounts with their roles and domains.
    """
    # Require admin role
    require_admin(current_user)

    # Get all users
    statement = select(User)
    users = session.exec(statement).all()

    return users


@app.put("/admin/users/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: int,
    request: UpdateUserRoleRequest,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Update user role and assigned domain.

    Admin only. Allows changing user role and domain assignment.
    """
    # Require admin role
    require_admin(current_user)

    # Find user
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    # Update role and domain
    user.role = request.role
    user.domain = request.domain
    user.updated_at = datetime.utcnow()

    session.add(user)
    session.commit()
    session.refresh(user)

    return user


@app.put("/admin/users/{user_id}/deactivate", response_model=UserResponse)
def deactivate_user(
    user_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    activate: bool = False,
):
    """
    Deactivate or reactivate user account.

    Admin only. Sets is_active flag.

    - deactivate: ?activate=false (default)
    - reactivate: ?activate=true
    """
    # Require admin role
    require_admin(current_user)

    # Find user
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    # Update active status
    user.is_active = activate
    user.updated_at = datetime.utcnow()

    session.add(user)
    session.commit()
    session.refresh(user)

    return user


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

"""Permission checking and role-based access control."""
from fastapi import HTTPException, status

from .models import User, UserRole


def require_admin(user: User) -> None:
    """
    Require user to have admin role.

    Args:
        user: Current authenticated user

    Raises:
        HTTPException: 403 if user is not an admin
    """
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )


def require_role(user: User, allowed_roles: list[UserRole]) -> None:
    """
    Require user to have one of the allowed roles.

    Args:
        user: Current authenticated user
        allowed_roles: List of roles that are allowed

    Raises:
        HTTPException: 403 if user doesn't have required role
    """
    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Required role: {', '.join(r.value for r in allowed_roles)}",
        )


def can_access_domain(user: User, domain: str) -> bool:
    """
    Check if user can access the specified domain.

    Rules:
    - Admin users can access any domain
    - Domain admin users can only access their assigned domain
    - User role has no domain access (read-only, future)

    Args:
        user: Current authenticated user
        domain: Domain to check access for

    Returns:
        True if user can access the domain, False otherwise
    """
    # Admins can access any domain
    if user.role == UserRole.ADMIN:
        return True

    # Domain admins can only access their assigned domain
    if user.role == UserRole.DOMAIN_ADMIN:
        return user.domain == domain

    # User role has no write access (read-only in future)
    return False


def check_domain_access(user: User, domain: str) -> None:
    """
    Check domain access and raise exception if denied.

    Args:
        user: Current authenticated user
        domain: Domain to check access for

    Raises:
        HTTPException: 403 if user cannot access the domain
    """
    if not can_access_domain(user, domain):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied to domain: {domain}",
        )


def get_user_domains(user: User, default_domain: str) -> list[str]:
    """
    Get list of domains the user can access.

    Args:
        user: Current authenticated user
        default_domain: Default domain from config

    Returns:
        List of accessible domain names
    """
    # Admins can theoretically access any domain
    # For now, we return the default domain as a placeholder
    if user.role == UserRole.ADMIN:
        # In a real system, this might query DirectAdmin for all domains
        # For now, return a list indicating admin has broad access
        return [default_domain]  # Admins can use any domain via params

    # Domain admins only see their assigned domain
    if user.role == UserRole.DOMAIN_ADMIN:
        return [user.domain] if user.domain else []

    # User role has no domains
    return []


def can_manage_email(user: User, email_domain: str) -> bool:
    """
    Check if user can manage emails in the specified domain.

    Args:
        user: Current authenticated user
        email_domain: Domain where the email exists

    Returns:
        True if user can manage emails in that domain
    """
    return can_access_domain(user, email_domain)


def check_domain_param_tampering(user: User, requested_domain: str | None) -> None:
    """
    Check if domain_admin is trying to access a different domain.

    Domain admins should not be able to request a different domain than their assigned one.
    If they try, raise 403 error.

    Args:
        user: Current authenticated user
        requested_domain: Domain requested by user (optional)

    Raises:
        HTTPException: 403 if domain_admin requests different domain
    """
    if user.role == UserRole.DOMAIN_ADMIN and requested_domain:
        if requested_domain != user.domain:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: domain_admin can only access {user.domain}",
            )


def get_effective_domain(user: User, requested_domain: str | None, default_domain: str) -> str:
    """
    Get the effective domain to use for the operation.

    Rules:
    - Admin: Use requested_domain if provided, else default_domain
    - Domain admin: Always use their assigned domain (ignore requested)

    Args:
        user: Current authenticated user
        requested_domain: Domain requested by user (optional)
        default_domain: Default domain from config

    Returns:
        The domain to use for the operation
    """
    # Domain admins always use their assigned domain
    if user.role == UserRole.DOMAIN_ADMIN:
        return user.domain or default_domain

    # Admins can use requested domain or fall back to default
    if user.role == UserRole.ADMIN:
        return requested_domain or default_domain

    # Default case
    return default_domain

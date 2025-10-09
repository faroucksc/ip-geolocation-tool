"""DirectAdmin API client for email management."""
import time
from typing import Any
from urllib.parse import parse_qs, urlencode

import httpx


class DirectAdminError(Exception):
    """Custom exception for DirectAdmin API errors."""

    def __init__(self, message: str, details: str | None = None):
        self.message = message
        self.details = details
        super().__init__(f"{message}: {details}" if details else message)


class DirectAdminClient:
    """Client for DirectAdmin API operations."""

    def __init__(self, host: str, user: str, key: str, domain: str):
        """
        Initialize DirectAdmin client.

        Args:
            host: DirectAdmin server URL (e.g., https://london.mxroute.com:2222)
            user: DirectAdmin username
            key: DirectAdmin API key
            domain: Default domain for email operations
        """
        self.host = host.rstrip("/")
        self.user = user
        self.key = key
        self.domain = domain
        self.auth = (user, key)

    def _parse_response(self, response_text: str) -> dict[str, Any]:
        """
        Parse URL-encoded DirectAdmin response.

        Args:
            response_text: URL-encoded response from DirectAdmin

        Returns:
            Parsed response as dictionary

        Raises:
            DirectAdminError: If response contains error
        """
        parsed = parse_qs(response_text)

        # Flatten single-item lists
        result = {}
        for key, value in parsed.items():
            result[key] = value[0] if len(value) == 1 else value

        # Check for errors
        if result.get("error") == "1":
            raise DirectAdminError(
                message=result.get("text", "Unknown error"),
                details=result.get("details"),
            )

        return result

    def _make_request(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """
        Make HTTP request to DirectAdmin API with retry logic.

        Args:
            endpoint: API endpoint (e.g., CMD_API_POP)
            params: Request parameters
            max_retries: Maximum number of retry attempts

        Returns:
            Parsed response dictionary

        Raises:
            DirectAdminError: If request fails after all retries
        """
        url = f"{self.host}/{endpoint}"
        params = params or {}

        for attempt in range(max_retries):
            try:
                response = httpx.post(
                    url,
                    auth=self.auth,
                    data=params,
                    timeout=30.0,
                    verify=False,  # SSL verification disabled for self-signed certs
                )
                response.raise_for_status()
                return self._parse_response(response.text)

            except httpx.HTTPStatusError as e:
                if attempt == max_retries - 1:
                    raise DirectAdminError(
                        message=f"HTTP {e.response.status_code}",
                        details=e.response.text,
                    )
                time.sleep(2**attempt)  # Exponential backoff

            except httpx.RequestError as e:
                if attempt == max_retries - 1:
                    raise DirectAdminError(
                        message="Network error",
                        details=str(e),
                    )
                time.sleep(2**attempt)

        raise DirectAdminError("Max retries exceeded")

    def list_emails(self) -> list[dict[str, str]]:
        """
        List all email accounts for the domain.

        Returns:
            List of email account dictionaries with 'username' key
        """
        response = self._make_request(
            "CMD_API_POP",
            params={"action": "list", "domain": self.domain},
        )

        # Response format: {"list[]": ["user1", "user2", ...]}
        users = response.get("list[]", response.get("list", []))
        if isinstance(users, str):
            users = [users]

        return [{"username": user} for user in users]

    def create_email(
        self,
        username: str,
        password: str,
        quota_mb: int = 1000,
    ) -> dict[str, str]:
        """
        Create new email account.

        Args:
            username: Email username (without @domain)
            password: Email password
            quota_mb: Quota in megabytes (default: 1000)

        Returns:
            Dictionary with created email info

        Raises:
            DirectAdminError: If creation fails
        """
        response = self._make_request(
            "CMD_API_POP",
            params={
                "action": "create",
                "domain": self.domain,
                "user": username,
                "passwd": password,
                "passwd2": password,
                "quota": quota_mb,
            },
        )

        return {
            "username": username,
            "domain": self.domain,
            "quota_mb": quota_mb,
        }

    def delete_email(self, username: str) -> bool:
        """
        Delete email account.

        Args:
            username: Email username (without @domain)

        Returns:
            True if deletion successful

        Raises:
            DirectAdminError: If deletion fails
        """
        self._make_request(
            "CMD_API_POP",
            params={
                "action": "delete",
                "domain": self.domain,
                "user": username,
            },
        )

        return True

    def change_password(self, username: str, new_password: str) -> bool:
        """
        Change email account password.

        Args:
            username: Email username (without @domain)
            new_password: New password

        Returns:
            True if password change successful

        Raises:
            DirectAdminError: If password change fails
        """
        self._make_request(
            "CMD_CHANGE_EMAIL_PASSWORD",
            params={
                "email": username,
                "domain": self.domain,
                "passwd": new_password,
                "passwd2": new_password,
            },
        )

        return True

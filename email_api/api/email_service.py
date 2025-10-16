"""Email notification service."""
import os
import secrets
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from sqlmodel import Session

from .models import PasswordResetToken


class EmailService:
    """Service for sending email notifications."""

    def __init__(self):
        """Initialize email service with SMTP configuration from environment."""
        self.smtp_host = os.getenv("SMTP_HOST", "mail.ammalogic.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", "dev@ammalogic.com")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("SMTP_FROM_EMAIL", "dev@ammalogic.com")
        self.from_name = os.getenv("SMTP_FROM_NAME", "Email Provisioning API")
        self.base_url = os.getenv("API_BASE_URL", "https://admin.faso.dev")

    def _send_email(self, to_email: str, subject: str, body: str) -> bool:
        """
        Send email via SMTP.

        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body (plain text)

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            print(f"[EMAIL] Attempting to send to {to_email}")
            print(f"[EMAIL] SMTP: {self.smtp_host}:{self.smtp_port}")
            print(f"[EMAIL] From: {self.from_email}")

            msg = MIMEMultipart()
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to_email
            msg["Subject"] = subject

            msg.attach(MIMEText(body, "plain"))

            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
            server.quit()

            print(f"[EMAIL] ✓ Successfully sent to {to_email}")
            return True

        except Exception as e:
            print(f"[EMAIL] ✗ Failed to send email to {to_email}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def send_user_credentials(
        self,
        to_email: str,
        login_email: str,
        password: str,
        role: str,
        must_change_password: bool = False,
        reset_token: Optional[str] = None,
    ) -> bool:
        """
        Send user account credentials to recovery email.

        Args:
            to_email: Recovery email address
            login_email: User's login email
            password: Temporary password
            role: User role (admin, domain_admin)
            must_change_password: Whether password change is required
            reset_token: Password reset token (if must_change_password is True)

        Returns:
            True if email sent successfully
        """
        subject = "Your Email Management Account - xseller.io"

        body = f"""
Your email management account has been created.

Login Credentials:
------------------
Email: {login_email}
Password: {password}
Role: {role}

"""
        if must_change_password and reset_token:
            body += f"""
⚠️  IMPORTANT: You must change your password before first login.

Reset Password: {self.base_url}/reset-password?token={reset_token}

(This link expires in 48 hours)

"""
        else:
            body += f"""
Login URL: {self.base_url}/auth/login

"""

        body += """
If you did not request this account, please contact the administrator immediately.

--
Email Provisioning API
"""

        return self._send_email(to_email, subject, body)

    def generate_reset_token(self, user_id: int, session: Session) -> str:
        """
        Generate password reset token for user.

        Args:
            user_id: User ID
            session: Database session

        Returns:
            Reset token UUID string
        """
        token = secrets.token_urlsafe(32)
        expiry_hours = int(os.getenv("RESET_TOKEN_EXPIRY_HOURS", "48"))
        expires_at = datetime.utcnow() + timedelta(hours=expiry_hours)

        reset_token = PasswordResetToken(
            token=token,
            user_id=user_id,
            expires_at=expires_at,
            used=False,
        )
        session.add(reset_token)
        session.commit()

        return token

    def send_email_account_credentials(
        self,
        to_email: str,
        email_address: str,
        password: str,
        quota_mb: int,
    ) -> bool:
        """
        Send email account credentials to user.

        Args:
            to_email: Recipient's contact email
            email_address: Created email address (username@domain)
            password: Email account password
            quota_mb: Mailbox quota in megabytes

        Returns:
            True if email sent successfully
        """
        subject = f"Email Account Created - {email_address}"

        body = f"""
Your email account has been created.

Email Account Details:
---------------------
Email Address: {email_address}
Password: {password}
Quota: {quota_mb} MB

IMAP Settings (Incoming Mail):
------------------------------
Server: mail.xseller.io
Port: 993
Encryption: SSL/TLS
Username: {email_address}
Password: {password}

SMTP Settings (Outgoing Mail):
------------------------------
Server: mail.xseller.io
Port: 465
Encryption: SSL/TLS
Username: {email_address}
Password: {password}

You can configure this account in your email client (Outlook, Thunderbird, iPhone Mail, etc.) using the settings above.

--
Email Provisioning API
"""

        return self._send_email(to_email, subject, body)


# Singleton instance
email_service = EmailService()

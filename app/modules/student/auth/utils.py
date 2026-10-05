import hashlib
import html
import secrets
from datetime import datetime, timezone

from app.core.config import settings
from app.core.email import send_email


def generate_reset_token() -> str:
    return secrets.token_urlsafe(32)


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def is_reset_token_expired(expires_at: datetime | None) -> bool:
    if expires_at is None:
        return True

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    return expires_at < datetime.now(timezone.utc)


def build_reset_password_link(token: str, reset_path: str = "/reset-password") -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}{reset_path}/{token}"


def send_password_reset_email(
    student, token: str, reset_path: str = "/reset-password"
) -> None:
    full_name = f"{student.firstName} {student.lastName}".strip()
    reset_link = build_reset_password_link(token, reset_path)
    expiry_minutes = settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES

    subject = "Reset your Queunity password"
    text_body = (
        f"Hi {full_name},\n\n"
        "We received a request to reset your Queunity password. "
        "Open the link below to choose a new password:\n\n"
        f"{reset_link}\n\n"
        f"This link expires in {expiry_minutes} minutes and can only be used once.\n"
        "If you did not request a password reset, you can ignore this email."
    )
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #111827; line-height: 1.5;">
        <p>Hi {html.escape(full_name)},</p>
        <p>We received a request to reset your Queunity password.
           Click the button below to choose a new password.</p>
        <p>
          <a href="{html.escape(reset_link)}"
             style="display: inline-block; padding: 10px 16px; background: #111827; color: #ffffff; text-decoration: none; border-radius: 6px;">
            Reset password
          </a>
        </p>
        <p>Or copy and paste this link into your browser:</p>
        <p>{html.escape(reset_link)}</p>
        <p>This link expires in {expiry_minutes} minutes and can only be used once.</p>
        <p>If you did not request a password reset, you can ignore this email.</p>
      </body>
    </html>
    """

    send_email(student.email, subject, text_body, html_body)

from app.modules.student.auth.utils import (
    generate_reset_token,
    hash_reset_token,
    is_reset_token_expired,
)
from app.modules.student.auth.utils import (
    send_password_reset_email as _send_password_reset_email,
)

PARENT_RESET_PASSWORD_PATH = "/parent/reset-password"

__all__ = [
    "generate_reset_token",
    "hash_reset_token",
    "is_reset_token_expired",
    "send_password_reset_email",
]


def send_password_reset_email(parent, token: str) -> None:
    _send_password_reset_email(parent, token, PARENT_RESET_PASSWORD_PATH)

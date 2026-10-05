import asyncio
from datetime import datetime, timedelta, timezone

from app.common.response import success_response
from app.core.config import settings
from app.core.database import prisma
from app.core.exceptions import APIException
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.parent.auth.schema import (
    ParentForgotPasswordModel,
    ParentLoginModel,
    ParentRegisterModel,
    ParentResetPasswordModel,
)
from app.modules.parent.auth.utilis import (
    generate_reset_token,
    hash_reset_token,
    is_reset_token_expired,
    send_password_reset_email,
)

SENSITIVE_PARENT_FIELDS = {
    "passwordHash",
    "resetPasswordTokenHash",
    "resetPasswordTokenExpiresAt",
}

FORGOT_PASSWORD_MESSAGE = (
    "If that email is registered, we have sent a password reset link."
)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _parent_token(parent) -> str:
    return create_access_token(
        {
            "id": parent.id,
            "role": "parent",
            "email": parent.email,
        }
    )


async def parent_login_controller(payload: ParentLoginModel):
    parent = await prisma.parent.find_unique(
        where={"email": _normalize_email(payload.email)}
    )
    if not parent:
        raise APIException(status_code=401, message="Invalid credentials")
    if not verify_password(payload.password, parent.passwordHash):
        raise APIException(status_code=401, message="Invalid credentials")

    return success_response(
        data={
            "token": _parent_token(parent),
            "parent": parent.model_dump(exclude=SENSITIVE_PARENT_FIELDS),
        },
        message="Login successful",
    )


async def parent_register_controller(payload: ParentRegisterModel):
    email = _normalize_email(payload.email)

    if await prisma.parent.find_first(
        where={"email": {"equals": email, "mode": "insensitive"}}
    ):
        raise APIException(status_code=400, message="Parent already exists")

    parent = await prisma.parent.create(
        data={
            "firstName": payload.firstName.strip(),
            "lastName": payload.lastName.strip(),
            "email": email,
            "passwordHash": hash_password(payload.password),
        }
    )

    return success_response(
        data={
            "parent": parent.model_dump(exclude=SENSITIVE_PARENT_FIELDS),
            "token": _parent_token(parent),
        },
        message="Parent registered successfully",
    )


async def parent_forgot_password_controller(payload: ParentForgotPasswordModel):
    parent = await prisma.parent.find_first(
        where={"email": {"equals": _normalize_email(payload.email), "mode": "insensitive"}}
    )
    if not parent:
        return success_response(message=FORGOT_PASSWORD_MESSAGE)

    reset_token = generate_reset_token()
    await prisma.parent.update(
        where={"id": parent.id},
        data={
            "resetPasswordTokenHash": hash_reset_token(reset_token),
            "resetPasswordTokenExpiresAt": datetime.now(timezone.utc)
            + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES),
        },
    )

    await asyncio.to_thread(send_password_reset_email, parent, reset_token)
    return success_response(message=FORGOT_PASSWORD_MESSAGE)


async def parent_reset_password_controller(payload: ParentResetPasswordModel):
    token_hash = hash_reset_token(payload.token)
    parent = await prisma.parent.find_unique(
        where={"resetPasswordTokenHash": token_hash}
    )

    if not parent or is_reset_token_expired(parent.resetPasswordTokenExpiresAt):
        if parent:
            await prisma.parent.update(
                where={"id": parent.id},
                data={
                    "resetPasswordTokenHash": None,
                    "resetPasswordTokenExpiresAt": None,
                },
            )
        raise APIException(status_code=400, message="Invalid or expired reset link")

    await prisma.parent.update(
        where={"id": parent.id},
        data={
            "passwordHash": hash_password(payload.newPassword),
            "resetPasswordTokenHash": None,
            "resetPasswordTokenExpiresAt": None,
        },
    )

    return success_response(message="Password reset successful. You can now log in.")

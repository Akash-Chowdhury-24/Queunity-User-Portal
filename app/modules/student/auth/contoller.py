import asyncio
from datetime import datetime, timedelta, timezone

from app.common.response import success_response
from app.common.student_public_id import generate_student_public_id
from app.core.config import settings
from app.core.database import prisma
from app.core.exceptions import APIException
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.student.auth.schema import (
    StudentForgotPasswordModel,
    StudentLoginModel,
    StudentRegisterModel,
    StudentResetPasswordModel,
)
from app.modules.student.auth.utils import (
    generate_reset_token,
    hash_reset_token,
    is_reset_token_expired,
    send_password_reset_email,
)

SENSITIVE_STUDENT_FIELDS = {
    "passwordHash",
    "resetPasswordTokenHash",
    "resetPasswordTokenExpiresAt",
}

FORGOT_PASSWORD_MESSAGE = (
    "If that email is registered, we have sent a password reset link."
)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _student_token(student) -> str:
    return create_access_token(
        {
            "id": student.id,
            "role": "student",
            "email": student.email,
            "above8Years": student.above8Years,
        }
    )


async def student_login_controller(payload: StudentLoginModel):
    student = await prisma.student.find_unique(
        where={"email": _normalize_email(payload.email)}
    )
    if not student:
        raise APIException(status_code=401, message="Invalid credentials")
    if not verify_password(payload.password, student.passwordHash):
        raise APIException(status_code=401, message="Invalid credentials")

    return success_response(
        data={
            "token": _student_token(student),
            "student": student.model_dump(exclude=SENSITIVE_STUDENT_FIELDS),
        },
        message="Login successful",
    )


async def student_register_controller(payload: StudentRegisterModel):
    first_name = payload.firstName.strip()
    last_name = payload.lastName.strip()
    email = _normalize_email(payload.email)

    if await prisma.student.find_first(
        where={"email": {"equals": email, "mode": "insensitive"}}
    ):
        raise APIException(status_code=400, message="Student already exists")

    student = await prisma.student.create(
        data={
            "firstName": first_name,
            "lastName": last_name,
            "email": email,
            "passwordHash": hash_password(payload.password),
            "above8Years": payload.above8Years,
            "publicId": generate_student_public_id(first_name, last_name, email),
        }
    )

    return success_response(
        data={
            "student": student.model_dump(exclude=SENSITIVE_STUDENT_FIELDS),
            "token": _student_token(student),
        },
        message="Student registered successfully",
    )


async def student_forgot_password_controller(payload: StudentForgotPasswordModel):
    student = await prisma.student.find_first(
        where={"email": {"equals": _normalize_email(payload.email), "mode": "insensitive"}}
    )
    if not student:
        return success_response(message=FORGOT_PASSWORD_MESSAGE)

    reset_token = generate_reset_token()
    await prisma.student.update(
        where={"id": student.id},
        data={
            "resetPasswordTokenHash": hash_reset_token(reset_token),
            "resetPasswordTokenExpiresAt": datetime.now(timezone.utc)
            + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES),
        },
    )

    await asyncio.to_thread(send_password_reset_email, student, reset_token)
    return success_response(message=FORGOT_PASSWORD_MESSAGE)


async def student_reset_password_controller(payload: StudentResetPasswordModel):
    token_hash = hash_reset_token(payload.token)
    student = await prisma.student.find_unique(
        where={"resetPasswordTokenHash": token_hash}
    )

    if not student or is_reset_token_expired(student.resetPasswordTokenExpiresAt):
        if student:
            await prisma.student.update(
                where={"id": student.id},
                data={
                    "resetPasswordTokenHash": None,
                    "resetPasswordTokenExpiresAt": None,
                },
            )
        raise APIException(status_code=400, message="Invalid or expired reset link")

    await prisma.student.update(
        where={"id": student.id},
        data={
            "passwordHash": hash_password(payload.newPassword),
            "resetPasswordTokenHash": None,
            "resetPasswordTokenExpiresAt": None,
        },
    )

    return success_response(message="Password reset successful. You can now log in.")

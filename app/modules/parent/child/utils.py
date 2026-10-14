import html
import logging
import secrets
import string
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.core.email import send_email

logger = logging.getLogger("app")

SENSITIVE_STUDENT_FIELDS = {
    "passwordHash",
    "resetPasswordTokenHash",
    "resetPasswordTokenExpiresAt",
}

PUBLIC_SCHOOL_FIELDS = {
    "id",
    "publicId",
    "name",
    "logoUrl",
    "schoolType",
    "schoolCategory",
    "country",
    "addressLine1",
    "addressLine2",
    "landmark",
    "city",
    "state",
    "zipCode",
}

PASSWORD_SYMBOLS = "!@#$%^&*"


def today_ist() -> date:
    return datetime.now(ZoneInfo("Asia/Kolkata")).date()


def generate_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + PASSWORD_SYMBOLS
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.islower() for c in password)
            and any(c.isupper() for c in password)
            and any(c.isdigit() for c in password)
            and any(c in PASSWORD_SYMBOLS for c in password)
        ):
            return password


def public_school(school: Any, *, include_grades: bool = False) -> dict | None:
    if school is None:
        return None
    data = school.model_dump(include=PUBLIC_SCHOOL_FIELDS)
    if include_grades:
        data["grades"] = [
            {"id": grade.id, "gradeName": grade.gradeName}
            for grade in (school.grades or [])
        ]
    return data


def public_child(student: Any) -> dict:
    data = student.model_dump(
        exclude=SENSITIVE_STUDENT_FIELDS | {"school", "grade", "parent"}
    )
    data["school"] = public_school(student.school)
    data["grade"] = (
        {"id": student.grade.id, "gradeName": student.grade.gradeName}
        if student.grade
        else None
    )
    return data


def _full_name(person: Any) -> str:
    return f"{person.firstName or ''} {person.lastName or ''}".strip()


def _send_safely(to_email: str, subject: str, text_body: str, html_body: str) -> None:
    try:
        send_email(to_email, subject, text_body, html_body)
    except Exception:
        # send_email already logs the SMTP failure; one bad recipient must not block the rest.
        logger.warning("Email '%s' to %s was not delivered", subject, to_email)


def _detail_rows(rows: list[tuple[str, str]]) -> tuple[str, str]:
    text = "\n".join(f"{label}: {value}" for label, value in rows)
    cells = "".join(
        f'<tr><td style="padding: 4px 12px 4px 0;"><strong>{html.escape(label)}</strong></td>'
        f"<td>{html.escape(value)}</td></tr>"
        for label, value in rows
    )
    return text, f'<table style="border-collapse: collapse;">{cells}</table>'


def _wrap_html(paragraphs_before: list[str], table: str, paragraphs_after: list[str]) -> str:
    before = "".join(f"<p>{p}</p>" for p in paragraphs_before)
    after = "".join(f"<p>{p}</p>" for p in paragraphs_after)
    return f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #111827; line-height: 1.5;">
        {before}
        {table}
        {after}
      </body>
    </html>
    """


def send_school_enrollment_email(school: Any, student: Any, parent: Any) -> None:
    if not school or not school.principalEmail:
        return

    student_name = _full_name(student)
    principal = f"{school.principalFirstName or ''} {school.principalLastName or ''}".strip()
    greeting = principal or school.name
    subject = f"New student enrolled at {school.name}: {student_name}"

    text_rows, table = _detail_rows(
        [
            ("Student name", student_name),
            ("Student ID", student.publicId),
            ("Student email", student.email),
            ("Date of birth", student.dateOfBirth.date().isoformat() if student.dateOfBirth else "Not provided"),
            ("Gender", getattr(student.gender, "value", student.gender) or "Not provided"),
            ("Grade", student.grade.gradeName if student.grade else "Not provided"),
            ("Parent name", _full_name(parent)),
            ("Parent email", parent.email),
            ("Parent phone", parent.phoneNumber or "Not provided"),
        ]
    )
    text_body = (
        f"Hi {greeting},\n\n"
        f"{student_name} has just been enrolled at {school.name} on Queunity by their parent.\n\n"
        f"{text_rows}\n\n"
        "If this enrollment looks wrong, please contact the parent or update the student's record."
    )
    html_body = _wrap_html(
        [
            f"Hi {html.escape(greeting)},",
            f"<strong>{html.escape(student_name)}</strong> has just been enrolled at "
            f"{html.escape(school.name)} on Queunity by their parent.",
        ],
        table,
        ["If this enrollment looks wrong, please contact the parent or update the student's record."],
    )
    _send_safely(school.principalEmail, subject, text_body, html_body)


def send_parent_child_added_email(parent: Any, student: Any, school: Any, temporary_password: str) -> None:
    parent_name = _full_name(parent)
    student_name = _full_name(student)
    subject = f"{student_name} has been added to your Queunity account"

    text_rows, table = _detail_rows(
        [
            ("School", school.name),
            ("Student ID", student.publicId),
            ("Login email", student.email),
            ("Temporary password", temporary_password),
            ("Login page", settings.FRONTEND_URL),
        ]
    )
    text_body = (
        f"Hi {parent_name},\n\n"
        f"{student_name} has been added to your Queunity account and enrolled at {school.name}.\n"
        "Here are your child's login details:\n\n"
        f"{text_rows}\n\n"
        "Please help your child change this password after their first login."
    )
    html_body = _wrap_html(
        [
            f"Hi {html.escape(parent_name)},",
            f"<strong>{html.escape(student_name)}</strong> has been added to your Queunity account "
            f"and enrolled at {html.escape(school.name)}. Here are your child's login details:",
        ],
        table,
        ["Please help your child change this password after their first login."],
    )
    _send_safely(parent.email, subject, text_body, html_body)


def send_child_account_created_email(student: Any, school: Any, temporary_password: str) -> None:
    student_name = _full_name(student)
    subject = "Your Queunity student account has been created"

    text_rows, table = _detail_rows(
        [
            ("School", school.name),
            ("Student ID", student.publicId),
            ("Login email", student.email),
            ("Temporary password", temporary_password),
            ("Login page", settings.FRONTEND_URL),
        ]
    )
    text_body = (
        f"Hi {student_name},\n\n"
        "Your parent has created a Queunity student account for you.\n\n"
        f"{text_rows}\n\n"
        "Please change this password after you log in."
    )
    html_body = _wrap_html(
        [
            f"Hi {html.escape(student_name)},",
            "Your parent has created a Queunity student account for you.",
        ],
        table,
        ["Please change this password after you log in."],
    )
    _send_safely(student.email, subject, text_body, html_body)


def send_child_created_notifications(parent: Any, student: Any, temporary_password: str) -> None:
    school = student.school
    send_school_enrollment_email(school, student, parent)
    send_parent_child_added_email(parent, student, school, temporary_password)
    send_child_account_created_email(student, school, temporary_password)

import html
import logging
from typing import Any

from app.core.email import send_email

logger = logging.getLogger("app")

WHEN_LABELS = {
    "TODAY": "Today",
    "YESTERDAY": "Yesterday",
    "FEW_DAYS_AGO": "A few days ago",
}

WHERE_LABELS = {
    "CLASSROOM": "Classroom",
    "BATHROOM": "Bathroom",
    "PLAYGROUND": "Playground",
    "OTHERS": "Other",
}


def _label(labels: dict[str, str], value: Any) -> str:
    if value is None:
        return "Not provided"
    raw = getattr(value, "value", value)
    return labels.get(raw, str(raw))


def case_notification_recipients(student: Any) -> list[tuple[str, str]]:
    recipients: list[tuple[str, str]] = []
    parent = getattr(student, "parent", None)
    if parent and parent.email:
        recipients.append(
            (parent.email, f"{parent.firstName} {parent.lastName}".strip())
        )
    school = getattr(student, "school", None)
    if school and school.principalEmail:
        principal = f"{school.principalFirstName or ''} {school.principalLastName or ''}".strip()
        recipients.append((school.principalEmail, principal or school.name))
    return recipients


def send_case_notification_emails(
    recipients: list[tuple[str, str]], student: Any, case: Any, action: str
) -> None:
    student_name = f"{student.firstName} {student.lastName}".strip()
    when = _label(WHEN_LABELS, case.whenItHappened)
    where = _label(WHERE_LABELS, case.whereItHappened)
    description = case.caseDescription or "Not provided"

    subject = f"Queunity: {student_name} has {action} a case"

    for email, name in recipients:
        text_body = (
            f"Hi {name},\n\n"
            f"{student_name} has {action} a case on Queunity.\n\n"
            f"Case name: {case.caseName}\n"
            f"When it happened: {when}\n"
            f"Where it happened: {where}\n"
            f"Description: {description}\n\n"
            "Please check in with the student and follow up as needed."
        )
        html_body = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #111827; line-height: 1.5;">
            <p>Hi {html.escape(name)},</p>
            <p>{html.escape(student_name)} has {action} a case on Queunity.</p>
            <table style="border-collapse: collapse;">
              <tr><td style="padding: 4px 12px 4px 0;"><strong>Case name</strong></td><td>{html.escape(case.caseName)}</td></tr>
              <tr><td style="padding: 4px 12px 4px 0;"><strong>When it happened</strong></td><td>{html.escape(when)}</td></tr>
              <tr><td style="padding: 4px 12px 4px 0;"><strong>Where it happened</strong></td><td>{html.escape(where)}</td></tr>
              <tr><td style="padding: 4px 12px 4px 0; vertical-align: top;"><strong>Description</strong></td><td>{html.escape(description)}</td></tr>
            </table>
            <p>Please check in with the student and follow up as needed.</p>
          </body>
        </html>
        """
        try:
            send_email(email, subject, text_body, html_body)
        except Exception:
            # send_email already logs the SMTP failure; one bad recipient must not block the rest.
            logger.warning("Case %s notification to %s was not delivered", case.id, email)

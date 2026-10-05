import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings
from app.core.exceptions import APIException

logger = logging.getLogger("app")


def send_email(to_email: str, subject: str, text_body: str, html_body: str) -> None:
    message = MIMEMultipart("alternative")
    message["From"] = settings.EMAIL
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(text_body, "plain"))
    message.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
            server.starttls()
            server.login(settings.EMAIL, settings.EMAIL_PASSWORD)
            server.send_message(message)
    except Exception as exc:
        logger.exception("Failed to send email to %s", to_email)
        raise APIException(
            status_code=500,
            message="Failed to send credentials email. Please try again.",
        ) from exc

import hashlib
import secrets
import unicodedata

ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
LENGTH = 8


def generate_student_public_id(
    first_name: str,
    last_name: str,
    email: str
) -> str:
    """
    Generates a public student ID using first name, last name,
    email, and a cryptographically secure random component.

    Format:
        <INITIALS>-<8 random characters>

    Example:
        AC-7K9X2PQM
    """

    def normalize(value: str) -> str:
        normalized = unicodedata.normalize("NFD", value)
        return "".join(
            c for c in normalized
            if unicodedata.category(c) != "Mn"
        )

    first = normalize(first_name).strip()
    last = normalize(last_name).strip()
    email_normalized = email.strip().lower()

    # Generate initials
    first_initial = first[0].upper() if first else "S"
    last_initial = last[0].upper() if last else "T"

    prefix = f"{first_initial}{last_initial}"

    # Use email to create a deterministic seed
    email_hash = hashlib.sha256(
        email_normalized.encode("utf-8")
    ).hexdigest()

    # Convert part of the email hash into characters
    email_part = "".join(
        ALPHABET[int(email_hash[i:i + 2], 16) % len(ALPHABET)]
        for i in range(0, 12, 2)
    )

    # Add random characters
    random_part = "".join(
        secrets.choice(ALPHABET)
        for _ in range(LENGTH - len(email_part))
    )

    return f"{prefix}-{email_part}{random_part}"

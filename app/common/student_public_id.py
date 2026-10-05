# import re
# import secrets
# import unicodedata

# ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
# LENGTH = 8
# STOP_WORDS = {"of", "the", "and", "for", "at", "in"}
# PUBLIC_ID_REGEX = re.compile(r"^[A-Z0-9]{2,5}-\d{2}-[2-9A-HJKMNP-Z]{8}$")


# def derive_initials(school_name: str) -> str:
#     """
#     Derives 2 to 5 character uppercase initials from a school name.
#     Ignores accents, punctuation, and common stop words.
#     """
#     normalized = unicodedata.normalize("NFD", school_name)
#     without_accents = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
#     # Remove possessives ('s / ’s) before splitting words
#     without_possessives = re.sub(r"['’]s\b", "", without_accents, flags=re.IGNORECASE)
#     cleaned = re.sub(r"[^A-Za-z0-9\s]", " ", without_possessives)
#     words = [w for w in cleaned.split() if w and w.lower() not in STOP_WORDS]
#     initials = "".join(w[0] for w in words).upper()[:5]
#     if len(initials) >= 2:
#         return initials
#     first_word = words[0] if words else ""
#     return first_word[:3].upper() if first_word else "STU"


# def generate_student_public_id(prefix: str, admission_year: int) -> str:
#     """
#     Generates a unique, non-guessable public student ID in the format:
#     <SCHOOL_INITIALS>-<YY>-<8 random chars> (e.g., DPS-26-7K9X2PQM).
#     Uses Python's secrets module (CSPRNG) with zero modulo bias.
#     """
#     yy = f"{admission_year % 100:02d}"
#     random_part = "".join(secrets.choice(ALPHABET) for _ in range(LENGTH))
#     return f"{prefix}-{yy}-{random_part}"



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
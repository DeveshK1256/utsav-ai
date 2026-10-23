import re
from typing import Tuple, Optional


def normalize_e164_phone(phone_raw: str) -> str:
    """
    Normalizes a phone number to standard E.164.
    Reuses Indian mobile normalization logic:
    - Strips spaces, hyphens, brackets, dots
    - Handles +91, 91 prefix, leading 0, and bare 10-digit Indian numbers starting with 6-9
    - Handles valid international E.164 formatted numbers (+[1-9][0-9]{7,14})
    Raises ValueError with descriptive reason if invalid.
    """
    if not phone_raw or not str(phone_raw).strip():
        raise ValueError("Phone number cannot be empty")

    cleaned = re.sub(r"[\s\-\(\)\.]", "", str(phone_raw).strip())

    # Case 1: Indian numbers with +91 prefix
    if cleaned.startswith("+91"):
        digits = cleaned[3:]
        if len(digits) == 10 and digits.isdigit() and digits[0] in "6789":
            return f"+91{digits}"
        raise ValueError(f"Invalid Indian mobile number '{phone_raw}': 10 digits starting with 6-9 required")

    # Case 2: Indian numbers with 91 prefix (12 digits)
    if cleaned.startswith("91") and len(cleaned) == 12:
        digits = cleaned[2:]
        if digits.isdigit() and digits[0] in "6789":
            return f"+91{digits}"
        raise ValueError(f"Invalid Indian mobile number '{phone_raw}' with 91 prefix")

    # Case 3: Indian numbers with leading 0 (11 digits)
    if cleaned.startswith("0") and len(cleaned) == 11:
        digits = cleaned[1:]
        if digits.isdigit() and digits[0] in "6789":
            return f"+91{digits}"
        raise ValueError(f"Invalid Indian mobile number '{phone_raw}' with leading 0")

    # Case 4: Bare 10-digit Indian number
    if len(cleaned) == 10 and cleaned.isdigit():
        if cleaned[0] in "6789":
            return f"+91{cleaned}"
        raise ValueError(f"Invalid Indian mobile number '{phone_raw}': must start with 6, 7, 8, or 9")

    # Case 5: International E.164 number (starts with '+' and 8-15 digits)
    if cleaned.startswith("+"):
        rest = cleaned[1:]
        if 8 <= len(rest) <= 15 and rest.isdigit() and rest[0] != "0":
            return cleaned
        raise ValueError(f"Invalid international E.164 phone number: '{phone_raw}'")

    raise ValueError(f"Unparseable phone number '{phone_raw}'. Provide a valid 10-digit Indian mobile or +E.164 format.")


def validate_and_normalize_guest_phone(phone_raw: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Returns (is_valid, normalized_phone, error_message).
    Safe wrapper for batch imports without throwing exceptions.
    """
    try:
        norm = normalize_e164_phone(phone_raw)
        return True, norm, None
    except ValueError as e:
        return False, None, str(e)

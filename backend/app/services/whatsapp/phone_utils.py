import re


def _extract_indian_digits(cleaned: str) -> str | None:
    """Extracts candidate 10-digit national number from known Indian prefixes."""
    if cleaned.startswith("+91") and len(cleaned) == 13:
        return cleaned[3:]
    if cleaned.startswith("91") and len(cleaned) == 12:
        return cleaned[2:]
    if cleaned.startswith("0") and len(cleaned) == 11:
        return cleaned[1:]
    if len(cleaned) == 10 and not cleaned.startswith("+"):
        return cleaned
    return None


def _parse_indian_phone(cleaned: str, phone_raw: str) -> str | None:
    """Parses various Indian phone representations into standard +91XXXXXXXXXX format."""
    digits = _extract_indian_digits(cleaned)
    if digits is None:
        if cleaned.startswith("+91") or (cleaned.startswith("91") and len(cleaned) >= 10):
            raise ValueError(
                f"Invalid Indian mobile number '{phone_raw}': 10 digits starting with 6-9 required"
            )
        return None

    if digits.isdigit() and digits[0] in "6789":
        return f"+91{digits}"
    raise ValueError(f"Invalid Indian mobile number '{phone_raw}': must start with 6, 7, 8, or 9")


def _parse_international_phone(cleaned: str, phone_raw: str) -> str | None:
    """Parses international E.164 formatted numbers (+[1-9][0-9]{7,14})."""
    if cleaned.startswith("+"):
        rest = cleaned[1:]
        if 8 <= len(rest) <= 15 and rest.isdigit() and rest[0] != "0":
            return cleaned
        raise ValueError(f"Invalid international E.164 phone number: '{phone_raw}'")
    return None


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

    indian_res = _parse_indian_phone(cleaned, phone_raw)
    if indian_res:
        return indian_res

    intl_res = _parse_international_phone(cleaned, phone_raw)
    if intl_res:
        return intl_res

    raise ValueError(
        f"Unparseable phone number '{phone_raw}'. "
        "Provide a valid 10-digit Indian mobile or +E.164 format."
    )


def validate_and_normalize_guest_phone(phone_raw: str) -> tuple[bool, str | None, str | None]:
    """
    Returns (is_valid, normalized_phone, error_message).
    Safe wrapper for batch imports without throwing exceptions.
    """
    try:
        norm = normalize_e164_phone(phone_raw)
        return True, norm, None
    except ValueError as e:
        return False, None, str(e)

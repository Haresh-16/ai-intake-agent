"""Input validation utilities."""

import re
from typing import Tuple, Optional, Dict, Any


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """Validate email format.

    Args:
        email: Email address to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email:
        return False, "Email is required"

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if re.match(pattern, email):
        return True, None

    return False, "Please enter a valid email address"


def validate_phone(phone: str) -> Tuple[bool, Optional[str]]:
    """Validate phone number format.

    Args:
        phone: Phone number to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not phone:
        return False, "Phone number is required"

    # Remove common formatting characters
    cleaned = re.sub(r"[\s\-\(\)\.]", "", phone)

    # Check if it's 10-11 digits (with optional +1 prefix)
    if re.match(r"^\+?1?\d{10}$", cleaned):
        return True, None

    return False, "Please enter a valid phone number (10 digits)"


def validate_prospect_data(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate entire prospect data payload.

    All fields are required.

    Args:
        data: Prospect data dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check first name
    if not data.get("first_name") or not data.get("first_name").strip():
        return False, "First name is required"

    # Check last name
    if not data.get("last_name") or not data.get("last_name").strip():
        return False, "Last name is required"

    # Check state
    if not data.get("state") or not data.get("state").strip():
        return False, "State is required"

    # Validate email (required)
    valid, error = validate_email(data.get("email", ""))
    if not valid:
        return False, error

    # Validate phone (required)
    valid, error = validate_phone(data.get("phone", ""))
    if not valid:
        return False, error

    return True, None

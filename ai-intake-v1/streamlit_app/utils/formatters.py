"""Display formatting and text transformation utilities."""

from datetime import datetime
from typing import Any, Dict


# Stage label mapping (human-readable)
STAGE_LABELS = {
    "greeting_and_disclosure": "Initial Greeting",
    "consent": "Consent Collection",
    "open_fact_gathering": "Fact Gathering",
    "silent_classification": "Information Review",
    "targeted_followups": "Follow-up Questions",
    "evidence_request": "Evidence Collection",
    "cross_practice_scan": "Comprehensive Review",
    "defendant_capture": "Defendant Information",
    "wrap": "Final Review",
}

# Practice area labels
PRACTICE_AREA_LABELS = {
    "TCPA": "Telephone Consumer Protection Act (Robocalls/Texts)",
    "FCRA": "Fair Credit Reporting Act (Credit Report Issues)",
    "FDCPA": "Fair Debt Collection Practices Act (Debt Collectors)",
    "MASS_ARB": "Mass Arbitration / Consumer Claims",
    "UNKNOWN_CONSUMER": "Consumer Issue (Under Review)",
    "WRONG_FIT": "Outside Firm Scope",
}

# Defendant role labels
DEFENDANT_ROLE_LABELS = {
    "caller": "Caller/Texter",
    "collector": "Debt Collector",
    "furnisher": "Data Furnisher",
    "bureau": "Credit Bureau",
    "other": "Other Party",
}

# Agent recommendation messages
RECOMMENDATION_MESSAGES = {
    "route_to_attorney": "✅ Your case will be prioritized for attorney review.",
    "route_to_intake_review": "📋 Your information will be reviewed by our intake team.",
    "request_more_evidence": "📄 We need some additional evidence from you before proceeding.",
    "wrong_fit_close": "ℹ️ Based on your information, this may not be a case we can assist with. An attorney will review to confirm.",
}


def format_stage_label(stage: str) -> str:
    """Convert technical stage name to user-friendly label.

    Args:
        stage: Technical stage name

    Returns:
        User-friendly stage label
    """
    return STAGE_LABELS.get(stage, stage.replace("_", " ").title())


def format_practice_area(area: str) -> str:
    """Convert practice area enum to descriptive label.

    Args:
        area: Practice area enum value

    Returns:
        Descriptive practice area label
    """
    return PRACTICE_AREA_LABELS.get(area, area)


def format_defendant_role(role: str) -> str:
    """Convert defendant role enum to readable label.

    Args:
        role: Defendant role enum value

    Returns:
        Readable role label
    """
    return DEFENDANT_ROLE_LABELS.get(role, role.capitalize())


def format_timestamp(dt: datetime) -> str:
    """Format datetime for message display.

    Args:
        dt: Datetime object

    Returns:
        Formatted time string (e.g., "02:30 PM")
    """
    return dt.strftime("%I:%M %p")


def format_recommendation_message(recommendation: str) -> str:
    """Convert agent recommendation to user-friendly next steps.

    Args:
        recommendation: Agent recommendation enum value

    Returns:
        User-friendly recommendation message
    """
    return RECOMMENDATION_MESSAGES.get(
        recommendation, "Your information will be reviewed."
    )

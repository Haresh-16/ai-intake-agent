"""Session state management for Streamlit application."""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
import streamlit as st


@dataclass
class SessionState:
    """Schema for Streamlit session state."""

    # Flow control
    flow_state: str = "prospect_form"  # prospect_form | chat_active | finalized

    # Conversation data
    conversation_id: Optional[str] = None
    prospect_data: Optional[Dict[str, Any]] = None

    # Messages
    messages: List[Dict[str, Any]] = field(default_factory=list)

    # Stage tracking
    current_stage: str = "greeting_and_disclosure"
    stage_index: int = 0

    # Summary
    summary: Optional[Dict[str, Any]] = None

    # UI state
    suggested_next_prompt: str = ""
    last_api_error: Optional[str] = None


# Stage names mapping (for progress tracking)
STAGES = [
    "greeting_and_disclosure",
    "consent",
    "open_fact_gathering",
    "silent_classification",
    "targeted_followups",
    "evidence_request",
    "cross_practice_scan",
    "defendant_capture",
    "wrap",
]


def initialize_session_state():
    """Initialize all required session state keys if not present."""
    defaults = SessionState()

    for key, value in asdict(defaults).items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_session_state():
    """Clear all session state for new conversation."""
    # Clear all keys
    for key in list(st.session_state.keys()):
        del st.session_state[key]

    # Reinitialize with defaults
    initialize_session_state()


def get_stage_index(stage: str) -> int:
    """Get the index of a stage in the intake flow.

    Args:
        stage: Stage name

    Returns:
        Index of the stage (0-8), or 0 if not found
    """
    try:
        return STAGES.index(stage)
    except ValueError:
        return 0

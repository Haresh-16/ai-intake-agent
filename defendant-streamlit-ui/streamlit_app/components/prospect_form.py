"""Prospect information collection form component."""

import streamlit as st
from typing import Optional

from streamlit_app.utils.validators import validate_prospect_data


# US states for dropdown
US_STATES = [
    "",
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DE",
    "FL",
    "GA",
    "HI",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
    "DC",
]


def render_prospect_form(on_submit_callback) -> None:
    """Render the prospect information collection form.

    This form collects initial prospect data before starting the intake
    conversation. All fields are required.

    Args:
        on_submit_callback: Function to call when form is submitted with valid data
    """
    st.header("Welcome to Legal Intake")

    st.markdown(
        """
        Please provide your contact information to get started.
        **All fields are required.**
        """
    )

    # Compliance reminder
    st.info(
        "You are not creating an attorney-client relationship by providing "
        "this information."
    )

    # Name fields
    col1, col2 = st.columns(2)
    with col1:
        first_name = st.text_input(
            "First Name *",
            max_chars=100,
            key="prospect_first_name",
            placeholder="Enter your first name",
        )
    with col2:
        last_name = st.text_input(
            "Last Name *",
            max_chars=100,
            key="prospect_last_name",
            placeholder="Enter your last name",
        )

    # Contact fields
    email = st.text_input(
        "Email *",
        max_chars=255,
        key="prospect_email",
        help="We'll use this to send you updates",
        placeholder="your.email@example.com",
    )

    phone = st.text_input(
        "Phone *",
        max_chars=20,
        key="prospect_phone",
        help="Format: +1-555-123-4567 or 5551234567",
        placeholder="+1-555-123-4567",
    )

    # State selection
    state = st.selectbox(
        "State *",
        options=US_STATES,
        key="prospect_state",
        help="Which US state are you located in?",
    )

    # Consent checkbox
    st.markdown("---")
    consent = st.checkbox(
        "I understand this is an AI intake assistant and not a lawyer *",
        value=False,
        key="prospect_consent",
    )

    # Check if all fields are filled
    all_fields_filled = bool(
        first_name
        and first_name.strip()
        and last_name
        and last_name.strip()
        and email
        and email.strip()
        and phone
        and phone.strip()
        and state
        and state.strip()
        and consent
    )

    # Submit button
    if st.button(
        "Start Intake Conversation",
        disabled=not all_fields_filled,
        type="primary",
        use_container_width=True,
    ):
        # Build prospect data
        prospect_data = {
            "first_name": first_name.strip() if first_name else "",
            "last_name": last_name.strip() if last_name else "",
            "email": email.strip() if email else "",
            "phone": phone.strip() if phone else "",
            "state": state if state else "",
            "source_channel": "streamlit_web",
            "consent_status": "pending",
        }

        # Validate
        is_valid, error_message = validate_prospect_data(prospect_data)

        if not is_valid:
            st.error(error_message)
        else:
            # Call callback with validated data
            on_submit_callback(prospect_data)

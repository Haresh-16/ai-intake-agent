"""Main Streamlit application for defendant intake UI."""

import sys
from pathlib import Path

# Add parent directory to path for absolute imports
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

import streamlit as st
from datetime import datetime
import httpx

from streamlit_app.config import config
from streamlit_app.api_client import IntakeAPIClient
from streamlit_app.utils.session_state import (
    initialize_session_state,
    reset_session_state,
    get_stage_index,
)
from streamlit_app.components.compliance_banner import render_compliance_banner
from streamlit_app.components.prospect_form import render_prospect_form
from streamlit_app.components.progress_tracker import render_progress_tracker
from streamlit_app.components.chat_interface import render_chat_interface
from streamlit_app.components.summary_view import render_summary_view


# Configure Streamlit page
st.set_page_config(
    page_title=config.app_title,
    page_icon=config.page_icon,
    layout=config.layout,
    initial_sidebar_state=config.initial_sidebar_state,
)


def handle_prospect_form_submit(prospect_data):
    """Handle prospect form submission.

    Args:
        prospect_data: Validated prospect data dict
    """
    # Store prospect data and transition to chat
    st.session_state.prospect_data = prospect_data
    st.session_state.flow_state = "chat_active"

    # Add initial agent greeting
    st.session_state.messages.append(
        {
            "role": "agent",
            "content": (
                "Hello! I am an AI intake assistant, not a lawyer. "
                "This chat is not legal advice and does not create an "
                "attorney-client relationship. Are you comfortable continuing?"
            ),
            "timestamp": datetime.now().isoformat(),
        }
    )

    st.rerun()


def handle_send_message(user_input: str):
    """Handle user message submission.

    Args:
        user_input: Message content from the user
    """
    # Add user message to UI immediately (optimistic update)
    st.session_state.messages.append(
        {
            "role": "prospect",
            "content": user_input,
            "timestamp": datetime.now().isoformat(),
        }
    )

    try:
        # Call backend API
        api_client = IntakeAPIClient(config.backend_url)
        response = api_client.send_message(
            conversation_id=st.session_state.conversation_id,
            prospect_data=st.session_state.prospect_data,
            content=user_input,
        )

        # Update session state with response
        st.session_state.conversation_id = response["conversation_id"]
        st.session_state.current_stage = response["current_stage"]
        st.session_state.stage_index = get_stage_index(response["current_stage"])
        st.session_state.suggested_next_prompt = response.get(
            "suggested_next_prompt", ""
        )

        # Add suggested prompt as agent message if provided
        if response.get("suggested_next_prompt"):
            st.session_state.messages.append(
                {
                    "role": "agent",
                    "content": response["suggested_next_prompt"],
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # Check for auto-finalization
        if (
            response["current_stage"] == "wrap"
            and config.auto_finalize_on_wrap
        ):
            finalize_conversation()

        # Clear error state on success
        st.session_state.last_api_error = None

    except httpx.ConnectError:
        st.error(
            "Unable to connect to server. Please check your connection and try again."
        )
        st.session_state.last_api_error = "connection_error"

    except httpx.TimeoutException:
        st.error("Request timed out. Please try again.")
        st.session_state.last_api_error = "timeout_error"

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 400:
            st.error("Invalid input. Please check your message and try again.")
        elif e.response.status_code == 404:
            st.error("Conversation not found. Let's start a new intake.")
            reset_session_state()
        elif e.response.status_code >= 500:
            st.error("Server error. Please try again in a moment.")
        else:
            st.error("An error occurred. Please try again.")
        st.session_state.last_api_error = f"http_error_{e.response.status_code}"

    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")
        st.session_state.last_api_error = "unknown_error"

    finally:
        # Rerun to update UI
        st.rerun()


def finalize_conversation():
    """Finalize the conversation and generate intake summary."""
    try:
        with st.spinner("Generating your intake summary..."):
            api_client = IntakeAPIClient(config.backend_url)
            response = api_client.finalize_conversation(
                st.session_state.conversation_id
            )

            # Store summary
            st.session_state.summary = response.get("summary", {})
            st.session_state.flow_state = "finalized"

            # Add agent message about finalization
            st.session_state.messages.append(
                {
                    "role": "agent",
                    "content": (
                        "Your intake has been finalized. "
                        "An attorney will review your information."
                    ),
                    "timestamp": datetime.now().isoformat(),
                }
            )

            # Clear error state on success
            st.session_state.last_api_error = None

    except httpx.ConnectError:
        st.error(
            "Unable to connect to server. Please check your connection and try again."
        )
        st.session_state.last_api_error = "connection_error"

    except httpx.TimeoutException:
        st.error("Request timed out. Please try again.")
        st.session_state.last_api_error = "timeout_error"

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            st.error("Conversation not found. Let's start a new intake.")
            reset_session_state()
        elif e.response.status_code >= 500:
            st.error("Server error. Please try again in a moment.")
        else:
            st.error("An error occurred while finalizing. Please try again.")
        st.session_state.last_api_error = f"http_error_{e.response.status_code}"

    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")
        st.session_state.last_api_error = "unknown_error"


def handle_new_intake():
    """Handle request to start a new intake."""
    reset_session_state()
    st.rerun()


def main():
    """Main application entry point."""
    # Initialize session state
    initialize_session_state()

    # Always show compliance banner
    render_compliance_banner()

    # Show progress tracker if in chat or finalized state
    if st.session_state.flow_state in ["chat_active", "finalized"]:
        if config.show_stage_progress:
            render_progress_tracker(
                st.session_state.current_stage,
                st.session_state.stage_index,
            )

    # Route based on flow state
    if st.session_state.flow_state == "prospect_form":
        render_prospect_form(on_submit_callback=handle_prospect_form_submit)

    elif st.session_state.flow_state == "chat_active":
        st.header("Intake Conversation")

        # Render chat interface
        render_chat_interface(
            messages=st.session_state.messages,
            on_send_message=handle_send_message,
            suggested_prompt=st.session_state.suggested_next_prompt,
            show_timestamps=config.show_timestamps,
        )

    elif st.session_state.flow_state == "finalized":
        # Render summary view
        render_summary_view(
            summary=st.session_state.summary,
            on_new_intake=handle_new_intake,
        )


if __name__ == "__main__":
    main()

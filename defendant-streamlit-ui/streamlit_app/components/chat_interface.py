"""Chat interface component for intake conversations."""

import streamlit as st
from typing import List, Dict, Any, Callable
from datetime import datetime


def render_chat_interface(
    messages: List[Dict[str, Any]],
    on_send_message: Callable[[str], None],
    suggested_prompt: str = "",
    show_timestamps: bool = False,
) -> None:
    """Render the chat interface with message history and input.

    Displays all messages in the conversation and provides an input area
    for the prospect to send new messages.

    Args:
        messages: List of message dicts with role, content, and timestamp
        on_send_message: Callback function to call when user sends a message
        suggested_prompt: Optional suggested prompt to display as hint
        show_timestamps: Whether to show timestamps on messages
    """
    # Display message history
    for msg in messages:
        role = msg.get("role", "prospect")
        content = msg.get("content", "")
        timestamp = msg.get("timestamp", "")

        if role == "prospect":
            with st.chat_message("user", avatar="👤"):
                st.write(content)
                if show_timestamps and timestamp:
                    st.caption(timestamp)

        elif role == "agent":
            with st.chat_message("assistant", avatar="🤖"):
                st.write(content)
                if show_timestamps and timestamp:
                    st.caption(timestamp)

        elif role == "system":
            st.info(content)

    # Input area
    st.markdown("---")

    # Use a container for the input to keep it at the bottom
    with st.container():
        user_input = st.text_area(
            "Your message:",
            key="user_input",
            placeholder="Type your message here...",
            height=100,
            help="Press Ctrl+Enter to send or click the Send button below",
        )

        col1, col2 = st.columns([1, 5])
        with col1:
            send_button = st.button("Send", type="primary", use_container_width=True)

        if send_button and user_input.strip():
            # Clear the input by calling the callback
            on_send_message(user_input.strip())
            # Note: st.rerun() will be called by the callback to refresh the UI

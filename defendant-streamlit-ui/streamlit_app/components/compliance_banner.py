"""Compliance disclosure banner component."""

import streamlit as st


def render_compliance_banner():
    """Render the non-dismissible compliance disclosure banner.

    This banner displays critical legal disclaimers and must be visible
    at all times to maintain compliance boundaries.
    """
    st.markdown(
        """
        <div style='background-color: #fff3cd; border-left: 5px solid #856404;
                    padding: 15px; margin-bottom: 20px; border-radius: 5px;'>
            <h3 style='color: #856404; margin-top: 0;'>⚠️ IMPORTANT DISCLOSURE</h3>
            <ul style='color: #856404; margin-bottom: 0;'>
                <li>This is an AI intake assistant, NOT a lawyer</li>
                <li>This chat does NOT provide legal advice</li>
                <li>This chat does NOT create an attorney-client relationship</li>
                <li>All information will be reviewed by a human attorney</li>
                <li>No case decisions are made by the AI system</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

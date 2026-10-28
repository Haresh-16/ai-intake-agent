"""Progress tracker component for intake stages."""

import streamlit as st
from streamlit_app.utils.formatters import format_stage_label


def render_progress_tracker(current_stage: str, stage_index: int) -> None:
    """Render visual progress indicator for intake stages.

    Displays a progress bar and current stage label to help the prospect
    understand where they are in the intake process.

    Args:
        current_stage: Current intake stage name
        stage_index: Index of current stage (0-8)
    """
    total_stages = 9
    progress = (stage_index + 1) / total_stages

    # Progress bar
    st.progress(progress)

    # Stage label
    stage_label = format_stage_label(current_stage)
    st.caption(f"Stage {stage_index + 1} of {total_stages}: {stage_label}")

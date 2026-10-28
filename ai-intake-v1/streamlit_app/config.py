"""Configuration for Streamlit defendant intake UI."""

from pydantic_settings import BaseSettings


class StreamlitConfig(BaseSettings):
    """Streamlit application configuration."""

    # Application settings
    app_title: str = "Legal Intake Assistant"
    page_icon: str = "⚖️"
    layout: str = "centered"  # or "wide"
    initial_sidebar_state: str = "collapsed"

    # Backend integration
    backend_url: str = "http://localhost:8000"

    # Feature flags
    show_stage_progress: bool = True
    auto_finalize_on_wrap: bool = True
    show_timestamps: bool = False

    # Styling
    primary_color: str = "#1f77b4"
    background_color: str = "#ffffff"
    secondary_background_color: str = "#f0f2f6"
    text_color: str = "#262730"

    class Config:
        """Pydantic configuration."""

        env_prefix = "STREAMLIT_"
        env_file = ".env.streamlit"
        extra = "ignore"


# Global config instance
config = StreamlitConfig()

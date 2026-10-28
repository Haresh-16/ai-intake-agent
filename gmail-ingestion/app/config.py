from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Intake Agent V1"
    env: str = "dev"
    database_url: str = "sqlite+aiosqlite:///./ai_intake_v1.db"
    outbound_kill_switch: bool = False

    # LLM Provider Configuration
    # Default: Groq (OpenAI-compatible API) for development/shadow mode
    # Set llm_stub_mode=False and provide llm_api_key to enable real LLM calls
    llm_provider: str = "openai_compatible"
    llm_model_id: str = "llama-3.1-70b-versatile"
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_timeout_seconds: int = 45
    llm_stub_mode: bool = True

    # Gmail Integration Configuration
    # Per build brief Section 13: Read-only access for attorney decision extraction
    # Service account with domain-wide delegation and gmail.readonly scope
    gmail_service_account_json: str | None = None  # JSON string of service account credentials
    gmail_enabled: bool = False  # Enable Gmail ingestion features
    gmail_default_mailbox: str = ""  # Default attorney mailbox for sync
    gmail_confidence_threshold: float = 0.7  # Min confidence for auto-accept extraction

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

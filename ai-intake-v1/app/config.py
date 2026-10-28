from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Intake Agent V1"
    env: str = "dev"
    database_url: str = "sqlite+aiosqlite:///./ai_intake_v1.db"
    outbound_kill_switch: bool = False

    # LLM Provider Configuration
    # Supported providers:
    # - "ollama": Local Ollama server (recommended, no API key needed)
    # - "openai_compatible": Groq, OpenAI, etc. (requires API key)
    # - Set llm_stub_mode=True to use heuristic stub (no LLM calls)
    llm_provider: str = "ollama"
    llm_model_id: str = "llama3.1:8b"
    llm_api_key: str | None = None
    llm_base_url: str = "http://localhost:11434"
    llm_timeout_seconds: int = 120
    llm_stub_mode: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

import asyncio
from unittest.mock import patch

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings
from app.db import Base
from app.schemas import PracticeArea, ProspectInput
from app.services.llm_agent_core import OpenAICompatibleClient, StubLLMClient, get_llm_client
from app.services.summary_generator import generate_summary


async def _run():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with Session() as session:
        summary = await generate_summary(
            session,
            "conv-1",
            ProspectInput(first_name="Ada", state="CA"),
            "I keep getting calls on my mobile from a debt collector. They called many times and I have call logs and screenshots. They also talked about a debt.",
        )
        assert summary.primary_practice_area in {PracticeArea.TCPA, PracticeArea.FDCPA}
        assert "classification" in summary.llm_request_metadata
        assert summary.agent_version
    await engine.dispose()


def test_phase2_llm_flow():
    asyncio.run(_run())


def test_provider_selection_stub_mode_true():
    """Test that stub client is used when stub_mode is True"""
    with patch("app.services.llm_agent_core.settings") as mock_settings:
        mock_settings.llm_provider = "openai_compatible"
        mock_settings.llm_stub_mode = True
        mock_settings.llm_api_key = "sk-test-key"
        client = get_llm_client()
        assert isinstance(client, StubLLMClient), "Should use stub when stub_mode=True even with API key"


def test_provider_selection_missing_api_key():
    """Test that stub client is used when API key is missing"""
    with patch("app.services.llm_agent_core.settings") as mock_settings:
        mock_settings.llm_provider = "openai_compatible"
        mock_settings.llm_stub_mode = False
        mock_settings.llm_api_key = None
        client = get_llm_client()
        assert isinstance(client, StubLLMClient), "Should use stub when API key is missing"


def test_provider_selection_empty_api_key():
    """Test that stub client is used when API key is empty string"""
    with patch("app.services.llm_agent_core.settings") as mock_settings:
        mock_settings.llm_provider = "openai_compatible"
        mock_settings.llm_stub_mode = False
        mock_settings.llm_api_key = ""
        client = get_llm_client()
        assert isinstance(client, StubLLMClient), "Should use stub when API key is empty"


def test_provider_selection_real_client():
    """Test that real client is used when properly configured"""
    with patch("app.services.llm_agent_core.settings") as mock_settings:
        mock_settings.llm_provider = "openai_compatible"
        mock_settings.llm_stub_mode = False
        mock_settings.llm_api_key = "sk-test-key"
        client = get_llm_client()
        assert isinstance(client, OpenAICompatibleClient), "Should use real client when API key present and stub_mode=False"


def test_provider_selection_wrong_provider():
    """Test that stub client is used when provider is not openai_compatible"""
    with patch("app.services.llm_agent_core.settings") as mock_settings:
        mock_settings.llm_provider = "some_other_provider"
        mock_settings.llm_stub_mode = False
        mock_settings.llm_api_key = "sk-test-key"
        client = get_llm_client()
        assert isinstance(client, StubLLMClient), "Should use stub when provider is not openai_compatible"


def test_stub_client_preserves_metadata():
    """Test that stub client still returns proper metadata for audit"""
    client = StubLLMClient()
    result, metadata, raw = asyncio.run(client.classify("I got robocalls on my cell phone"))
    assert metadata["stubbed"] is True
    assert metadata["temperature"] == 0.0
    assert "raw_response_preview" in metadata
    assert result.primary_practice_area == PracticeArea.TCPA

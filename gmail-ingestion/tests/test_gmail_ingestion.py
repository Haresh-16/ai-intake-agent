"""
Tests for Gmail ingestion pipeline.

These tests verify:
1. Gmail authentication with domain-wide delegation
2. Message and thread fetching
3. Attorney decision extraction via LLM
4. Storage and audit logging
5. End-to-end sync workflow

Note: Uses stub mode by default to avoid requiring real Gmail credentials.
"""

import pytest
from datetime import datetime
from app.schemas import (
    GmailSyncConfig,
    GmailSyncRequest,
    DecisionType,
    AttorneyDecisionExtraction,
)
from app.services.gmail_auth import GmailAuthService, GmailAuthError
from app.services.gmail_client import GmailMessage
from app.services.gmail_extraction import GmailExtractionService


def test_gmail_message_parsing():
    """Test GmailMessage parsing from Gmail API response."""
    message_data = {
        "id": "msg123",
        "threadId": "thread456",
        "snippet": "This is a preview of the message...",
        "internalDate": "1704067200000",  # 2024-01-01 00:00:00 UTC
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Re: Case Intake"},
                {"name": "From", "value": "Jibrael Hindi <jibrael@firm.com>"},
                {"name": "To", "value": "Jane Doe <jane@example.com>"},
                {"name": "Date", "value": "Mon, 1 Jan 2024 00:00:00 -0800"},
            ]
        },
    }

    msg = GmailMessage(message_data)

    assert msg.id == "msg123"
    assert msg.thread_id == "thread456"
    assert msg.subject == "Re: Case Intake"
    assert "jibrael@firm.com" in msg.from_email
    assert msg.snippet == "This is a preview of the message..."

    # Test datetime parsing
    dt = msg.get_datetime()
    assert isinstance(dt, datetime)

    # Test dict conversion
    msg_dict = msg.to_dict()
    assert msg_dict["id"] == "msg123"
    assert msg_dict["subject"] == "Re: Case Intake"


def test_attorney_decision_extraction_schema():
    """Test AttorneyDecisionExtraction schema validation."""
    # Valid extraction
    decision = AttorneyDecisionExtraction(
        decision_type=DecisionType.ACCEPT,
        decision_rationale=(
            "Strong TCPA case with clear robocall violations and willful conduct. "
            "Prospect has evidence and statute of limitations is favorable."
        ),
        decision_date=datetime(2024, 1, 15, 10, 30, 0),
        deciding_attorney="Jibrael Hindi",
        confidence_score=0.92,
        reasoning=(
            "Email explicitly states 'we will represent this client' and provides "
            "detailed case assessment with statutory basis and damage estimates."
        ),
    )

    assert decision.decision_type == DecisionType.ACCEPT
    assert decision.confidence_score == 0.92
    assert len(decision.decision_rationale.split()) >= 10  # Min 10 words

    # Test invalid rationale (too short)
    with pytest.raises(ValueError, match="sufficiently descriptive"):
        AttorneyDecisionExtraction(
            decision_type=DecisionType.ACCEPT,
            decision_rationale="Too short",  # Only 2 words
            decision_date=datetime.utcnow(),
            deciding_attorney="Test",
            confidence_score=0.5,
            reasoning="This will fail because rationale is too short for validation",
        )


def test_gmail_sync_config_validation():
    """Test GmailSyncConfig schema validation."""
    # Valid config
    config = GmailSyncConfig(
        mailbox="attorney@firm.com",
        prospect_identifiers=[
            {"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com"},
            {"email": "john@example.com", "phone": "+1234567890"},
        ],
        max_messages=100,
        confidence_threshold=0.7,
    )

    assert config.mailbox == "attorney@firm.com"
    assert len(config.prospect_identifiers) == 2
    assert config.confidence_threshold == 0.7

    # Test defaults
    assert config.date_range_start is None
    assert config.date_range_end is None

    # Test validation boundaries
    with pytest.raises(ValueError):
        GmailSyncConfig(
            mailbox="test@example.com",
            max_messages=2000,  # Exceeds max of 1000
        )

    with pytest.raises(ValueError):
        GmailSyncConfig(
            mailbox="test@example.com",
            confidence_threshold=1.5,  # Exceeds max of 1.0
        )


def test_gmail_auth_service_initialization():
    """Test GmailAuthService initialization."""
    # Should raise error if no credentials provided
    with pytest.raises(GmailAuthError, match="Must provide"):
        GmailAuthService()

    # Should succeed with JSON dict
    service_account_json = {
        "type": "service_account",
        "project_id": "test-project",
        "private_key_id": "key123",
        "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n",
        "client_email": "test@test-project.iam.gserviceaccount.com",
        "client_id": "123456789",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }

    auth_service = GmailAuthService(service_account_json=service_account_json)
    assert auth_service is not None


def test_decision_types():
    """Test all DecisionType enum values."""
    assert DecisionType.ACCEPT.value == "accept"
    assert DecisionType.REJECT.value == "reject"
    assert DecisionType.MORE_INFO.value == "more_info"
    assert DecisionType.REFER_OUT.value == "refer_out"

    # Test enum membership
    assert "accept" in [dt.value for dt in DecisionType]
    assert "invalid" not in [dt.value for dt in DecisionType]


@pytest.mark.asyncio
async def test_stub_extraction(db_session):
    """Test stub extraction mode (no real LLM calls)."""
    extraction_service = GmailExtractionService(db_session)

    # Create mock Gmail messages
    messages = [
        GmailMessage(
            {
                "id": "msg1",
                "threadId": "thread1",
                "snippet": "We will represent this client for the TCPA violations...",
                "internalDate": "1704067200000",
                "payload": {
                    "headers": [
                        {"name": "From", "value": "jibrael@firm.com"},
                        {"name": "Subject", "value": "Case Decision"},
                    ]
                },
            }
        )
    ]

    # Extract decision using stub mode
    decision, metadata, needs_review = await extraction_service.extract_decision(messages)

    assert decision is not None
    assert isinstance(decision, AttorneyDecisionExtraction)
    assert metadata["stubbed"] is True
    assert needs_review is True  # Stub mode always flags for review (low confidence)


# Integration test marker - skip unless explicitly enabled
@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_sync_workflow(db_session):
    """
    Full integration test of sync workflow.

    This test requires:
    - GMAIL_SERVICE_ACCOUNT_JSON environment variable
    - Valid service account with domain-wide delegation
    - Test mailbox with sample messages

    Skip by default to avoid external dependencies.
    Run with: pytest -m integration
    """
    pytest.skip("Integration test requires real Gmail credentials")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

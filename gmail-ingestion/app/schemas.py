from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PracticeArea(str, Enum):
    TCPA = "TCPA"
    FCRA = "FCRA"
    FDCPA = "FDCPA"
    MASS_ARB = "MASS_ARB"
    UNKNOWN_CONSUMER = "UNKNOWN_CONSUMER"
    WRONG_FIT = "WRONG_FIT"


class AgentRecommendation(str, Enum):
    ROUTE_TO_ATTORNEY = "route_to_attorney"
    ROUTE_TO_INTAKE_REVIEW = "route_to_intake_review"
    REQUEST_MORE_EVIDENCE = "request_more_evidence"
    WRONG_FIT_CLOSE = "wrong_fit_close"


class DefendantRole(str, Enum):
    CALLER = "caller"
    COLLECTOR = "collector"
    FURNISHER = "furnisher"
    BUREAU = "bureau"
    OTHER = "other"


class SecondaryPracticeArea(BaseModel):
    area: str
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    source: Literal["rule_based", "llm_inferred"] = "rule_based"


class Defendant(BaseModel):
    name: str
    role: DefendantRole
    pattern_bank_hit: bool = False


class ComplianceCheck(BaseModel):
    no_legal_advice_given: bool
    no_outcome_promised: bool
    no_acr_implied: bool
    disclosure_logged: bool


class ProspectInput(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    state: str | None = None
    source_channel: str = "web_form"
    consent_status: str = "pending"
    external_ids: dict[str, str] = Field(default_factory=dict)


class IntakeSummary(BaseModel):
    conversation_id: str
    prospect: ProspectInput
    primary_practice_area: PracticeArea
    primary_confidence: float = Field(ge=0.0, le=1.0)
    secondary_practice_areas: list[SecondaryPracticeArea] = Field(default_factory=list)
    fact_pattern: str = Field(min_length=20, max_length=2000)
    defendants: list[Defendant] = Field(default_factory=list)
    evidence_collected: list[str] = Field(default_factory=list)
    evidence_requested: list[str] = Field(default_factory=list)
    evidence_missing: list[str] = Field(default_factory=list)
    cross_practice_flag: bool
    follow_up_question: str
    agent_recommendation: AgentRecommendation
    compliance_check: ComplianceCheck
    agent_version: str
    llm_request_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("fact_pattern")
    @classmethod
    def validate_fact_pattern(cls, value: str) -> str:
        compact = " ".join(value.split())
        if len(compact.split()) < 12:
            raise ValueError("fact_pattern must be sufficiently descriptive")
        return compact

    @field_validator("evidence_missing")
    @classmethod
    def validate_missing_subset(cls, value: list[str], info):
        requested = set(info.data.get("evidence_requested", []))
        if not set(value).issubset(requested):
            raise ValueError("evidence_missing must be subset of evidence_requested")
        return value


class MessageCreate(BaseModel):
    conversation_id: str | None = None
    prospect: ProspectInput
    role: Literal["prospect", "agent", "reviewer", "system"]
    content: str


class APIMessageResponse(BaseModel):
    conversation_id: str
    sanitized_content: str
    suggested_next_prompt: str
    current_stage: str


class ConversationDetail(BaseModel):
    id: str
    status: str
    channel: str
    started_at: datetime
    messages: list[dict]
    summary: dict | None = None


class ReviewAction(BaseModel):
    review_status: Literal["approved", "modified", "rejected"]
    reviewer_id: str
    reviewer_note: str | None = None
    final_disposition: str | None = None


class FollowUpTaskView(BaseModel):
    id: str
    conversation_id: str
    due_at: datetime
    status: str
    sequence_number: int
    evidence_items: list[str]
    template_version: str


class LLMClassificationResult(BaseModel):
    primary_practice_area: PracticeArea
    primary_confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(min_length=8, max_length=500)


class LLMEvidenceResult(BaseModel):
    evidence_requested: list[str] = Field(min_length=1)
    follow_up_question: str = Field(min_length=10, max_length=300)


class LLMStructuredSummary(BaseModel):
    primary_practice_area: PracticeArea
    primary_confidence: float = Field(ge=0.0, le=1.0)
    fact_pattern: str = Field(min_length=20, max_length=2000)
    follow_up_question: str = Field(min_length=10, max_length=300)
    agent_recommendation: AgentRecommendation


class LLMRequestMetadata(BaseModel):
    provider: str
    model_id: str
    operation: str
    prompt_version: str
    prompt_hash: str
    request_id: str
    stubbed: bool = False
    temperature: float = 0.0
    prompt_tokens_estimate: int | None = None
    completion_tokens_estimate: int | None = None
    raw_response_preview: str | None = None

    model_config = ConfigDict(extra="allow")


# ==================== Gmail Ingestion Schemas ====================


class DecisionType(str, Enum):
    """Attorney decision types extracted from Gmail."""

    ACCEPT = "accept"
    REJECT = "reject"
    MORE_INFO = "more_info"
    REFER_OUT = "refer_out"


class AttorneyDecisionExtraction(BaseModel):
    """
    LLM-extracted attorney decision from Gmail thread.
    Used for training corpus ingestion.
    """

    decision_type: DecisionType
    decision_rationale: str = Field(min_length=20, max_length=2000)
    decision_date: datetime
    deciding_attorney: str = Field(min_length=2, max_length=100)
    confidence_score: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(
        min_length=20, max_length=1000
    )  # Why the LLM classified this way

    @field_validator("decision_rationale")
    @classmethod
    def validate_rationale(cls, value: str) -> str:
        """Ensure rationale is sufficiently descriptive."""
        compact = " ".join(value.split())
        if len(compact.split()) < 10:
            raise ValueError("decision_rationale must be sufficiently descriptive (min 10 words)")
        return compact


class GmailSyncConfig(BaseModel):
    """Configuration for Gmail sync operation."""

    mailbox: str = Field(description="Email address of mailbox to sync")
    prospect_identifiers: list[dict[str, str]] = Field(
        description="List of prospect identifiers to match (name, email, phone)",
        default_factory=list,
    )
    date_range_start: datetime | None = Field(
        None, description="Start date for email search (optional)"
    )
    date_range_end: datetime | None = Field(None, description="End date for email search (optional)")
    query_filter: str | None = Field(
        None, description="Additional Gmail search query (e.g., 'from:jibrael@')"
    )
    max_messages: int = Field(100, ge=1, le=1000, description="Max messages to fetch per sync")
    confidence_threshold: float = Field(
        0.7, ge=0.0, le=1.0, description="Minimum confidence to auto-accept extraction"
    )


class GmailSyncStatus(BaseModel):
    """Status response for Gmail sync operation."""

    sync_id: str
    sync_type: str
    mailbox: str
    status: Literal["pending", "running", "completed", "failed"]
    messages_fetched: int
    threads_processed: int
    decisions_extracted: int
    decisions_flagged_for_review: int
    started_at: datetime
    completed_at: datetime | None
    error_message: str | None
    correlation_id: str


class AttorneyDecisionDetail(BaseModel):
    """Attorney decision detail for API responses."""

    id: str
    prospect_id: str | None
    conversation_id: str | None
    gmail_message_id: str
    gmail_thread_id: str
    decision_type: DecisionType
    decision_rationale: str
    decision_date: datetime
    deciding_attorney: str
    confidence_score: float
    requires_human_review: bool
    raw_email_subject: str | None
    raw_email_snippet: str | None
    created_at: datetime
    review_status: str
    extraction_metadata: dict[str, Any]


class GmailSyncRequest(BaseModel):
    """Request to trigger Gmail sync."""

    config: GmailSyncConfig
    initiated_by: str = Field(description="User or system initiating the sync")

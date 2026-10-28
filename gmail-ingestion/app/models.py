from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> str:
    return str(uuid4())


def _utcnow() -> datetime:
    return datetime.utcnow()


class Prospect(Base):
    __tablename__ = "prospects"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    external_ids: Mapped[dict] = mapped_column(JSON, default=dict)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    state: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source_channel: Mapped[str] = mapped_column(String(50), default="ghl_chat")
    consent_status: Mapped[str] = mapped_column(String(30), default="pending")
    status: Mapped[str] = mapped_column(String(30), default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    conversations: Mapped[list[Conversation]] = relationship(back_populates="prospect")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    prospect_id: Mapped[str] = mapped_column(ForeignKey("prospects.id"))
    channel: Mapped[str] = mapped_column(String(50), default="ghl_chat")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active")
    agent_version: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    prospect: Mapped[Prospect] = relationship(back_populates="conversations")
    messages: Mapped[list[Message]] = relationship(back_populates="conversation", cascade="all, delete-orphan")
    summaries: Mapped[list[IntakeSummaryRecord]] = relationship(back_populates="conversation", cascade="all, delete-orphan")
    follow_ups: Mapped[list[FollowUpTask]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"))
    role: Mapped[str] = mapped_column(String(30))
    content: Mapped[str] = mapped_column(Text)
    tool_calls: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    model_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class IntakeSummaryRecord(Base):
    __tablename__ = "intake_summaries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"))
    primary_practice_area: Mapped[str] = mapped_column(String(40))
    primary_confidence: Mapped[str] = mapped_column(String(10))
    secondary_practice_areas: Mapped[list] = mapped_column(JSON, default=list)
    fact_pattern: Mapped[str] = mapped_column(Text)
    defendants: Mapped[list] = mapped_column(JSON, default=list)
    evidence_collected: Mapped[list] = mapped_column(JSON, default=list)
    evidence_requested: Mapped[list] = mapped_column(JSON, default=list)
    evidence_missing: Mapped[list] = mapped_column(JSON, default=list)
    cross_practice_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    follow_up_question: Mapped[str] = mapped_column(Text)
    agent_recommendation: Mapped[str] = mapped_column(String(50))
    review_status: Mapped[str] = mapped_column(String(30), default="pending")
    reviewer_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    final_disposition: Mapped[str | None] = mapped_column(String(100), nullable=True)
    compliance_check: Mapped[dict] = mapped_column(JSON, default=dict)
    agent_version: Mapped[str] = mapped_column(String(200))
    raw_summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    conversation: Mapped[Conversation] = relationship(back_populates="summaries")


class LLMCallRecord(Base):
    __tablename__ = "llm_call_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    conversation_id: Mapped[str | None] = mapped_column(ForeignKey("conversations.id"), nullable=True)
    message_id: Mapped[str | None] = mapped_column(ForeignKey("messages.id"), nullable=True)
    intake_summary_id: Mapped[str | None] = mapped_column(ForeignKey("intake_summaries.id"), nullable=True)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    model_id: Mapped[str] = mapped_column(String, nullable=False)
    operation: Mapped[str] = mapped_column(String, nullable=False)
    prompt_version: Mapped[str] = mapped_column(String, nullable=False)
    prompt_hash: Mapped[str] = mapped_column(String, nullable=False)
    request_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    response_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    raw_response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class FollowUpTask(Base):
    __tablename__ = "follow_up_tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"))
    template_id: Mapped[str] = mapped_column(String(100))
    template_version: Mapped[str] = mapped_column(String(30), default="v1")
    attempt_number: Mapped[int] = mapped_column(Integer)
    due_at: Mapped[datetime] = mapped_column(DateTime)
    channel: Mapped[str] = mapped_column(String(30), default="sms")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="scheduled")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    stop_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    conversation: Mapped[Conversation] = relationship(back_populates="follow_ups")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[str] = mapped_column(String(100))
    before_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)


class GmailAttorneyDecision(Base):
    """
    Stores attorney decisions extracted from Gmail messages.
    Read-only ingestion from firm Gmail for training corpus.
    """

    __tablename__ = "gmail_attorney_decisions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    prospect_id: Mapped[str | None] = mapped_column(ForeignKey("prospects.id"), nullable=True)
    conversation_id: Mapped[str | None] = mapped_column(ForeignKey("conversations.id"), nullable=True)
    gmail_message_id: Mapped[str] = mapped_column(String(100), index=True)  # Gmail API message ID
    gmail_thread_id: Mapped[str] = mapped_column(String(100), index=True)  # Gmail API thread ID
    decision_type: Mapped[str] = mapped_column(
        String(30)
    )  # 'accept' | 'reject' | 'more_info' | 'refer_out'
    decision_rationale: Mapped[str] = mapped_column(Text)
    decision_date: Mapped[datetime] = mapped_column(DateTime)
    deciding_attorney: Mapped[str] = mapped_column(String(100))
    confidence_score: Mapped[str] = mapped_column(String(10))  # 0.0 to 1.0 stored as string
    requires_human_review: Mapped[bool] = mapped_column(
        Boolean, default=False
    )  # Flag for low-confidence
    extraction_metadata: Mapped[dict] = mapped_column(
        JSON, default=dict
    )  # LLM request metadata, prompt hash
    raw_email_subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_email_snippet: Mapped[str | None] = mapped_column(
        String(1000), nullable=True
    )  # Preview only, not full content
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewer_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    review_status: Mapped[str] = mapped_column(
        String(30), default="pending"
    )  # 'pending' | 'confirmed' | 'rejected' | 'modified'


class GmailSyncRecord(Base):
    """
    Tracks Gmail sync operations for auditability.
    Each sync run creates one record.
    """

    __tablename__ = "gmail_sync_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    sync_type: Mapped[str] = mapped_column(
        String(50), default="attorney_decisions"
    )  # Type of sync operation
    mailbox: Mapped[str] = mapped_column(String(255))  # Email address of mailbox synced
    query_params: Mapped[dict] = mapped_column(
        JSON, default=dict
    )  # Search query used (filters, date range, etc.)
    messages_fetched: Mapped[int] = mapped_column(Integer, default=0)
    threads_processed: Mapped[int] = mapped_column(Integer, default=0)
    decisions_extracted: Mapped[int] = mapped_column(Integer, default=0)
    decisions_flagged_for_review: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(
        String(30), default="pending"
    )  # 'pending' | 'running' | 'completed' | 'failed'
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(100), index=True)  # For audit trail
    initiated_by: Mapped[str] = mapped_column(String(100))  # User or system that triggered sync

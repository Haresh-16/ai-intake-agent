"""
API routes for Gmail ingestion operations.

Endpoints:
- POST /api/gmail/sync - Trigger sync operation
- GET /api/gmail/sync/{sync_id}/status - Get sync status
- GET /api/gmail/decisions - List extracted decisions
- GET /api/gmail/decisions/{decision_id} - Get decision details

Security:
- Read-only Gmail operations
- Full audit logging
- Requires authentication (TODO: add auth middleware)
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import GmailAttorneyDecision, GmailSyncRecord
from app.schemas import (
    AttorneyDecisionDetail,
    DecisionType,
    GmailSyncConfig,
    GmailSyncRequest,
    GmailSyncStatus,
)
from app.services.gmail_auth import GmailAuthService
from app.services.gmail_ingestion import GmailIngestionError, GmailIngestionPipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gmail", tags=["gmail"])


def get_auth_service() -> GmailAuthService:
    """
    Get configured Gmail auth service.

    This dependency loads service account credentials from environment.
    In production, credentials should be securely managed (e.g., secrets manager).
    """
    try:
        # Try to load from environment variable
        service_account_json = GmailAuthService.load_service_account_from_env()
        return GmailAuthService(service_account_json=service_account_json)
    except Exception as e:
        logger.error(f"Failed to initialize Gmail auth service: {e}")
        raise HTTPException(
            status_code=500,
            detail="Gmail authentication not configured. Set GMAIL_SERVICE_ACCOUNT_JSON environment variable.",
        ) from e


@router.post("/sync", response_model=GmailSyncStatus, status_code=202)
async def trigger_sync(
    request: GmailSyncRequest,
    db: AsyncSession = Depends(get_db),
    auth_service: GmailAuthService = Depends(get_auth_service),
) -> GmailSyncStatus:
    """
    Trigger Gmail sync operation to extract attorney decisions.

    This endpoint:
    1. Creates a sync record
    2. Authenticates with Gmail (read-only)
    3. Searches for messages matching prospect identifiers
    4. Extracts attorney decisions using LLM
    5. Stores decisions with audit trail

    **Request Body:**
    ```json
    {
      "config": {
        "mailbox": "attorney@firm.com",
        "prospect_identifiers": [
          {"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com"},
          {"email": "john@example.com"}
        ],
        "date_range_start": "2024-01-01T00:00:00Z",
        "date_range_end": "2024-12-31T23:59:59Z",
        "query_filter": "from:jibrael@",
        "max_messages": 100,
        "confidence_threshold": 0.7
      },
      "initiated_by": "user:admin"
    }
    ```

    **Response:**
    - 202 Accepted - Sync started, returns sync_id for status polling
    - 500 Internal Server Error - Sync failed to start

    **Security:**
    - Read-only Gmail access (gmail.readonly scope)
    - No email writes or sends
    - Full audit trail with correlation IDs

    **Important:**
    This is a potentially long-running operation. Use the sync_id
    to poll for status via GET /api/gmail/sync/{sync_id}/status
    """
    try:
        pipeline = GmailIngestionPipeline(db, auth_service)
        status = await pipeline.run_sync(
            config=request.config, initiated_by=request.initiated_by
        )
        return status

    except GmailIngestionError as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/sync/{sync_id}/status", response_model=GmailSyncStatus)
async def get_sync_status(
    sync_id: str,
    db: AsyncSession = Depends(get_db),
) -> GmailSyncStatus:
    """
    Get status of Gmail sync operation.

    **Path Parameters:**
    - sync_id: ID of sync operation (returned from POST /api/gmail/sync)

    **Response:**
    - 200 OK - Returns sync status
    - 404 Not Found - Sync record not found

    **Status Values:**
    - pending: Sync queued but not started
    - running: Sync in progress
    - completed: Sync finished successfully
    - failed: Sync encountered error

    **Example Response:**
    ```json
    {
      "sync_id": "abc123",
      "sync_type": "attorney_decisions",
      "mailbox": "attorney@firm.com",
      "status": "completed",
      "messages_fetched": 45,
      "threads_processed": 12,
      "decisions_extracted": 8,
      "decisions_flagged_for_review": 2,
      "started_at": "2024-01-15T10:30:00Z",
      "completed_at": "2024-01-15T10:35:00Z",
      "error_message": null,
      "correlation_id": "xyz789"
    }
    ```
    """
    result = await db.execute(select(GmailSyncRecord).where(GmailSyncRecord.id == sync_id))
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=404, detail=f"Sync record {sync_id} not found")

    return GmailSyncStatus(
        sync_id=record.id,
        sync_type=record.sync_type,
        mailbox=record.mailbox,
        status=record.status,
        messages_fetched=record.messages_fetched,
        threads_processed=record.threads_processed,
        decisions_extracted=record.decisions_extracted,
        decisions_flagged_for_review=record.decisions_flagged_for_review,
        started_at=record.started_at,
        completed_at=record.completed_at,
        error_message=record.error_message,
        correlation_id=record.correlation_id,
    )


@router.get("/decisions", response_model=list[AttorneyDecisionDetail])
async def list_decisions(
    db: AsyncSession = Depends(get_db),
    decision_type: DecisionType | None = Query(None, description="Filter by decision type"),
    requires_review: bool | None = Query(None, description="Filter by review status"),
    limit: int = Query(50, ge=1, le=500, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> list[AttorneyDecisionDetail]:
    """
    List extracted attorney decisions.

    **Query Parameters:**
    - decision_type: Filter by decision type (accept/reject/more_info/refer_out)
    - requires_review: Filter by review flag (true/false)
    - limit: Max results (1-500, default 50)
    - offset: Pagination offset (default 0)

    **Response:**
    List of attorney decision records ordered by created_at descending.

    **Example Response:**
    ```json
    [
      {
        "id": "dec123",
        "prospect_id": "pro456",
        "conversation_id": null,
        "gmail_message_id": "msg789",
        "gmail_thread_id": "thread012",
        "decision_type": "accept",
        "decision_rationale": "Strong TCPA case with clear violations...",
        "decision_date": "2024-01-10T15:30:00Z",
        "deciding_attorney": "Jibrael Hindi",
        "confidence_score": 0.92,
        "requires_human_review": false,
        "raw_email_subject": "Re: Case Intake - Jane Doe",
        "raw_email_snippet": "After reviewing the evidence...",
        "created_at": "2024-01-15T10:35:00Z",
        "review_status": "auto_accepted",
        "extraction_metadata": {...}
      }
    ]
    ```

    **Use Cases:**
    - View all high-confidence accepted cases
    - Review low-confidence extractions
    - Audit attorney decision history
    - Build training corpus for agent
    """
    query = select(GmailAttorneyDecision).order_by(desc(GmailAttorneyDecision.created_at))

    # Apply filters
    if decision_type:
        query = query.where(GmailAttorneyDecision.decision_type == decision_type.value)

    if requires_review is not None:
        query = query.where(GmailAttorneyDecision.requires_human_review == requires_review)

    # Apply pagination
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    decisions = result.scalars().all()

    return [_decision_to_detail(d) for d in decisions]


@router.get("/decisions/{decision_id}", response_model=AttorneyDecisionDetail)
async def get_decision(
    decision_id: str,
    db: AsyncSession = Depends(get_db),
) -> AttorneyDecisionDetail:
    """
    Get attorney decision details by ID.

    **Path Parameters:**
    - decision_id: ID of decision record

    **Response:**
    - 200 OK - Returns decision details
    - 404 Not Found - Decision not found

    **Use Cases:**
    - Review specific decision details
    - Verify extraction accuracy
    - Link decision to prospect/conversation
    """
    result = await db.execute(
        select(GmailAttorneyDecision).where(GmailAttorneyDecision.id == decision_id)
    )
    decision = result.scalar_one_or_none()

    if not decision:
        raise HTTPException(status_code=404, detail=f"Decision {decision_id} not found")

    return _decision_to_detail(decision)


def _decision_to_detail(decision: GmailAttorneyDecision) -> AttorneyDecisionDetail:
    """Convert decision model to API response."""
    return AttorneyDecisionDetail(
        id=decision.id,
        prospect_id=decision.prospect_id,
        conversation_id=decision.conversation_id,
        gmail_message_id=decision.gmail_message_id,
        gmail_thread_id=decision.gmail_thread_id,
        decision_type=DecisionType(decision.decision_type),
        decision_rationale=decision.decision_rationale,
        decision_date=decision.decision_date,
        deciding_attorney=decision.deciding_attorney,
        confidence_score=float(decision.confidence_score),
        requires_human_review=decision.requires_human_review,
        raw_email_subject=decision.raw_email_subject,
        raw_email_snippet=decision.raw_email_snippet,
        created_at=decision.created_at,
        review_status=decision.review_status,
        extraction_metadata=decision.extraction_metadata,
    )

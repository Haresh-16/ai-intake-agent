"""
Gmail ingestion pipeline orchestrator.

Per build brief Section 13, this service:
1. Authenticates with Gmail using domain-wide delegation (read-only)
2. Searches for messages related to training corpus prospects
3. Extracts attorney decisions using LLM
4. Stores decisions with full audit trail
5. Flags low-confidence extractions for human review

Architecture:
- Orchestrates gmail_auth, gmail_client, and gmail_extraction services
- Uses deterministic audit logging (app/services/audit.py)
- All operations are read-only (no Gmail writes)
- Full correlation IDs for end-to-end traceability
"""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GmailAttorneyDecision, GmailSyncRecord, Prospect
from app.schemas import GmailSyncConfig, GmailSyncStatus
from app.services.audit import write_audit_log
from app.services.gmail_auth import GmailAuthService
from app.services.gmail_client import GmailClient, GmailClientError
from app.services.gmail_extraction import GmailExtractionService, GmailExtractionError

logger = logging.getLogger(__name__)


class GmailIngestionError(Exception):
    """Raised when ingestion pipeline fails."""

    pass


class GmailIngestionPipeline:
    """
    Orchestrates read-only Gmail ingestion for attorney decision extraction.

    This pipeline:
    1. Creates a sync record for auditability
    2. Authenticates with Gmail using provided service account
    3. Searches for messages matching prospect identifiers
    4. Fetches message threads
    5. Extracts attorney decisions using LLM
    6. Stores decisions with confidence flags
    7. Logs all operations to audit trail
    8. Updates sync record with results

    Security invariants:
    - Read-only Gmail access (gmail.readonly scope)
    - No message writes or sends
    - Full audit trail with correlation IDs
    - PII minimization (metadata/snippets only, no full content)
    """

    def __init__(self, db: AsyncSession, auth_service: GmailAuthService):
        """
        Initialize ingestion pipeline.

        Args:
            db: Database session
            auth_service: Configured Gmail auth service
        """
        self.db = db
        self.auth_service = auth_service
        self.extraction_service = GmailExtractionService(db)

    async def run_sync(
        self, config: GmailSyncConfig, initiated_by: str
    ) -> GmailSyncStatus:
        """
        Run Gmail sync operation.

        Args:
            config: Sync configuration
            initiated_by: User/system initiating sync

        Returns:
            Sync status with results

        Raises:
            GmailIngestionError: If sync fails

        Workflow:
            1. Create sync record (status=pending)
            2. Initialize Gmail client for mailbox
            3. For each prospect identifier:
                a. Build search query
                b. Search messages
                c. Fetch unique threads
                d. Extract decisions
                e. Store results
            4. Update sync record (status=completed/failed)
            5. Return sync status
        """
        correlation_id = str(uuid4())
        sync_id = str(uuid4())

        logger.info(
            f"Starting Gmail sync {sync_id} for mailbox {config.mailbox} "
            f"(correlation_id: {correlation_id})"
        )

        # Create sync record
        sync_record = GmailSyncRecord(
            id=sync_id,
            sync_type="attorney_decisions",
            mailbox=config.mailbox,
            query_params=config.model_dump(),
            status="pending",
            correlation_id=correlation_id,
            initiated_by=initiated_by,
        )
        self.db.add(sync_record)
        await self.db.commit()

        # Audit log sync start
        await write_audit_log(
            db=self.db,
            actor=f"system:{initiated_by}",
            action="gmail.sync.started",
            entity_type="gmail_sync_record",
            entity_id=sync_id,
            before_state=None,
            after_state={"correlation_id": correlation_id, "mailbox": config.mailbox},
        )

        try:
            # Update status to running
            sync_record.status = "running"
            await self.db.commit()

            # Initialize Gmail client
            gmail_client = GmailClient(self.auth_service, config.mailbox)

            # Track results
            all_thread_ids: set[str] = set()
            decisions_extracted = 0
            decisions_flagged = 0

            # Process each prospect identifier
            for prospect_data in config.prospect_identifiers:
                logger.info(f"Processing prospect: {prospect_data}")

                # Build search query
                query = gmail_client.build_prospect_query(
                    first_name=prospect_data.get("first_name"),
                    last_name=prospect_data.get("last_name"),
                    email=prospect_data.get("email"),
                    phone=prospect_data.get("phone"),
                    additional_filter=config.query_filter,
                )

                if not query:
                    logger.warning(f"Empty query for prospect {prospect_data}, skipping")
                    continue

                # Search messages
                try:
                    message_ids, _ = gmail_client.search_messages(
                        query=query, max_results=config.max_messages
                    )
                except GmailClientError as e:
                    logger.error(f"Search failed for query '{query}': {e}")
                    continue

                # Collect unique thread IDs
                for msg_id in message_ids:
                    try:
                        msg = gmail_client.get_message(msg_id, format="minimal")
                        all_thread_ids.add(msg.thread_id)
                    except GmailClientError as e:
                        logger.error(f"Failed to fetch message {msg_id}: {e}")
                        continue

            logger.info(f"Found {len(all_thread_ids)} unique threads to process")

            # Process each thread
            for thread_id in all_thread_ids:
                try:
                    # Fetch thread messages
                    thread_messages = gmail_client.get_thread(thread_id, format="metadata")

                    # Extract decision
                    decision, metadata, needs_review = (
                        await self.extraction_service.extract_decision(
                            thread_messages=thread_messages,
                            confidence_threshold=config.confidence_threshold,
                        )
                    )

                    if decision:
                        # Store decision
                        await self._store_decision(
                            decision=decision,
                            thread_messages=thread_messages,
                            metadata=metadata,
                            requires_review=needs_review,
                            sync_id=sync_id,
                            correlation_id=correlation_id,
                        )

                        decisions_extracted += 1
                        if needs_review:
                            decisions_flagged += 1

                except GmailExtractionError as e:
                    logger.error(f"Extraction failed for thread {thread_id}: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error processing thread {thread_id}: {e}")
                    continue

            # Update sync record with results
            sync_record.messages_fetched = len(message_ids) if message_ids else 0
            sync_record.threads_processed = len(all_thread_ids)
            sync_record.decisions_extracted = decisions_extracted
            sync_record.decisions_flagged_for_review = decisions_flagged
            sync_record.status = "completed"
            sync_record.completed_at = datetime.utcnow()
            await self.db.commit()

            # Audit log completion
            await write_audit_log(
                db=self.db,
                actor=f"system:{initiated_by}",
                action="gmail.sync.completed",
                entity_type="gmail_sync_record",
                entity_id=sync_id,
                before_state={"status": "running"},
                after_state={
                    "status": "completed",
                    "decisions_extracted": decisions_extracted,
                    "decisions_flagged": decisions_flagged,
                },
            )

            logger.info(
                f"Gmail sync {sync_id} completed: {decisions_extracted} decisions extracted, "
                f"{decisions_flagged} flagged for review"
            )

            return self._sync_record_to_status(sync_record)

        except Exception as e:
            logger.error(f"Gmail sync {sync_id} failed: {e}")

            # Update sync record with error
            sync_record.status = "failed"
            sync_record.error_message = str(e)
            sync_record.completed_at = datetime.utcnow()
            await self.db.commit()

            # Audit log failure
            await write_audit_log(
                db=self.db,
                actor=f"system:{initiated_by}",
                action="gmail.sync.failed",
                entity_type="gmail_sync_record",
                entity_id=sync_id,
                before_state={"status": "running"},
                after_state={"status": "failed", "error": str(e)},
            )

            raise GmailIngestionError(f"Sync failed: {e}") from e

    async def _store_decision(
        self,
        decision,
        thread_messages: list,
        metadata: dict,
        requires_review: bool,
        sync_id: str,
        correlation_id: str,
    ) -> None:
        """
        Store extracted attorney decision to database.

        Args:
            decision: Extracted AttorneyDecisionExtraction
            thread_messages: Gmail messages in thread
            metadata: LLM request metadata
            requires_review: Whether human review needed
            sync_id: ID of sync operation
            correlation_id: Correlation ID for audit trail
        """
        # Get first and last message for metadata
        first_msg = thread_messages[0] if thread_messages else None
        last_msg = thread_messages[-1] if len(thread_messages) > 0 else first_msg

        # Try to match to existing prospect (optional)
        prospect_id = await self._match_prospect(thread_messages)

        # Create decision record
        decision_record = GmailAttorneyDecision(
            prospect_id=prospect_id,
            conversation_id=None,  # May be linked later
            gmail_message_id=last_msg.id if last_msg else "",
            gmail_thread_id=first_msg.thread_id if first_msg else "",
            decision_type=decision.decision_type.value,
            decision_rationale=decision.decision_rationale,
            decision_date=decision.decision_date,
            deciding_attorney=decision.deciding_attorney,
            confidence_score=str(decision.confidence_score),
            requires_human_review=requires_review,
            extraction_metadata=metadata,
            raw_email_subject=first_msg.subject if first_msg else None,
            raw_email_snippet=first_msg.snippet[:1000] if first_msg else None,
            review_status="pending" if requires_review else "auto_accepted",
        )

        self.db.add(decision_record)
        await self.db.commit()

        # Audit log decision storage
        await write_audit_log(
            db=self.db,
            actor=f"system:gmail_ingestion:{sync_id}",
            action="gmail.decision.extracted",
            entity_type="gmail_attorney_decision",
            entity_id=decision_record.id,
            before_state=None,
            after_state={
                "decision_type": decision.decision_type.value,
                "confidence": decision.confidence_score,
                "requires_review": requires_review,
                "correlation_id": correlation_id,
            },
        )

        logger.info(
            f"Stored decision {decision_record.id} "
            f"(type={decision.decision_type.value}, confidence={decision.confidence_score:.2f})"
        )

    async def _match_prospect(self, thread_messages: list) -> str | None:
        """
        Try to match Gmail thread to existing prospect.

        Args:
            thread_messages: Messages in thread

        Returns:
            Prospect ID if match found, None otherwise

        Matching strategy:
            1. Extract email addresses from thread
            2. Query prospects by email
            3. Return first match (or None)
        """
        if not thread_messages:
            return None

        # Collect email addresses from thread
        emails = set()
        for msg in thread_messages:
            if msg.from_email:
                # Extract email from "Name <email@domain.com>" format
                if "<" in msg.from_email and ">" in msg.from_email:
                    email = msg.from_email.split("<")[1].split(">")[0].strip()
                    emails.add(email.lower())
                else:
                    emails.add(msg.from_email.lower())

        if not emails:
            return None

        # Query prospects
        for email in emails:
            result = await self.db.execute(
                select(Prospect).where(Prospect.email == email).limit(1)
            )
            prospect = result.scalar_one_or_none()
            if prospect:
                logger.info(f"Matched thread to prospect {prospect.id} via email {email}")
                return prospect.id

        return None

    @staticmethod
    def _sync_record_to_status(record: GmailSyncRecord) -> GmailSyncStatus:
        """Convert sync record to status response."""
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

    async def get_sync_status(self, sync_id: str) -> GmailSyncStatus:
        """
        Get status of sync operation.

        Args:
            sync_id: Sync operation ID

        Returns:
            Sync status

        Raises:
            GmailIngestionError: If sync record not found
        """
        result = await self.db.execute(
            select(GmailSyncRecord).where(GmailSyncRecord.id == sync_id)
        )
        record = result.scalar_one_or_none()

        if not record:
            raise GmailIngestionError(f"Sync record {sync_id} not found")

        return self._sync_record_to_status(record)

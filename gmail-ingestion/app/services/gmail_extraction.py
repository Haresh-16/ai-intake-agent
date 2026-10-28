"""
LLM-powered extraction of attorney decisions from Gmail threads.

Per build brief Section 13:
- Extract decision type (accept/reject/more_info/refer_out)
- Extract rationale
- Extract decision date
- Extract deciding attorney
- Confidence-flag low-confidence extractions for human review

Architecture:
- Uses provider-backed LLM infrastructure from llm_agent_core.py
- Deterministic validation outside the model
- Full audit trail with prompt hash and LLM metadata
- No retention of email content beyond metadata/snippet
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from uuid import uuid4

import httpx
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import LLMCallRecord
from app.schemas import AttorneyDecisionExtraction, DecisionType
from app.services.gmail_client import GmailMessage

logger = logging.getLogger(__name__)


class GmailExtractionError(Exception):
    """Raised when extraction fails."""

    pass


class GmailExtractionService:
    """
    Extracts attorney decisions from Gmail threads using LLM.

    This service:
    1. Takes a Gmail thread (list of messages)
    2. Constructs extraction prompt with compliance constraints
    3. Calls LLM with JSON mode to extract structured decision
    4. Validates extraction with Pydantic schema
    5. Flags low-confidence extractions for human review
    6. Logs all LLM calls to llm_call_records for audit
    """

    EXTRACTION_PROMPT_VERSION = "gmail_attorney_decision_v1"
    CONFIDENCE_THRESHOLD = 0.7  # Default threshold for auto-accept

    def __init__(self, db: AsyncSession):
        """
        Initialize extraction service.

        Args:
            db: Database session for logging LLM calls
        """
        self.db = db

    @staticmethod
    def _build_system_prompt() -> str:
        """
        Build system prompt for attorney decision extraction.

        Returns locked prompt with compliance constraints.
        """
        return """You are an extraction assistant for a law firm's case management system.

Your task is to analyze email threads and identify attorney decisions about prospective client matters.

**Decision Types:**
- "accept": Attorney decided to take the case / represent the client
- "reject": Attorney decided NOT to take the case (wrong fit, conflicts, etc.)
- "more_info": Attorney needs more information before deciding
- "refer_out": Attorney referred the matter to another firm or attorney

**Extraction Rules:**
1. Extract the decision type, rationale, date, and deciding attorney
2. Be conservative - only extract clear, explicit decisions
3. If the decision is ambiguous or unclear, assign lower confidence
4. Do NOT infer decisions from vague statements
5. The rationale should be the attorney's stated reason (not your interpretation)
6. Date should be when the decision was communicated (message date)
7. Attorney name should be extracted from signature, sender, or context

**Output Format:**
Return valid JSON with these exact fields:
{
  "decision_type": "accept|reject|more_info|refer_out",
  "decision_rationale": "The attorney's stated reasoning (10+ words)",
  "decision_date": "ISO 8601 datetime",
  "deciding_attorney": "Attorney name",
  "confidence_score": 0.0-1.0,
  "reasoning": "Why you classified this way (20+ words)"
}

**Confidence Scoring:**
- 0.9-1.0: Explicit decision with clear rationale and attorney identified
- 0.7-0.9: Clear decision but some ambiguity in details
- 0.5-0.7: Decision implied but not explicitly stated
- <0.5: Very uncertain or missing key information

**Important:**
- Flag uncertain extractions with confidence < 0.7
- If no clear decision exists, return confidence 0.0 and decision_type "more_info"
- Never fabricate information - extract only what is present in the thread"""

    @staticmethod
    def _build_user_prompt(thread_messages: list[GmailMessage]) -> str:
        """
        Build user prompt with email thread context.

        Args:
            thread_messages: List of Gmail messages in thread

        Returns:
            Formatted prompt with thread content

        Security note:
            Only includes message metadata and snippets (not full body)
            per build brief requirement for no content retention.
        """
        # Sort messages chronologically
        sorted_messages = sorted(thread_messages, key=lambda m: m.get_datetime())

        thread_text = "**EMAIL THREAD:**\n\n"

        for idx, msg in enumerate(sorted_messages, 1):
            thread_text += f"--- Message {idx} ---\n"
            thread_text += f"From: {msg.from_email}\n"
            thread_text += f"To: {msg.to_email}\n"
            thread_text += f"Date: {msg.date}\n"
            thread_text += f"Subject: {msg.subject}\n"
            thread_text += f"Preview: {msg.snippet}\n\n"

        thread_text += """**TASK:**
Analyze the above email thread and extract the attorney decision if one exists.
Return your response as valid JSON matching the specified format."""

        return thread_text

    async def extract_decision(
        self,
        thread_messages: list[GmailMessage],
        confidence_threshold: float | None = None,
    ) -> tuple[AttorneyDecisionExtraction | None, dict, bool]:
        """
        Extract attorney decision from Gmail thread using LLM.

        Args:
            thread_messages: List of Gmail messages in thread
            confidence_threshold: Minimum confidence to auto-accept (defaults to 0.7)

        Returns:
            Tuple of:
            - Extracted decision (None if extraction failed or confidence too low)
            - LLM request metadata dict
            - requires_human_review flag

        Raises:
            GmailExtractionError: If LLM call fails

        Example:
            ```python
            decision, metadata, needs_review = await service.extract_decision(messages)
            if decision:
                if needs_review:
                    # Flag for human verification
                    pass
                else:
                    # Auto-accept high-confidence extraction
                    pass
            ```
        """
        if confidence_threshold is None:
            confidence_threshold = self.CONFIDENCE_THRESHOLD

        if not thread_messages:
            raise GmailExtractionError("Cannot extract from empty thread")

        # Build prompts
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(thread_messages)

        # Generate prompt hash for audit trail
        prompt_content = system_prompt + user_prompt
        prompt_hash = hashlib.sha256(prompt_content.encode()).hexdigest()

        try:
            # Call LLM
            response_json, llm_meta, raw_response = await self._call_llm(
                system_prompt, user_prompt
            )

            # Build metadata
            metadata = {
                "provider": settings.llm_provider,
                "model_id": settings.llm_model_id,
                "operation": "gmail_attorney_decision_extraction",
                "prompt_version": self.EXTRACTION_PROMPT_VERSION,
                "prompt_hash": prompt_hash,
                "request_id": str(uuid4()),
                "stubbed": llm_meta.get("stubbed", False),
                "temperature": llm_meta.get("temperature", 0.0),
                "raw_response_preview": raw_response[:500] if raw_response else None,
            }

            # Parse and validate response
            try:
                decision = AttorneyDecisionExtraction(**response_json)
            except ValidationError as e:
                logger.error(f"LLM response failed schema validation: {e}")
                logger.error(f"Response JSON: {response_json}")

                # Log failed extraction
                await self._log_llm_call(
                    metadata=metadata,
                    raw_response=raw_response,
                    success=False,
                    error_message=str(e),
                )

                raise GmailExtractionError(f"Extraction validation failed: {e}")

            # Determine if human review needed
            requires_review = decision.confidence_score < confidence_threshold

            # Log successful extraction
            await self._log_llm_call(
                metadata=metadata,
                raw_response=raw_response,
                success=True,
            )

            logger.info(
                f"Extracted {decision.decision_type} decision with confidence {decision.confidence_score:.2f}"
            )

            return decision, metadata, requires_review

        except Exception as e:
            logger.error(f"Gmail extraction failed: {e}")
            raise GmailExtractionError(f"Extraction failed: {e}") from e

    async def _call_llm(
        self, system_prompt: str, user_prompt: str
    ) -> tuple[dict, dict, str]:
        """
        Call LLM with prompts and return structured JSON.

        Args:
            system_prompt: System instructions
            user_prompt: User input with thread content

        Returns:
            Tuple of (response_dict, metadata, raw_response_text)

        Raises:
            GmailExtractionError: If LLM call fails
        """
        # Use stub mode if configured
        if settings.llm_stub_mode or not settings.llm_api_key:
            logger.warning("Using stub mode for Gmail extraction")
            return await self._stub_extraction(user_prompt)

        # Real LLM call via OpenAI-compatible API
        try:
            payload = {
                "model": settings.llm_model_id,
                "temperature": 0.0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            }

            async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
                resp = await client.post(
                    f"{settings.llm_base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()

            # Extract response
            raw_text = data["choices"][0]["message"]["content"]
            response_dict = json.loads(raw_text)

            # Extract usage metadata
            metadata = {
                "stubbed": False,
                "temperature": 0.0,
                "prompt_tokens": data.get("usage", {}).get("prompt_tokens"),
                "completion_tokens": data.get("usage", {}).get("completion_tokens"),
            }

            return response_dict, metadata, raw_text

        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            raise GmailExtractionError(f"LLM call failed: {e}") from e

    async def _stub_extraction(
        self, user_prompt: str
    ) -> tuple[dict, dict, str]:
        """
        Stub implementation for testing without real LLM.

        Returns a conservative "more_info" decision with low confidence.
        """
        response = {
            "decision_type": "more_info",
            "decision_rationale": "Stub extraction mode - requires human review to determine actual decision from email thread context and attorney communication patterns.",
            "decision_date": datetime.utcnow().isoformat(),
            "deciding_attorney": "Unknown (Stub Mode)",
            "confidence_score": 0.3,
            "reasoning": "This is a stub response generated without LLM analysis. Human review is required for accurate decision extraction.",
        }

        metadata = {"stubbed": True, "temperature": 0.0}
        raw_text = json.dumps(response)

        return response, metadata, raw_text

    async def _log_llm_call(
        self,
        metadata: dict,
        raw_response: str,
        success: bool = True,
        error_message: str | None = None,
    ) -> None:
        """
        Log LLM call to database for audit trail.

        Args:
            metadata: LLM request metadata
            raw_response: Raw LLM response text
            success: Whether extraction succeeded
            error_message: Error message if failed
        """
        try:
            call_record = LLMCallRecord(
                conversation_id=None,  # No conversation for Gmail extraction
                message_id=None,
                intake_summary_id=None,
                provider=metadata["provider"],
                model_id=metadata["model_id"],
                operation=metadata["operation"],
                prompt_version=metadata["prompt_version"],
                prompt_hash=metadata["prompt_hash"],
                request_metadata=metadata,
                response_metadata={"success": success, "error": error_message},
                raw_response_text=raw_response[:10000] if raw_response else None,  # Truncate
            )

            self.db.add(call_record)
            await self.db.commit()

        except Exception as e:
            logger.error(f"Failed to log LLM call: {e}")
            # Don't raise - logging failure shouldn't break extraction

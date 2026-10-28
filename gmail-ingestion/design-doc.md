# AI Intake Agent V1 Design Doc

## Purpose
This project is a supervision-first intake platform scaffold for the legal workflow described in the attached build brief. It is designed to stay aligned with the brief's non-negotiables: no legal advice, no outcome prediction, no implied attorney-client relationship, immutable-style auditability, structured JSON output, human review before external action, and controlled follow-up logic.

## V1 scope implemented here
- FastAPI backend for intake, review, and follow-up operations.
- Strict Pydantic intake-summary JSON validator.
- Locked prompt file and SHA-256 prompt hash loader.
- Heuristic classifier and evidence-request generator.
- Deterministic cross-practice scan rules.
- Follow-up scheduler with opt-out, quiet-hours, and kill-switch checks.
- Minimal reviewer dashboard.
- Audit log writes for all important actions.

## V1 scope - Gmail ingestion (newly implemented)
- Read-only Gmail API integration with domain-wide delegation
- Attorney decision extraction from email threads using LLM
- Structured storage of decisions with confidence scoring
- Full audit trail for sync operations and extractions
- Human review flagging for low-confidence extractions

## Out of scope for this scaffold
- Real GoHighLevel and Filevine credentialed integrations (Gmail is now implemented)
- Production auth, MFA, SSO, and session timeout middleware
- Virus scanning and signed-upload pipeline
- Production-grade model integration with zero-retention vendor settings
- Full React dashboard

## Architecture

### Runtime shape
- `app/main.py` boots the FastAPI service and auto-creates tables on startup.
- `app/api/` contains route modules grouped by responsibility.
- `app/services/` contains deterministic business logic, prompt governance, and policy checks.
- `app/models.py` contains SQLAlchemy persistence models.
- `app/schemas.py` contains strict Pydantic contracts and enums.
- `app/static/dashboard.html` is a minimal queue/detail reviewer UI.
- `tests/` contains basic validator and follow-up tests.
- `scripts/init_db.py` resets the local database for demo work.

### Primary request flow
1. Prospect message hits `POST /api/intake/messages`.
2. Text is sanitized for SSN, long account number, and DOB patterns.
3. Prospect and conversation are created if needed.
4. The message is persisted and audited.
5. The API returns a suggested next prompt and the current intake stage.
6. When ready, `POST /api/intake/conversations/{conversation_id}/finalize` generates the structured summary.
7. The summary is validated through the Pydantic schema before persistence.
8. Follow-up tasks are scheduled only when recommendation is `request_more_evidence` and evidence is still missing.
9. Reviewers inspect the summary through queue/detail APIs or the dashboard.
10. Reviewer decisions are audited.

## Folder map

### Root files
- `README.md`: local setup and scope notes.
- `.env.example`: environment variables.
- `pyproject.toml`: package metadata and dependencies.
- `design-doc.md`: this long-lived alignment document.

### `app/`
- `config.py`: settings object and environment parsing, including provider/stub LLM options.
- `db.py`: async engine, session factory, and declarative base.
- `models.py`: SQLAlchemy tables for prospects, conversations, messages, summaries, LLM call records, follow-up tasks, and audit logs.
- `schemas.py`: strict JSON contracts, enums, and LLM metadata schemas.
- `main.py`: FastAPI app assembly and startup hooks.

### `app/api/`
- `routes_health.py`: liveness and readiness-style health endpoint.
- `routes_intake.py`: intake message creation, conversation finalization, summary persistence, and transcript detail fetch.
- `routes_review.py`: reviewer queue, summary detail, and reviewer decision actions.
- `routes_followups.py`: due follow-up retrieval and follow-up run simulation with policy checks.

### `app/services/`
- `audit.py`: centralized audit-log writer for append-only event capture.
- `pii.py`: sensitive-data redaction and opt-out detection before persistence or follow-up handling.
- `prompt_loader.py`: locked prompt file loader and prompt-hash generator.
- `classifier.py`: compatibility shim that re-exports provider-backed classification through the Phase 2 agent core.
- `evidence.py`: deterministic evidence checklist definitions by practice area.
- `cross_practice.py`: deterministic secondary-claim scan based on the V1 rule set.
- `followup.py`: follow-up task scheduling, cadence timing, and quiet-hours checks.
- `llm_agent_core.py`: provider-backed agent-core boundary for classification, targeted evidence asks, summary generation, and LLM call-record persistence.
- `router.py`: queue escalation and routing rules kept outside the model.
- `summary_generator.py`: orchestrates agent-core calls, deterministic policy logic, defendant extraction, evidence reconciliation, and final validated summary assembly.

### `app/prompts/`
- `system_prompt_v1.txt`: partner-governed locked system prompt used for prompt hashing and replay metadata.

### `app/static/`
- `dashboard.html`: minimal reviewer queue and detail interface for local scaffold use.

### `tests/`
- `test_validator.py`: confirms the strict intake-summary schema accepts valid payloads.
- `test_followup.py`: confirms the three-attempt cadence and quiet-hours behavior.
- `test_llm_phase2.py`: confirms the Phase 2 agent-core flow returns a summary with LLM metadata attached.

### `scripts/`
- `init_db.py`: local reset/bootstrap script.

## Data model notes

### Prospects
Holds external IDs, contact info, state, source channel, consent state, and high-level status.

### Conversations
Represents the intake instance. Stores channel, lifecycle status, and prompt/model version hash.

### Messages
Stores transcript rows with role, sanitized content, and optional metadata.

### Intake summaries
Stores both normalized columns and the raw validated JSON payload. This gives you simple filtering plus exact replay.

### Follow-up tasks
Stores template ID, version, attempt number, due time, channel, payload, and blocked/sent status.

### Audit log
Append-only in intent. Every important state transition should write here.

### LLM call records
Stores provider, model ID, operation, prompt version, prompt hash, raw response text, and request/response metadata for replay and audit.

## API contract

### `POST /api/intake/messages`
Creates or appends a message.

Request shape:
```json
{
  "conversation_id": null,
  "prospect": {
    "first_name": "Jane",
    "last_name": "Doe",
    "email": "jane@example.com",
    "phone": "+1...",
    "state": "WA",
    "source_channel": "ghl_chat",
    "consent_status": "pending",
    "external_ids": {}
  },
  "role": "prospect",
  "content": "A collector called my cell phone repeatedly about a debt."
}
```

Response shape:
```json
{
  "conversation_id": "...",
  "sanitized_content": "...",
  "suggested_next_prompt": "...",
  "current_stage": "open_fact_gathering"
}
```

### `POST /api/intake/conversations/{conversation_id}/finalize`
Generates, validates, persists, and returns the intake summary. Also schedules follow-ups when needed.

### `GET /api/intake/conversations/{conversation_id}`
Returns transcript plus latest summary.

### `GET /api/review/queue`
Returns pending summaries for the reviewer queue.

### `GET /api/review/summaries/{summary_id}`
Returns the raw summary JSON plus transcript.

### `POST /api/review/summaries/{summary_id}/decision`
Records reviewer action.

### `GET /api/followups/due`
Returns scheduled tasks that are due.

### `POST /api/followups/run`
Simulates a follow-up send or blocks it if policy conditions fail.

## Design rules to keep aligned with the brief
1. The LLM agent core never decides whether the firm takes the case.
2. Every summary must pass strict schema validation before review routing.
3. Output should remain structured first and prose second.
4. Follow-up content must come from approved templates, not free-form generation.
5. Quiet hours, opt-out, and kill switch remain server-side policy, never model-side policy.
6. Sensitive identifiers must be redacted before they are persisted to the chat log.
7. Every reviewer action must preserve the original summary while logging the diff or replacement.
8. Auditability takes priority over convenience.

## Recommended next build steps

### Phase 1: harden the scaffold
- Add Alembic migrations.
- Add structured logging and correlation IDs.
- Add auth and reviewer roles.
- Add real append-only DB permissions in Postgres.

### Phase 2: provider-backed agent core (implemented in current scaffold)
- Classification, targeted evidence asks, and summary generation now run through `app/services/llm_agent_core.py`.
- The default local transport is a stub provider so the stack remains runnable without external credentials.
- JSON validation, compliance checks, cross-practice deterministic rules, routing, and follow-up policy remain outside the model.
- Prompt version, prompt hash, model ID, operation type, and request/response metadata are persisted in `llm_call_records` for replay.

### Phase 3: real integrations
- GHL inbound webhook adapter and outbound follow-up sender.
- Gmail read-only extraction pipeline.
- Filevine read-only training-corpus sync.

### Phase 4: dashboard upgrade
- Move to React + Tailwind.
- Add MFA/SSO.
- Add queue filters, review diffs, evidence panes, and audit trail drill-down.

## Risks and caveats
- The local dashboard is intentionally minimal and not production-grade.
- The current default provider is still a stub transport for local development; switch to a real provider by setting the LLM environment variables and disabling stub mode.
- SQLite is included for easy local startup, but Postgres should be used for serious dev and all production work.
- Audit append-only semantics are modeled in code, but production enforcement should happen at the database permission layer.

## How to use this doc
Use this file as the alignment reference before making any architectural change. If a proposed change weakens compliance, auditability, human review, or strict schema validation, it is misaligned with the intended V1 and should be redesigned.


## Phase 2 implementation notes

The current scaffold no longer uses the old heuristic-only classification path as the primary implementation. Instead, classification, targeted evidence-request generation, and structured summary generation all flow through the provider-backed agent-core boundary in `app/services/llm_agent_core.py`.

### Provider configuration

The runtime behavior is intentionally split into two modes:

**Stub mode (default)**:
- Uses heuristic-based `StubLLMClient` for local development and CI-friendly testing
- No external API calls or credentials required
- Automatically activated when:
  - `LLM_STUB_MODE=true`, OR
  - `LLM_API_KEY` is missing/empty, OR
  - `LLM_PROVIDER` is not `openai_compatible`

**Provider mode (Groq)**:
- Uses `OpenAICompatibleClient` with Groq's OpenAI-compatible API
- Default configuration:
  - `LLM_PROVIDER=openai_compatible`
  - `LLM_BASE_URL=https://api.groq.com/openai/v1`
  - `LLM_MODEL_ID=llama-3.1-70b-versatile`
- Requires `LLM_API_KEY` from https://console.groq.com/keys
- Activated when `LLM_STUB_MODE=false` AND `LLM_API_KEY` is set

Groq provides:
- Fast inference with LPU architecture
- OpenAI-compatible API format
- Structured JSON output support (`response_format: {type: "json_object"}`)
- Large context windows (128k tokens for Llama 3.1 70B)
- Strong instruction following for legal intake classification

**Model selection rationale**:
- `llama-3.1-70b-versatile` chosen for:
  - Excellent structured JSON generation
  - Strong reasoning for practice area classification
  - Reliable instruction following
  - Large context window for long transcripts
  - Production stability

**IMPORTANT**: This integration is for development/shadow mode only. Production deployment requires:
- Vendor selection with zero-retention data agreement
- Rate limiting and cost controls
- Monitoring and fallback strategies
- Partner-approved model selection

**Current configuration**: The .env file is currently configured with `LLM_MODEL_ID=llama-3.1-70b-versatile` and `LLM_STUB_MODE=true` (stub mode enabled for local development without API calls).

### Architectural boundaries preserved

The LLM integration maintains strict compliance boundaries:
- The model is called **only** for classification, targeted evidence asks, and neutral summary generation
- JSON validation is enforced by Pydantic schemas **outside the model**
- Compliance checks remain deterministic and server-side
- Cross-practice required rules remain deterministic and server-side
- Reviewer routing, follow-up cadence, quiet-hours enforcement, and kill-switch behavior remain **outside the model**
- Prompts include explicit compliance guardrails (no legal advice, no outcome prediction, neutral tone)

### Audit and replay support

Replay and audit support are improved through the `llm_call_records` table and `llm_request_metadata` payloads attached to summaries. Each LLM-backed operation stores:
- Provider and model ID
- Operation name (classification, evidence_request, summary_generation)
- Prompt version and SHA-256 prompt hash
- Request ID for correlation
- Raw response preview (first 500 characters)
- Token usage metadata when available
- Stubbed flag to distinguish heuristic vs. real LLM responses

This enables full replay of any intake decision for compliance review and debugging.

## Gmail Integration (Phase 3 Implementation)

Per build brief Section 13, Gmail ingestion provides read-only access to attorney decisions from firm email for training corpus enrichment.

### Architecture

**Services** (`app/services/gmail_*.py`):
- `gmail_auth.py`: OAuth 2.0 with domain-wide delegation, gmail.readonly scope only
- `gmail_client.py`: Message and thread retrieval, search query building
- `gmail_extraction.py`: LLM-powered attorney decision extraction
- `gmail_ingestion.py`: Orchestrates full sync pipeline with audit logging

**Models** (`app/models.py`):
- `GmailAttorneyDecision`: Stores extracted decisions with confidence, rationale, date, attorney
- `GmailSyncRecord`: Tracks sync operations for auditability

**API Routes** (`app/api/routes_gmail.py`):
- `POST /api/gmail/sync`: Trigger sync operation
- `GET /api/gmail/sync/{sync_id}/status`: Poll sync status
- `GET /api/gmail/decisions`: List extracted decisions
- `GET /api/gmail/decisions/{decision_id}`: Get decision details

### Data Flow

1. **Authentication**: Service account with domain-wide delegation authenticates for target mailbox
2. **Search**: Query Gmail for messages matching prospect identifiers (name, email, phone)
3. **Fetch**: Retrieve unique threads containing matches
4. **Extract**: LLM analyzes thread and extracts structured decision:
   - Decision type (accept/reject/more_info/refer_out)
   - Rationale (attorney's stated reasoning)
   - Decision date (message timestamp)
   - Deciding attorney (from signature/sender)
   - Confidence score (0.0-1.0)
5. **Validate**: Pydantic schema ensures extraction meets quality standards
6. **Flag**: Low-confidence extractions (<0.7 by default) marked for human review
7. **Store**: Decision persisted with full LLM metadata for replay
8. **Audit**: Every operation logged to audit_log table with correlation IDs

### Security Constraints (Build Brief Compliance)

**Read-only access** (Section 13):
- OAuth scope limited to `gmail.readonly` only
- NO email sending or modification permitted
- Auth service validates scope before operations

**PII minimization** (Section 13):
- Only message metadata and snippets stored (not full body)
- No retention of privileged attorney-client communications beyond extraction
- Subject and snippet truncated to 500/1000 chars respectively

**Auditability** (Section 2):
- Every sync operation creates immutable `GmailSyncRecord`
- Every decision extraction logged to `llm_call_records` with prompt hash
- Every storage operation audited via `write_audit_log`
- Correlation IDs enable end-to-end traceability

**Human review gating** (Sections 1, 17):
- Extractions below confidence threshold flagged `requires_human_review=True`
- Review status tracked: pending → confirmed/rejected/modified
- Original extraction preserved immutably even if modified by reviewer

### Configuration

**Environment variables** (`.env`):
```bash
# Gmail Integration
GMAIL_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'
GMAIL_ENABLED=true
GMAIL_DEFAULT_MAILBOX=attorney@firm.com
GMAIL_CONFIDENCE_THRESHOLD=0.7

# LLM for extraction (reuses existing config)
LLM_STUB_MODE=false  # Set true for local dev without API
LLM_API_KEY=your_groq_key
```

**Service account setup**:
1. Create service account in Google Cloud Console
2. Enable Gmail API
3. Set up domain-wide delegation with `gmail.readonly` scope
4. Download JSON key and set `GMAIL_SERVICE_ACCOUNT_JSON`

### LLM Extraction Details

**Prompt design**:
- System prompt defines decision types and extraction rules
- User prompt includes thread metadata (from/to/date/subject/snippet)
- Full body NOT included per PII minimization requirement
- Confidence scoring guidelines ensure conservative classification

**Validation**:
- Pydantic schema enforces min/max lengths for rationale and reasoning
- Decision date must be valid ISO 8601 datetime
- Confidence must be 0.0-1.0 range
- Deciding attorney extracted from context (not fabricated)

**Stub mode**:
- Default mode for local development without LLM API
- Returns conservative "more_info" decision with 0.3 confidence
- Always flags for human review
- Enables full pipeline testing without external dependencies

### Sync Workflow Example

```python
# 1. Configure sync
config = GmailSyncConfig(
    mailbox="attorney@firm.com",
    prospect_identifiers=[
        {"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com"}
    ],
    date_range_start="2024-01-01T00:00:00Z",
    max_messages=100,
    confidence_threshold=0.7
)

# 2. Trigger sync via API
POST /api/gmail/sync
{
  "config": {...},
  "initiated_by": "user:admin"
}

# 3. Returns sync_id immediately (202 Accepted)
{
  "sync_id": "abc123",
  "status": "running",
  ...
}

# 4. Poll for completion
GET /api/gmail/sync/abc123/status

# 5. Review extracted decisions
GET /api/gmail/decisions?requires_review=true
```

### Testing Strategy

**Unit tests** (`tests/test_gmail_ingestion.py`):
- Schema validation (GmailSyncConfig, AttorneyDecisionExtraction)
- Message parsing (GmailMessage from API response)
- Stub extraction mode (no external dependencies)
- Enum coverage (DecisionType values)

**Integration tests** (marked `@pytest.mark.integration`):
- Full sync workflow with real Gmail credentials
- Skipped by default to avoid external dependencies
- Run explicitly: `pytest -m integration`

**Manual testing**:
1. Set up service account and credentials
2. Run sync against test mailbox
3. Verify decisions extracted and flagged correctly
4. Check audit logs for complete correlation

### Risks and Mitigations

**Risk: Over-broad scope creep**
- Mitigation: Auth service validates gmail.readonly scope, logs warnings for non-readonly

**Risk: PII exposure in logs**
- Mitigation: Only metadata/snippets stored, full body never retained

**Risk: Hallucinated attorney decisions**
- Mitigation: Confidence scoring + human review flag for uncertain extractions

**Risk: Gmail API rate limits**
- Mitigation: Configurable max_messages per sync, pagination support for future batching

**Risk: Training data contamination**
- Mitigation: Prospect matching optional, decisions stored independently, human review confirms linkage

### Future Enhancements (V2+)

- **Batch processing**: Queue-based async sync for large mailbox ingestion
- **Webhook triggers**: Real-time ingestion via Gmail push notifications
- **Multi-mailbox sync**: Parallel processing across multiple attorney mailboxes
- **Advanced matching**: Fuzzy name matching, phone normalization for better prospect linkage
- **Analytics dashboard**: Visualize decision trends, attorney productivity, confidence distributions
- **Export to Filevine**: Auto-populate case records with extracted decisions (write access required)

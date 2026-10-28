# AI Intake Agent V1 Design Doc

## Purpose
This project is a supervision-first intake platform scaffold for the legal workflow described in the attached build brief. It is designed to stay aligned with the brief's non-negotiables: no legal advice, no outcome prediction, no implied attorney-client relationship, immutable-style auditability, structured JSON output, human review before external action, and controlled follow-up logic.

## V1 scope implemented here
- FastAPI backend for intake, review, and follow-up operations.
- Strict Pydantic intake-summary JSON validator.
- Locked prompt file and SHA-256 prompt hash loader.
- Provider-backed LLM classification with Ollama/Groq support.
- Deterministic cross-practice scan rules with hybrid LLM merge capability.
- Follow-up scheduler with opt-out, quiet-hours, and kill-switch checks.
- Enhanced reviewer dashboard with approve/modify/reject actions.
- Audit log writes for all important actions.
- Replay testing infrastructure for accuracy validation.

## Out of scope for this scaffold
- Real GoHighLevel, Gmail, and Filevine credentialed integrations.
- Production auth, MFA, SSO, and session timeout middleware.
- Virus scanning and signed-upload pipeline.
- Production-grade model integration with zero-retention vendor settings.
- Full React dashboard.

## Architecture

### Runtime shape
- `app/main.py` boots the FastAPI service and auto-creates tables on startup.
- `app/api/` contains route modules grouped by responsibility.
- `app/services/` contains deterministic business logic, prompt governance, and policy checks.
- `app/models.py` contains SQLAlchemy persistence models.
- `app/schemas.py` contains strict Pydantic contracts and enums.
- `app/static/dashboard.html` is the reviewer UI with full approve/modify/reject workflow.
- `tests/` contains validator, follow-up, and LLM integration tests.
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
10. Reviewer decisions (approve/modify/reject) are audited with full before/after state.

## Folder map

### Root files
- `README.md`: local setup and scope notes.
- `.env.example`: environment variables.
- `pyproject.toml`: package metadata and dependencies.
- `design-doc.md`: this long-lived alignment document.
- `LLM_approach_improvement_next_steps.md`: replay test analysis and recommended accuracy improvements.

### `app/`
- `config.py`: settings object and environment parsing, including Ollama/Groq/stub LLM options.
- `db.py`: async engine, session factory, and declarative base.
- `models.py`: SQLAlchemy tables for prospects, conversations, messages, summaries, LLM call records, follow-up tasks, and audit logs.
- `schemas.py`: strict JSON contracts, enums (including `ReviewDecision`), and LLM metadata schemas.
- `main.py`: FastAPI app assembly and startup hooks.

### `app/api/`
- `routes_health.py`: liveness and readiness-style health endpoint.
- `routes_intake.py`: intake message creation, conversation finalization, summary persistence, and transcript detail fetch.
- `routes_review.py`: reviewer queue, summary detail by status, and reviewer decision actions with audit logging.
- `routes_followups.py`: due follow-up retrieval and follow-up run simulation with policy checks.

### `app/services/`
- `audit.py`: centralized audit-log writer for append-only event capture.
- `pii.py`: sensitive-data redaction and opt-out detection before persistence or follow-up handling.
- `prompt_loader.py`: locked prompt file loader and prompt-hash generator.
- `classifier.py`: compatibility shim that re-exports provider-backed classification through the Phase 2 agent core.
- `evidence.py`: deterministic evidence checklist definitions by practice area.
- `cross_practice.py`: deterministic secondary-claim scan with `merge_secondary_areas()` for hybrid LLM+rules approach.
- `followup.py`: follow-up task scheduling, cadence timing, and quiet-hours checks.
- `llm_agent_core.py`: provider-backed agent-core boundary supporting Ollama, Groq, and stub modes.
- `router.py`: queue escalation and routing rules kept outside the model.
- `summary_generator.py`: orchestrates agent-core calls, hybrid secondary detection, and final validated summary assembly.

### `app/prompts/`
- `system_prompt_v1.txt`: partner-governed locked system prompt with classification, evidence, and summary generation sections.

### `app/static/`
- `dashboard.html`: full-featured reviewer interface with tabbed views, edit capability, and action buttons.

### `tests/`
- `test_validator.py`: confirms the strict intake-summary schema accepts valid payloads.
- `test_followup.py`: confirms the three-attempt cadence and quiet-hours behavior.
- `test_llm_phase2.py`: confirms the Phase 2 agent-core flow returns a summary with LLM metadata attached.

### `scripts/`
- `init_db.py`: local reset/bootstrap script.

### Replay testing files
- `replay_runner.py`: automated 100-case replay test runner for accuracy validation.
- `synthetic_replay_corpus_100.jsonl`: test corpus with gold labels.
- `replay_results.json`: latest test results with accuracy metrics.

## Data model notes

### Prospects
Holds external IDs, contact info, state, source channel, consent state, and high-level status.

### Conversations
Represents the intake instance. Stores channel, lifecycle status, and prompt/model version hash.

### Messages
Stores transcript rows with role, sanitized content, and optional metadata.

### Intake summaries
Stores both normalized columns and the raw validated JSON payload. Includes review metadata: `review_status`, `reviewer_id`, `reviewed_at`, `final_disposition`.

### Follow-up tasks
Stores template ID, version, attempt number, due time, channel, payload, and blocked/sent status.

### Audit log
Append-only in intent. Every important state transition should write here, including reviewer decisions with before/after state.

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

### `GET /api/review/summaries/by-status/{status}`
Returns summaries filtered by review status (approved, modified, rejected) with reviewer metadata.

### `GET /api/review/summaries/{summary_id}`
Returns the raw summary JSON, transcript, and review metadata (reviewer_id, reviewed_at, final_disposition).

### `POST /api/review/summaries/{summary_id}/decision`
Records reviewer action with full audit trail.

Request shape:
```json
{
  "decision": "approved|modified|rejected",
  "reviewer_id": "reviewer-name",
  "reviewer_note": "optional note",
  "updated_summary": { ... }  // Required for "modified" decision
}
```

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

## Phase 2 implementation notes

The current scaffold routes classification, targeted evidence-request generation, and structured summary generation through the provider-backed agent-core boundary in `app/services/llm_agent_core.py`.

### Provider configuration

The runtime behavior supports multiple LLM providers:

**Stub mode (default)**:
- Uses heuristic-based `StubLLMClient` for local development and CI-friendly testing
- No external API calls or credentials required
- Automatically activated when `LLM_STUB_MODE=true` or `LLM_API_KEY` is missing

**Ollama mode (local)**:
- Uses local Ollama server for development without cloud costs
- Configuration:
  - `LLM_PROVIDER=ollama`
  - `LLM_BASE_URL=http://localhost:11434/v1`
  - `LLM_MODEL_ID=llama3.1:8b`
- Requires Ollama installed with model pulled (`ollama pull llama3.1:8b`)
- Activated when `LLM_STUB_MODE=false` AND `LLM_PROVIDER=ollama`

**Groq mode (cloud)**:
- Uses Groq's OpenAI-compatible API for fast cloud inference
- Configuration:
  - `LLM_PROVIDER=openai_compatible`
  - `LLM_BASE_URL=https://api.groq.com/openai/v1`
  - `LLM_MODEL_ID=llama-3.1-70b-versatile`
- Requires `LLM_API_KEY` from https://console.groq.com/keys
- Activated when `LLM_STUB_MODE=false` AND `LLM_PROVIDER=openai_compatible`

**IMPORTANT**: This integration is for development/shadow mode only. Production deployment requires:
- Vendor selection with zero-retention data agreement
- Rate limiting and cost controls
- Monitoring and fallback strategies
- Partner-approved model selection

### Architectural boundaries preserved

The LLM integration maintains strict compliance boundaries:
- The model is called **only** for classification, targeted evidence asks, and neutral summary generation
- JSON validation is enforced by Pydantic schemas **outside the model**
- Compliance checks remain deterministic and server-side
- Cross-practice required rules remain deterministic and server-side
- Reviewer routing, follow-up cadence, quiet-hours enforcement, and kill-switch behavior remain **outside the model**
- Prompts include explicit compliance guardrails (no legal advice, no outcome prediction, neutral tone)

### Hybrid secondary detection

The cross-practice detection supports a hybrid LLM + rules approach:
- `scan_cross_practice_deterministic()`: keyword-based rules (authoritative)
- `merge_secondary_areas()`: merges LLM suggestions with rule-based results
- Rule-based results take priority for auditability
- LLM suggestions filtered by confidence threshold (0.7 default)
- Source tagging: "llm_inferred" vs "rule_based" for audit trail

**Current status**: Hybrid approach showed regression in testing (63% → 42% secondary accuracy). See `LLM_approach_improvement_next_steps.md` for analysis and recommended rollback.

### Audit and replay support

Replay and audit support are provided through the `llm_call_records` table and `llm_request_metadata` payloads attached to summaries. Each LLM-backed operation stores:
- Provider and model ID
- Operation name (classification, evidence_request, summary_generation)
- Prompt version and SHA-256 prompt hash
- Request ID for correlation
- Raw response preview (first 500 characters)
- Token usage metadata when available
- Stubbed flag to distinguish heuristic vs. real LLM responses

## Reviewer dashboard

The dashboard at `/dashboard` provides:
- **Tabbed queue views**: Pending, Approved, Modified, Rejected
- **Summary detail panel**: Full JSON display with transcript
- **Approve button**: One-click approval with reviewer ID prompt
- **Modify button**: Editable JSON textarea with validation, confirm/cancel workflow
- **Reject button**: Rejection with optional reason note
- **Review history**: Displays reviewer ID, timestamp, and final disposition for reviewed items
- **Cache-busting headers**: Ensures latest UI code is served

## Replay testing infrastructure

The replay testing system validates classification accuracy:
- **100-case corpus**: `synthetic_replay_corpus_100.jsonl` with gold labels
- **Automated runner**: `replay_runner.py` processes all cases against live API
- **Metrics tracked**:
  - Primary classification accuracy
  - Secondary practice areas (exact match)
  - Cross-practice flag accuracy
  - Recommendation logic accuracy
- **Results output**: `replay_results.json` with failure analysis

### Latest results (see `LLM_approach_improvement_next_steps.md`)
| Metric | Accuracy |
|--------|----------|
| Primary Classification | 78% |
| Secondary Areas (exact) | 42% |
| Cross-Practice Flag | 61% |
| Recommendation Logic | 75% |

## Recommended next steps

### Immediate: LLM accuracy improvements
See `LLM_approach_improvement_next_steps.md` for detailed analysis and action items:
1. **Rollback hybrid approach**: Restore secondary accuracy to 63% baseline
2. **Improve primary classification**: Add few-shot examples for TCPA vs FDCPA distinction
3. **Refine recommendation logic**: Investigate remaining 25% failures
4. **Re-run replay test**: Validate improvements after each change

### Phase 3: harden the scaffold
- Add Alembic migrations.
- Add structured logging and correlation IDs.
- Add auth and reviewer roles.
- Add real append-only DB permissions in Postgres.

### Phase 4: real integrations
- GHL inbound webhook adapter and outbound follow-up sender.
- Gmail read-only extraction pipeline.
- Filevine read-only training-corpus sync.

### Phase 5: dashboard upgrade
- Move to React + Tailwind.
- Add MFA/SSO.
- Add queue filters, review diffs, evidence panes, and audit trail drill-down.

## Risks and caveats
- The local dashboard is functional but not production-grade.
- The current default provider is stub mode for local development; switch to Ollama or Groq by setting environment variables.
- SQLite is included for easy local startup, but Postgres should be used for serious dev and all production work.
- Audit append-only semantics are modeled in code, but production enforcement should happen at the database permission layer.
- Hybrid LLM+rules approach for secondary detection showed regression and may need rollback.

## How to use this doc
Use this file as the alignment reference before making any architectural change. If a proposed change weakens compliance, auditability, human review, or strict schema validation, it is misaligned with the intended V1 and should be redesigned.

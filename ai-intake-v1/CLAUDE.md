# CLAUDE.md

## Mission
Build a supervised AI Intake Agent that converts inbound prospective-client conversations into structured, attorney-reviewable intake summaries for TCPA, FCRA, FDCPA, mass arbitration, unknown consumer issues, and wrong-fit leads.

Week 1 target:
- One controlled channel
- Strict JSON intake summaries
- Human review dashboard
- Full audit logging
- Read-only ingestion for GHL, Filevine, and Gmail attorney decisions

Core principle:
- Build for supervision first, intelligence second.
- Optimize for compliance, auditability, and human review over speed or cleverness.

## Product rules
These rules are non-negotiable. They outrank convenience, polish, and speed.

- Never give legal advice.
- Never promise, predict, estimate, or imply outcomes.
- Never create or imply an attorney-client relationship.
- Never allow the agent to accept or reject a matter without human review.
- Every case-impacting external action must route to a human first.
- Every conversation, classification, routing action, reviewer action, and follow-up event must be auditable.
- Historical records are immutable in intent. Preserve append-only semantics.

## Architecture boundaries
Treat this application as a supervised legal-intake platform, not a general chatbot.

### LLM is allowed only for
- Practice-area classification
- Targeted evidence asks
- Neutral structured summary generation

### Deterministic/server-side code must own
- JSON schema validation
- Compliance checks and blocking
- Routing and escalation
- Cross-practice must-fire rules
- Quiet-hours and opt-out enforcement
- Kill switch behavior
- Audit logging
- Template-based follow-up sending
- PII redaction and masking

Do not move server-side policy into prompts just because it is faster.

## Existing implementation assumptions
Current scaffold uses:
- FastAPI backend
- SQLAlchemy models
- Pydantic schemas
- Provider-backed `llm_agent_core.py` with stub mode by default
- Prompt hashing and replay metadata
- Review queue and follow-up flows

When changing architecture, update all affected layers together:
- models
- schemas
- services
- routes
- tests
- design-doc.md

## Coding rules
- Prefer incremental, reviewable changes over broad rewrites.
- Reuse existing patterns before introducing new abstractions.
- Keep functions small and explicit in compliance-sensitive paths.
- Do not weaken auditability for convenience.
- Avoid hidden side effects.
- Make policy boundaries obvious in code.
- If a task touches data shape, update schema validation and tests in the same change.
- If a task touches workflow or responsibilities, update `design-doc.md` in the same change.

## Required workflow
For any task expected to take more than 30 minutes:
1. Enter planning mode first.
2. Identify affected files, invariants, and risks before editing.
3. Implement the smallest coherent slice.
4. Run or propose verification steps.
5. Self-review for edge cases and drift from the brief.

Use this response format for non-trivial tasks:
1. Plan
2. Files to change
3. Implementation
4. Verification
5. Risks / follow-ups

## Invariants to protect
- Human review before case-impacting action
- Strict structured JSON output
- Prompt version and hash tracking
- LLM request metadata persistence for replay
- Deterministic cross-practice rule coverage
- Quiet-hours and opt-out handling outside the model
- Immutable/auditable reviewer actions
- No storage of SSN or full account numbers in chat logs

## What not to do
- Do not generate free-form follow-up bodies when templates are required.
- Do not let the model decide acceptance, rejection, value, or likelihood of success.
- Do not silently broaden integration scopes from read-only to write access.
- Do not bypass audit logging for internal actions.
- Do not invent schema fields without updating validation, persistence, docs, and tests.
- Do not edit locked prompts unless the task explicitly requests a partner-approved prompt update.

## Task-specific skills
### Skill: Compliance-sensitive backend change
When editing compliance-sensitive backend logic:
1. Identify whether the logic belongs in the LLM or deterministic code.
2. Default to deterministic code unless the task is classification, evidence asking, or summary generation.
3. Verify audit logging coverage.
4. Verify human-review gating remains intact.
5. Verify tests cover failure and edge cases.

### Skill: Intake schema change
When changing intake summary fields:
1. Update Pydantic schema first.
2. Update persistence model and API serialization.
3. Update summary generator and downstream readers.
4. Update tests.
5. Update `design-doc.md` file-responsibility and contract notes.

### Skill: Integration work
When working on GHL, Gmail, or Filevine:
1. Default to read-only behavior unless explicitly approved otherwise.
2. Log object IDs and correlation IDs.
3. Avoid side effects unrelated to the requested operation.
4. Surface any unexpected remote state change immediately.

## Repo areas
See the scoped CLAUDE.md files in:
- `app/api/CLAUDE.md`
- `app/services/CLAUDE.md`
- `tests/CLAUDE.md`

## Suggested recurring prompt
Use this instruction at the start of substantial tasks:

"Think deeply before responding. This is a supervision-first legal-intake system. Optimize for compliance, auditability, and human review over speed or cleverness. Keep policy outside the model. Before editing, identify all affected files, invariants, and tests. After coding, self-review for edge cases, regressions, and drift from the build brief."

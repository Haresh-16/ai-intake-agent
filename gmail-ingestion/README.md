# AI Intake Agent V1

A compliance-first FastAPI scaffold for a supervised legal-intake workflow.

## What is included
- Conversation intake APIs.
- Strict intake-summary JSON validator.
- Locked prompt loader with SHA-256 versioning.
- Heuristic classifier, evidence checklist engine, and deterministic cross-practice scan.
- Follow-up scheduler with quiet-hours, opt-out, and max-attempt logic.
- Reviewer queue APIs and a minimal dashboard.
- Append-only audit logging model.
- Pytest coverage for the validator and follow-up scheduler.

## Quick start
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
python scripts/init_db.py
uvicorn app.main:app --reload
```

Open:
- API docs: http://127.0.0.1:8000/docs
- Dashboard: http://127.0.0.1:8000/dashboard

## Environment
The default local database is SQLite for fast startup. For alignment with the brief, set `DATABASE_URL` to Postgres in real deployment.

## Notes
- This scaffold is intentionally supervision-first.
- Outbound sends are simulated and written to the audit log.
- Replace the heuristic agent core with an LLM provider once zero-retention and prompt governance are approved.


## Phase 2 agent core

This scaffold now uses a provider-backed agent-core interface for:
- practice-area classification
- targeted evidence asks
- structured summary generation

JSON validation, compliance checks, routing, and follow-up policy remain outside the model.
LLM calls are recorded in `llm_call_records` with prompt version, prompt hash, model ID, operation type, and request metadata for replay and audit.

By default, the project runs in `LLM_PROVIDER=stub` mode so the end-to-end flow works without paid credentials.

## Phase 2 agent core

This scaffold now routes classification, targeted evidence asks, and summary generation through a provider-backed agent-core interface. JSON validation, compliance checks, routing, and follow-up policy remain outside the model. By default it runs in stub mode so the end-to-end flow works without paid credentials.

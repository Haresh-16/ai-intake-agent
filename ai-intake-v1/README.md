# AI Intake Agent V1

A compliance-first FastAPI scaffold for a supervised legal-intake workflow.

## What is included
- Conversation intake APIs with PII sanitization.
- Strict intake-summary JSON validator.
- Locked prompt loader with SHA-256 versioning.
- Provider-backed LLM classification (Ollama, Groq, or stub mode).
- Deterministic cross-practice scan with hybrid LLM merge capability.
- Follow-up scheduler with quiet-hours, opt-out, and max-attempt logic.
- Enhanced reviewer dashboard with approve/modify/reject actions.
- Tabbed queue views (Pending, Approved, Modified, Rejected).
- Append-only audit logging with full before/after state tracking.
- Replay testing infrastructure for accuracy validation.
~
## Quick start
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
cp .env.example .env
python scripts/init_db.py
uvicorn app.main:app --reload
```

Open:
- API docs: http://127.0.0.1:8000/docs
- Dashboard: http://127.0.0.1:8000/dashboard

## Environment variables

### Database
- `DATABASE_URL`: SQLite for local, Postgres for production

### LLM Provider Configuration
```bash
# Stub mode (default - no external API calls)
LLM_STUB_MODE=true

# Ollama mode (local LLM server)
LLM_STUB_MODE=false
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL_ID=llama3.1:8b

# Groq mode (cloud API)
LLM_STUB_MODE=false
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL_ID=llama-3.1-70b-versatile
LLM_API_KEY=your-groq-api-key
```

## Using Ollama (local development)

1. Install Ollama: https://ollama.ai
2. Pull a model:
   ```bash
   ollama pull llama3.1:8b
   ```
3. Start Ollama server (runs on port 11434 by default)
4. Configure `.env`:
   ```bash
   LLM_STUB_MODE=false
   LLM_PROVIDER=ollama
   LLM_BASE_URL=http://localhost:11434/v1
   LLM_MODEL_ID=llama3.1:8b
   ```

## Dashboard features

The reviewer dashboard at `/dashboard` provides:
- **Pending tab**: Items awaiting review with approve/modify/reject actions
- **Approved tab**: Approved items with reviewer info
- **Modified tab**: Modified items with edit history
- **Rejected tab**: Rejected items with rejection reasons
- **Modify workflow**: Edit summary JSON directly, validate, and confirm
- **Audit trail**: Full reviewer attribution and timestamps

## Replay testing

Run the 100-case accuracy test:
```bash
# Start the server
uvicorn app.main:app --reload

# In another terminal, run replay test
python replay_runner.py
```

Results are saved to `replay_results.json`. See `LLM_approach_improvement_next_steps.md` for analysis.

## Project structure
```
app/
  api/           # FastAPI route handlers
  services/      # Business logic and LLM integration
  prompts/       # Locked system prompts
  static/        # Dashboard HTML
tests/           # Pytest test suite
scripts/         # Database init scripts
```

## Key files
- `design-doc.md`: Architecture and alignment reference
- `LLM_approach_improvement_next_steps.md`: Replay test analysis and improvement roadmap
- `replay_runner.py`: Automated accuracy testing
- `synthetic_replay_corpus_100.jsonl`: Test corpus with gold labels

## Notes
- This scaffold is intentionally supervision-first.
- Outbound sends are simulated and written to the audit log.
- JSON validation, compliance checks, routing, and follow-up policy remain outside the model.
- LLM calls are recorded in `llm_call_records` for replay and audit.

## Current accuracy (latest replay test)
| Metric | Accuracy |
|--------|----------|
| Primary Classification | 78% |
| Secondary Areas | 42% |
| Cross-Practice Flag | 61% |
| Recommendation | 75% |

See `LLM_approach_improvement_next_steps.md` for improvement roadmap.

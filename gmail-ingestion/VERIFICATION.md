# OpenRouter LLM Integration Verification Guide

This guide provides step-by-step commands to verify the OpenRouter free LLM provider integration.

## Prerequisites

Ensure you have Python 3.11+ installed and the project dependencies set up.

## Setup

### 1. Activate virtual environment

All commands in this guide assume the venv is activated. Activate it first:

```bash
cd D:\AI_Intake_Agent\ai-intake-v1-phase2\ai-intake-v1
source .venv/Scripts/activate
```

### 2. Install project dependencies

```bash
source .venv/Scripts/activate && python -m pip install -e .
```

## Verification Steps

### Step 1: Local Development (Stub Mode - No Credentials Needed)

This tests the default behavior using the heuristic stub client without external API calls.

#### Run all Phase 2 LLM tests
```bash
source .venv/Scripts/activate && python -m pytest tests/test_llm_phase2.py -v
```

Expected output: All tests should pass, including:
- `test_phase2_llm_flow` - Full summary generation flow
- `test_provider_selection_stub_mode_true` - Stub when stub_mode=True
- `test_provider_selection_missing_api_key` - Stub when API key missing
- `test_provider_selection_empty_api_key` - Stub when API key empty
- `test_provider_selection_real_client` - Real client when configured
- `test_provider_selection_wrong_provider` - Stub for unknown provider
- `test_stub_client_preserves_metadata` - Metadata captured in stub mode

#### Run specific test cases
```bash
# Test stub mode behavior
source .venv/Scripts/activate && python -m pytest tests/test_llm_phase2.py::test_provider_selection_stub_mode_true -v

# Test missing API key fallback
source .venv/Scripts/activate && python -m pytest tests/test_llm_phase2.py::test_provider_selection_missing_api_key -v

# Test metadata preservation
source .venv/Scripts/activate && python -m pytest tests/test_llm_phase2.py::test_stub_client_preserves_metadata -v
```

#### Start the API server (stub mode)
```bash
source .venv/Scripts/activate && uvicorn app.main:app --reload
```

Expected output:
```
INFO:     Will watch for changes in these directories: ['D:\\AI_Intake_Agent\\ai-intake-v1-phase2\\ai-intake-v1']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxx] using StatReload
INFO:     Started server process [xxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

Access the API at: http://127.0.0.1:8000/docs

---

### Step 2: Enable Groq Integration (Real LLM)

This enables real LLM calls using Groq's API.

#### Get Groq API Key
1. Visit https://console.groq.com/keys
2. Sign up for a free account
3. Generate an API key from the dashboard

#### Configure environment
```bash
# Copy example environment file
cp .env.example .env

# Edit .env file and set these values:
# LLM_API_KEY=gsk_your-api-key-here
# LLM_STUB_MODE=false
```

Your `.env` file should contain:
```env
APP_NAME=AI Intake Agent V1
ENV=dev
DATABASE_URL=sqlite+aiosqlite:///./ai_intake_v1.db
OUTBOUND_KILL_SWITCH=false

LLM_PROVIDER=openai_compatible
LLM_MODEL_ID=llama-3.1-70b-versatile
LLM_API_KEY=gsk_your-actual-key-here
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_TIMEOUT_SECONDS=45
LLM_STUB_MODE=false
```

#### Start API with Groq integration
```bash
source .venv/Scripts/activate && uvicorn app.main:app --reload
```

#### Test real LLM integration
```bash
# Run full integration test (will make real API calls)
source .venv/Scripts/activate && python -m pytest tests/test_llm_phase2.py::test_phase2_llm_flow -v
```

**Note**: This test will make real API calls to Groq and consume API quota.

---

### Step 3: Test API Endpoints

#### Health check
```bash
curl http://127.0.0.1:8000/api/health
```

Expected response:
```json
{"status": "ok", "app": "AI Intake Agent V1", "env": "dev"}
```

#### Create intake message
```bash
curl -X POST http://127.0.0.1:8000/api/intake/messages \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": null,
    "prospect": {
      "first_name": "Jane",
      "last_name": "Doe",
      "email": "jane@example.com",
      "phone": "+15551234567",
      "state": "CA",
      "source_channel": "ghl_chat",
      "consent_status": "pending",
      "external_ids": {}
    },
    "role": "prospect",
    "content": "I keep getting robocalls on my cell phone about a debt I already paid. They call multiple times a day."
  }'
```

Expected response includes:
```json
{
  "conversation_id": "...",
  "sanitized_content": "...",
  "suggested_next_prompt": "...",
  "current_stage": "open_fact_gathering"
}
```

#### Finalize conversation and generate summary
```bash
# Replace {conversation_id} with the ID from previous response
curl -X POST http://127.0.0.1:8000/api/intake/conversations/{conversation_id}/finalize
```

Expected response includes:
```json
{
  "conversation_id": "...",
  "primary_practice_area": "TCPA",
  "primary_confidence": 0.85,
  "fact_pattern": "...",
  "agent_recommendation": "route_to_attorney",
  "llm_request_metadata": {
    "classification": {
      "provider": "openai_compatible",
      "model_id": "llama-3.1-70b-versatile",
      "operation": "classification",
      "stubbed": false
    }
  }
}
```

---

### Step 4: Verify Provider Selection Logic

#### Test fallback to stub when API key is missing
```bash
# Remove API key from .env temporarily
# Set LLM_API_KEY=
# Then restart server and run:
source .venv/Scripts/activate && python -m pytest tests/test_llm_phase2.py::test_provider_selection_missing_api_key -v
```

#### Test provider selection with valid configuration
```bash
# Restore API key in .env
# Set LLM_STUB_MODE=false
# Then run:
source .venv/Scripts/activate && python -m pytest tests/test_llm_phase2.py::test_provider_selection_real_client -v
```

---

## Troubleshooting

### Issue: Tests fail with ModuleNotFoundError
**Solution**: Install project dependencies
```bash
source .venv/Scripts/activate && python -m pip install -e .
```

### Issue: API returns "LLM_API_KEY and LLM_BASE_URL are required"
**Solution**: Check your `.env` file:
1. Verify `LLM_API_KEY` is set
2. Verify `LLM_STUB_MODE=false`
3. Restart the server after changing `.env`

### Issue: Groq API returns 401 Unauthorized
**Solution**:
1. Verify your API key is correct
2. Check that the key hasn't expired
3. Visit https://console.groq.com/keys to verify account status

### Issue: Groq API returns 429 Too Many Requests
**Solution**: Rate limit exceeded
1. Wait for rate limit to reset
2. Consider reducing test frequency
3. Set `LLM_STUB_MODE=true` for local testing

### Issue: JSON parsing errors from LLM response
**Expected behavior**: Pydantic validation catches invalid JSON
1. Check `llm_call_records` table for raw response
2. Review prompt effectiveness
3. Consider adjusting prompts or switching models

---

## Expected Behavior Summary

| Configuration | LLM_STUB_MODE | LLM_API_KEY | Expected Client |
|--------------|---------------|-------------|-----------------|
| Default (local dev) | `true` | empty | `StubLLMClient` |
| Stub mode enforced | `true` | set | `StubLLMClient` |
| API key missing | `false` | empty | `StubLLMClient` (fallback) |
| Groq enabled | `false` | set | `OpenAICompatibleClient` |

---

## Compliance Verification

Verify that all compliance boundaries remain intact:

### ✅ LLM is used ONLY for:
- Practice area classification
- Targeted evidence requests
- Neutral summary generation

### ✅ Server-side code owns:
- JSON schema validation (Pydantic)
- Compliance checks (no legal advice, no ACR)
- Routing and escalation logic
- Cross-practice deterministic rules
- Quiet-hours and opt-out enforcement
- Kill switch behavior
- Audit logging

### ✅ Audit metadata captured:
- Provider and model ID
- Operation name
- Prompt version and hash
- Request ID
- Raw response preview
- Token usage
- Stubbed flag

---

## Next Steps After Verification

1. **Shadow mode testing**: Run both stub and real LLM in parallel, compare outputs
2. **Error handling**: Add graceful degradation for API failures
3. **Monitoring**: Add logging for rate limits, latency, token usage
4. **Production readiness**:
   - Vendor selection with zero-retention agreement
   - Cost controls and budgets
   - Partner approval of model selection
   - Fallback strategies for failures

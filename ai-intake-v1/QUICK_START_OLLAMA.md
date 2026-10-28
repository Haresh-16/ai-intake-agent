# Quick Start: Switch to Ollama (Local LLM)

This guide will help you switch from Groq API to Ollama to avoid rate limiting.

## Step 1: Install Ollama

### Download Ollama:
```bash
# Visit: https://ollama.com/download/windows
# Or direct download link:
https://ollama.com/download/OllamaSetup.exe
```

1. Download and run `OllamaSetup.exe`
2. Follow the installation wizard
3. Ollama will automatically start as a Windows service

### Verify Installation:
```bash
ollama --version
```

Expected output: `ollama version is 0.x.x` or similar

## Step 2: Download a Model

Choose one of these models (recommended: llama3.1:8b):

```bash
# RECOMMENDED: Good balance of speed and quality (4.7GB download)
ollama pull llama3.1:8b

# Alternative: Smaller and faster (2GB download)
ollama pull llama3.2:3b

# Alternative: Best quality but slower (40GB download, needs powerful GPU)
ollama pull llama3.1:70b
```

**Note:** The first pull will download the model (this may take a few minutes).

## Step 3: Test Ollama

Verify the model works:

```bash
# Test the model
ollama run llama3.1:8b "Hello, how are you?"

# Check installed models
ollama list

# Check Ollama is running
curl http://localhost:11434/api/tags
```

## Step 4: Restart Your FastAPI Server

1. **Stop the current server** (if running):
   - Press `Ctrl+C` in the terminal where the server is running

2. **Start the server again**:
   ```bash
   cd D:/AI_Intake_Agent/ai-intake-v1-phase2/ai-intake-v1
   source .venv/Scripts/activate
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

3. **Verify it's using Ollama**: Check the console output - it should NOT show Groq API calls

## Step 5: Run Tests

```bash
# Run the LLM tests
pytest tests/test_llm_phase2.py -v

# Run the replay runner (all 100 cases should work now!)
python replay_runner.py
```

## Configuration Reference

Your `.env` file is already configured for Ollama:

```env
LLM_PROVIDER=ollama
LLM_MODEL_ID=llama3.1:8b
LLM_BASE_URL=http://localhost:11434
LLM_TIMEOUT_SECONDS=120
LLM_STUB_MODE=false
```

## Switching Between Providers

### Use Ollama (Local - No rate limits):
```env
LLM_PROVIDER=ollama
LLM_MODEL_ID=llama3.1:8b
LLM_BASE_URL=http://localhost:11434
LLM_STUB_MODE=false
```

### Use Groq API (Remote - Has rate limits):
```env
LLM_PROVIDER=openai_compatible
LLM_MODEL_ID=llama-3.3-70b-versatile
LLM_API_KEY=your-groq-api-key
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_STUB_MODE=false
```

### Use Stub Mode (Testing - No LLM calls):
```env
LLM_STUB_MODE=true
```

## Troubleshooting

### Ollama not responding:
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, restart Ollama service (Windows):
taskkill /F /IM ollama.exe
ollama serve
```

### Model not found error:
```bash
# List installed models
ollama list

# If llama3.1:8b is not listed, pull it
ollama pull llama3.1:8b
```

### Slow inference:
- Switch to a smaller model: `llama3.2:3b`
- Update `.env`: `LLM_MODEL_ID=llama3.2:3b`

### Out of memory:
- Use smaller model: `llama3.2:3b` or `llama3.2:1b`
- Close other applications

## Performance Comparison

| Provider | Rate Limit | Speed | Cost | Quality |
|----------|------------|-------|------|---------|
| **Ollama (local)** | ⚡ None | Medium | Free | Good |
| Groq API | ❌ 12K TPM | Very Fast | Free (limited) | Very Good |
| OpenAI API | ⚠️ Varies | Fast | $$ Paid | Excellent |

## Next Steps

Once Ollama is working:
1. Run the full replay test: `python replay_runner.py`
2. Check `replay_results.json` for accuracy metrics
3. All 100 cases should complete without rate limit errors!

## Support

- Ollama docs: https://ollama.com/docs
- Model library: https://ollama.com/library
- Common issues: See OLLAMA_SETUP.md

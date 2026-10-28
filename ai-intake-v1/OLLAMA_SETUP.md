# Ollama Setup Instructions

## 1. Download and Install Ollama

### Windows:
1. Go to https://ollama.com/download/windows
2. Download `OllamaSetup.exe`
3. Run the installer
4. Ollama will run as a service on `http://localhost:11434`

### Verify Installation:
```bash
ollama --version
```

## 2. Download a Suitable Model

For this legal intake agent, we recommend `llama3.1:8b` (4.7GB) or `llama3.2:3b` (2GB) for faster inference:

### Recommended: Llama 3.1 8B (Good balance)
```bash
ollama pull llama3.1:8b
```

### Alternative: Llama 3.2 3B (Faster, smaller)
```bash
ollama pull llama3.2:3b
```

### Alternative: Llama 3.1 70B (Best quality, requires powerful GPU)
```bash
ollama pull llama3.1:70b
```

## 3. Test the Model

```bash
ollama run llama3.1:8b "Hello, how are you?"
```

## 4. Keep Ollama Running

Ollama runs as a background service. To check if it's running:

```bash
curl http://localhost:11434/api/tags
```

You should see a JSON response with available models.

## 5. Update .env Configuration

After installation, update your `.env` file to use Ollama:

```env
LLM_PROVIDER=ollama
LLM_MODEL_ID=llama3.1:8b
LLM_BASE_URL=http://localhost:11434
LLM_STUB_MODE=false
```

## Model Recommendations

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| llama3.2:3b | 2GB | Very Fast | Good | Testing/Development |
| llama3.1:8b | 4.7GB | Fast | Very Good | Production (Recommended) |
| llama3.1:70b | 40GB | Slow | Excellent | High accuracy requirements |
| qwen2.5:7b | 4.7GB | Fast | Very Good | Alternative option |

## Troubleshooting

### Ollama not responding:
```bash
# Windows: Restart Ollama service
taskkill /F /IM ollama.exe
ollama serve
```

### Check running models:
```bash
ollama list
```

### Remove a model:
```bash
ollama rm llama3.1:8b
```

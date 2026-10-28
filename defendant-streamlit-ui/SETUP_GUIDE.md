# Setup Guide - AI Intake Agent V1

This guide will help you configure API keys and database settings for the AI Intake Agent.

## Quick Start

### 1. Create your `.env` file

First, copy the example file to create your actual environment file:

**On Linux/Mac:**
```bash
cp .env.example .env
```

**On Windows:**
```bash
copy .env.example .env
```

### 2. Database Setup (Already Configured!)

The default configuration uses **SQLite**, which requires no additional setup:
```
DATABASE_URL=sqlite+aiosqlite:///./ai_intake_v1.db
```

The database file will be created automatically when you run the application. No credentials needed.

### 3. LLM API Key Setup

You have two options:

#### **Option A: Stub Mode (No API Key - Good for Testing)**

Keep the current settings in your `.env` file:
```env
LLM_STUB_MODE=true
LLM_API_KEY=
```

**Benefits:**
- The system will use heuristic stubs instead of real LLM calls
- No cost, no API key needed
- Great for development and testing

#### **Option B: Real LLM Mode (Requires API Key)**

**Step 1: Get a free OpenRouter API key**
1. Go to: https://openrouter.ai/
2. Sign up for a free account
3. Navigate to "Keys" section
4. Create a new API key

**Step 2: Update your `.env` file**
```env
LLM_PROVIDER=openai_compatible
LLM_MODEL_ID=google/gemini-2.0-flash-thinking-exp:free
LLM_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxx  # Replace with your actual API key
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_TIMEOUT_SECONDS=45
LLM_STUB_MODE=false  # IMPORTANT: Change this to false
```

### 4. Complete `.env` File Example

Your minimal `.env` file should look like this:

```env
APP_NAME=AI Intake Agent V1
ENV=dev
DATABASE_URL=sqlite+aiosqlite:///./ai_intake_v1.db
OUTBOUND_KILL_SWITCH=false

# LLM Provider Configuration
LLM_PROVIDER=openai_compatible
LLM_MODEL_ID=google/gemini-2.0-flash-thinking-exp:free
LLM_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxx  # Your actual key (or leave blank for stub mode)
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_TIMEOUT_SECONDS=45

# Set to false to enable real LLM calls (requires LLM_API_KEY)
# Set to true to use heuristic stub (no API key needed)
LLM_STUB_MODE=false  # Set to true for stub mode, false for real API calls
```

## Alternative LLM Providers

### Using OpenAI Directly

```env
LLM_PROVIDER=openai_compatible
LLM_MODEL_ID=gpt-4o-mini
LLM_API_KEY=sk-proj-xxxxxxxxxxxxxxxx
LLM_BASE_URL=https://api.openai.com/v1
LLM_STUB_MODE=false
```

Get API key from: https://platform.openai.com/api-keys

### Using Anthropic Claude

```env
LLM_PROVIDER=openai_compatible
LLM_MODEL_ID=claude-3-5-sonnet-20241022
LLM_API_KEY=sk-ant-xxxxxxxxxxxxxxxx
LLM_BASE_URL=https://api.anthropic.com/v1
LLM_STUB_MODE=false
```

Get API key from: https://console.anthropic.com/settings/keys

## Verification

After setup, verify your configuration:

1. Check that `.env` file exists in project root
2. Ensure `LLM_API_KEY` is filled if `LLM_STUB_MODE=false`
3. Run the application to test database creation
4. Check logs for successful LLM provider connection

## Troubleshooting

**Issue: Database not created**
- Ensure you have write permissions in the project directory
- Check that `DATABASE_URL` is properly formatted

**Issue: LLM API errors**
- Verify your API key is valid
- Check that `LLM_STUB_MODE=false` if you want to use real LLM
- Ensure you have credits/quota on your LLM provider account

**Issue: Application won't start**
- Confirm `.env` file exists (not `.env.example`)
- Check for syntax errors in `.env` file
- Ensure all required environment variables are set

## Next Steps

1. Install dependencies (if not done): `pip install -r requirements.txt`
2. Initialize the database: `python -m app.db.init_db` (if applicable)
3. Start the application: `uvicorn app.main:app --reload`
4. Access the API documentation at: `http://localhost:8000/docs`

## Security Notes

- Never commit your `.env` file to version control
- Keep your API keys secure and rotate them regularly
- Use stub mode for development when possible to save costs
- The `.env` file is already in `.gitignore`

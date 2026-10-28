# Gmail Ingestion Setup Guide

This guide walks through setting up the read-only Gmail ingestion pipeline for attorney decision extraction per build brief Section 13.

## Prerequisites

- Google Workspace account with admin access
- Python 3.11+
- Gmail API enabled for your Google Cloud project
- Understanding of OAuth 2.0 and domain-wide delegation

## Quick Start

### 1. Install Dependencies

```bash
# Install project dependencies (includes Google client libraries)
pip install -e .
```

### 2. Create Google Cloud Service Account

**Step 2.1: Create Project (if needed)**
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create new project: "AI Intake Agent"
3. Note the project ID

**Step 2.2: Enable Gmail API**
1. In Cloud Console, go to "APIs & Services" > "Library"
2. Search for "Gmail API"
3. Click "Enable"

**Step 2.3: Create Service Account**
1. Go to "IAM & Admin" > "Service Accounts"
2. Click "Create Service Account"
3. Name: `gmail-readonly-ingestion`
4. Description: "Read-only Gmail access for attorney decision extraction"
5. Click "Create and Continue"
6. Skip role assignment (no project-level roles needed)
7. Click "Done"

**Step 2.4: Create Key**
1. Click on the newly created service account
2. Go to "Keys" tab
3. Click "Add Key" > "Create New Key"
4. Choose "JSON" format
5. Click "Create"
6. Save the downloaded JSON file securely (you'll need this!)

**Step 2.5: Note the Client ID**
1. In the service account details, find the "Unique ID" (numeric)
2. Copy this ID - you'll need it for domain-wide delegation

### 3. Set Up Domain-Wide Delegation

**IMPORTANT**: This requires Google Workspace admin access.

**Step 3.1: Enable Domain-Wide Delegation**
1. In the service account details, click "Advanced settings"
2. Check "Enable Google Workspace Domain-wide Delegation"
3. Save changes

**Step 3.2: Authorize Scopes in Workspace**
1. Go to [Google Workspace Admin Console](https://admin.google.com)
2. Navigate to: Security > Access and data control > API controls
3. Scroll to "Domain-wide delegation"
4. Click "Add new"
5. Enter the service account Client ID from step 2.5
6. Add OAuth scope: `https://www.googleapis.com/auth/gmail.readonly`
   - ⚠️ **CRITICAL**: Use ONLY `gmail.readonly` (read-only access)
   - Do NOT add write scopes
7. Click "Authorize"

### 4. Configure Environment Variables

**Step 4.1: Copy the service account JSON**

```bash
# Option A: Set as environment variable (JSON string)
export GMAIL_SERVICE_ACCOUNT_JSON='{"type":"service_account","project_id":"...","private_key":"..."}'

# Option B: Use .env file (recommended for development)
# Create .env file in project root and add:
cat >> .env <<'EOF'

# Gmail Integration (build brief Section 13)
GMAIL_SERVICE_ACCOUNT_JSON='PASTE_YOUR_SERVICE_ACCOUNT_JSON_HERE'
GMAIL_ENABLED=true
GMAIL_DEFAULT_MAILBOX=attorney@yourfirm.com
GMAIL_CONFIDENCE_THRESHOLD=0.7

# LLM Configuration (for extraction)
LLM_STUB_MODE=false
LLM_API_KEY=your_groq_api_key_here
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL_ID=llama-3.1-70b-versatile

EOF
```

**Step 4.2: Secure the credentials**

```bash
# Set restrictive permissions on .env file
chmod 600 .env

# Add to .gitignore to prevent accidental commit
echo ".env" >> .gitignore
```

### 5. Initialize Database

```bash
# Run database migrations to create Gmail tables
python -m scripts.init_db
```

### 6. Verify Setup

**Test authentication:**

```python
# test_gmail_auth.py
from app.services.gmail_auth import GmailAuthService

# Load credentials
auth_service = GmailAuthService.load_service_account_from_env()
auth = GmailAuthService(service_account_json=auth_service)

# Test delegation for a mailbox
creds = auth.get_delegated_credentials("attorney@yourfirm.com")
print(f"✓ Successfully authenticated with delegation")
print(f"  Scopes: {creds.scopes}")
print(f"  Subject: {creds._subject}")
```

**Test message fetching:**

```python
# test_gmail_fetch.py
from app.services.gmail_auth import GmailAuthService
from app.services.gmail_client import GmailClient

auth_service = GmailAuthService.load_service_account_from_env()
auth = GmailAuthService(service_account_json=auth_service)

client = GmailClient(auth, "attorney@yourfirm.com")

# Search for test messages
message_ids, _ = client.search_messages("subject:test", max_results=5)
print(f"✓ Found {len(message_ids)} messages")

# Fetch first message
if message_ids:
    msg = client.get_message(message_ids[0])
    print(f"  Subject: {msg.subject}")
    print(f"  From: {msg.from_email}")
```

### 7. Run First Sync

**Start the API server:**

```bash
uvicorn app.main:app --reload
```

**Trigger a test sync via API:**

```bash
curl -X POST http://localhost:8000/api/gmail/sync \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "mailbox": "attorney@yourfirm.com",
      "prospect_identifiers": [
        {"email": "testclient@example.com"}
      ],
      "max_messages": 10,
      "confidence_threshold": 0.7
    },
    "initiated_by": "user:admin"
  }'
```

**Poll sync status:**

```bash
# Replace SYNC_ID with the ID returned from the POST request
curl http://localhost:8000/api/gmail/sync/SYNC_ID/status
```

**View extracted decisions:**

```bash
curl http://localhost:8000/api/gmail/decisions
```

## Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GMAIL_SERVICE_ACCOUNT_JSON` | Yes | None | Service account credentials (JSON string) |
| `GMAIL_ENABLED` | No | false | Enable Gmail ingestion features |
| `GMAIL_DEFAULT_MAILBOX` | No | "" | Default attorney mailbox for sync |
| `GMAIL_CONFIDENCE_THRESHOLD` | No | 0.7 | Min confidence for auto-accept extraction |
| `LLM_STUB_MODE` | No | true | Use stub LLM (set false for real extraction) |
| `LLM_API_KEY` | Yes* | None | LLM API key (*required if stub_mode=false) |

### GmailSyncConfig Parameters

```python
GmailSyncConfig(
    mailbox="attorney@firm.com",           # Required: mailbox to sync
    prospect_identifiers=[                 # Required: prospects to search for
        {"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com"},
        {"email": "john@example.com", "phone": "+1234567890"}
    ],
    date_range_start="2024-01-01T00:00:00Z",  # Optional: filter by date
    date_range_end="2024-12-31T23:59:59Z",    # Optional: filter by date
    query_filter="from:jibrael@",             # Optional: additional Gmail filter
    max_messages=100,                         # Optional: max messages per sync (1-1000)
    confidence_threshold=0.7                  # Optional: min confidence for auto-accept
)
```

## Troubleshooting

### Error: "Authentication failed: Unauthorized"

**Cause**: Domain-wide delegation not properly configured

**Fix**:
1. Verify service account Client ID in Workspace admin console
2. Ensure `gmail.readonly` scope is authorized
3. Wait 5-10 minutes for changes to propagate
4. Try again

### Error: "Missing gmail.readonly scope"

**Cause**: Service account credentials don't have the required scope

**Fix**:
1. Check the service account JSON has all required fields
2. Re-download service account key from Cloud Console
3. Verify domain-wide delegation scope matches exactly: `https://www.googleapis.com/auth/gmail.readonly`

### Error: "No messages found"

**Cause**: Search query returned no results

**Debugging**:
```python
# Build and test query manually
from app.services.gmail_client import GmailClient

client = GmailClient(auth, "attorney@yourfirm.com")
query = client.build_prospect_query(
    first_name="Jane",
    last_name="Doe",
    email="jane@example.com"
)
print(f"Query: {query}")

# Try broader search
message_ids, _ = client.search_messages("subject:*", max_results=5)
print(f"Total messages in mailbox: {len(message_ids)}")
```

### Low Extraction Confidence

**Cause**: LLM unable to identify clear attorney decision in thread

**Fixes**:
- Review email thread manually - is decision explicit?
- Adjust confidence threshold if extraction is actually correct
- Provide more context via `query_filter` to narrow results
- Flag for human review (expected behavior for ambiguous threads)

## Security Checklist

- [ ] Service account has ONLY `gmail.readonly` scope (no write access)
- [ ] Service account JSON stored securely (not committed to git)
- [ ] Environment variables set with restrictive permissions (`chmod 600 .env`)
- [ ] Mailbox access limited to necessary attorney accounts
- [ ] Audit logs enabled and monitored
- [ ] LLM provider has zero-retention agreement (per build brief)

## Next Steps

1. **Test with 100-case training corpus**: Run sync for all prospects from training data
2. **Review extracted decisions**: Validate accuracy and flag any hallucinations
3. **Tune confidence threshold**: Adjust based on review feedback
4. **Set up monitoring**: Track sync failures, extraction errors, API quota
5. **Document decision patterns**: Build knowledge base of attorney decision language

## Production Deployment

**Before production**:
1. Move credentials to secure secrets manager (AWS Secrets Manager, Google Secret Manager)
2. Enable MFA for all admin accounts with delegation access
3. Set up monitoring and alerting for sync failures
4. Implement rate limiting to avoid Gmail API quota exhaustion
5. Review and document privileged email handling procedures with legal team
6. Obtain partner sign-off on LLM extraction prompts
7. Test disaster recovery (credential rotation, failover mailbox)

## Support

For issues or questions:
1. Check logs: `tail -f app.log`
2. Review audit trail: `SELECT * FROM audit_log WHERE entity_type='gmail_sync_record' ORDER BY occurred_at DESC;`
3. Contact: [Your support contact]

---

**Build Brief Reference**: Section 13 (Gmail Attorney Decision Extraction)

**Compliance**: Read-only access, PII minimization, human review, full audit trail

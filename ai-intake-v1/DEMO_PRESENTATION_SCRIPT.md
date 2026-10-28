# AI Intake Agent V1 - Demo Presentation Script

## Pre-Demo Setup Checklist
```bash
# Terminal 1: Start the server
cd "D:\AI_Intake_Agent\ai-intake-v1-phase2\ai-intake-v1"
source .venv/Scripts/activate
uvicorn app.main:app --reload

# Terminal 2: Keep ready for API calls
# Browser tabs ready:
#   - http://127.0.0.1:8000/dashboard
#   - http://127.0.0.1:8000/docs
```

---

## SCRIPT

### Opening (30 seconds)
**[Screen: Project README or title slide]**

> "Today I'm presenting the AI Intake Agent V1 - a supervision-first legal intake platform that converts prospective client conversations into structured, attorney-reviewable summaries.
>
> The key principle here is: **build for supervision first, intelligence second**. The system is designed for compliance, auditability, and human review - not autonomous decision-making."

---

### Architecture Overview (1 minute)
**[Screen: design-doc.md or architecture diagram]**

> "Let me walk through the architecture briefly.
>
> **What the LLM handles:**
> - Practice area classification (TCPA, FCRA, FDCPA, mass arbitration)
> - Targeted evidence requests
> - Neutral structured summary generation
>
> **What stays server-side and deterministic:**
> - JSON schema validation
> - Compliance checks
> - Cross-practice detection rules
> - Follow-up scheduling with quiet-hours
> - All audit logging
> - PII redaction
>
> This separation is intentional. The model never decides whether to accept a case - that's always a human decision."

---

### Sample User Journey (1.5 minutes)
**[Screen: ARCHITECTURE_DIAGRAM.md - Data Flow section, or draw on whiteboard]**

> "Let me walk through a typical user journey - what happens when a prospect reaches out.
>
> **Step 1: Prospect Sends Message**
> A prospect contacts the firm via chat, email, or web form saying: *'I keep getting robocalls from a debt collector on my cell phone. They call 5-6 times a day.'*
>
> **Step 2: PII Redaction**
> Before anything is stored, our server-side code scans for sensitive data - Social Security numbers, dates of birth, full account numbers. These are automatically redacted. The model never sees raw PII.
>
> **Step 3: Classification (LLM)**
> The sanitized transcript goes to the LLM for classification. Based on the keywords 'robocalls', 'cell phone', and 'debt collector', it classifies this as **TCPA** with high confidence - the issue is the *method* of contact, not the debt itself.
>
> **Step 4: Evidence Check**
> The system checks what evidence is needed for a TCPA case: call logs, caller ID screenshots, dates and times. It identifies what's missing from the conversation.
>
> **Step 5: Targeted Follow-up Questions**
> Because this is TCPA, the system asks TCPA-specific questions: *'Do you have call logs showing the incoming calls? Can you provide screenshots of the caller ID?'* - not generic questions, but practice-area-specific ones.
>
> **Step 6: Summary Generation (LLM)**
> Once enough information is gathered, the LLM generates a neutral, factual summary. No legal advice, no outcome predictions - just facts.
>
> **Step 7: Schema Validation**
> The summary must pass strict Pydantic schema validation. If the JSON is malformed or missing required fields, it's rejected before it ever reaches a reviewer.
>
> **Step 8: Human Review Queue**
> The validated summary lands in the reviewer dashboard. An attorney or intake specialist reviews it and decides: approve, modify, or reject.
>
> The key point: **the model assists, but humans decide**. No case is accepted or rejected without human review."

---

### API Documentation (45 seconds)
**[Screen: http://127.0.0.1:8000/docs]**

> "Here's our FastAPI documentation. The key endpoints are:
>
> - **POST /api/intake/messages** - receives prospect messages with automatic PII sanitization
> - **POST /api/intake/conversations/{id}/finalize** - generates the structured summary
> - **GET /api/review/queue** - returns pending items for reviewer
> - **POST /api/review/summaries/{id}/decision** - records approve, modify, or reject actions
>
> Every action here writes to the audit log with full before-and-after state tracking."

---

### Dashboard Demo - Pending Queue (1.5 minutes)
**[Screen: http://127.0.0.1:8000/dashboard]**

> "This is the reviewer dashboard. Notice the four tabs: Pending, Approved, Modified, and Rejected.
>
> Let me select an item from the pending queue..."

**[Click on a pending item]**

> "On the right, you see the full summary JSON - practice area classification, secondary areas, cross-practice flag, evidence checklist, and the recommendation.
>
> The reviewer has three options:
>
> **Approve** - if the classification and summary are correct
> **Modify** - if adjustments are needed
> **Reject** - if it's spam, duplicate, or clearly wrong-fit"

---

### Dashboard Demo - Approve Action (1 minute)
**[Click Approve button, enter reviewer ID]**

> "When I click Approve, the system prompts for my Reviewer ID - this ensures attribution for every decision.
>
> Watch what happens... the item moves from Pending to the Approved tab."

**[Switch to Approved tab]**

> "Here in the Approved tab, you can see the reviewer ID, timestamp, and disposition are all recorded. This creates the audit trail required for legal compliance."

---

### Dashboard Demo - Modify Workflow (1.5 minutes)
**[Switch back to Pending tab, select another item, click Modify]**

> "The Modify workflow is more involved. When I click Modify, I get an editable JSON textarea.
>
> Let me demonstrate - say the LLM classified this as FDCPA but I believe it's actually TCPA based on the transcript..."

**[Edit the JSON, change practice_area]**

> "I'll change the primary_practice_area from 'fdcpa' to 'tcpa'.
>
> The system validates the JSON format before submission - invalid JSON gets rejected client-side.
>
> Now I click 'Confirm Modification' and enter my reviewer ID..."

**[Confirm and enter reviewer ID]**

> "The original summary is preserved in the audit log, and this modified version becomes the official record. Check the Modified tab to see it."

---

### Dashboard Demo - Reject Action (45 seconds)
**[Select another pending item, click Reject]**

> "For rejection, I'm prompted for my reviewer ID and an optional reason.
>
> This might be used for spam submissions, clearly wrong-fit leads, or duplicates. The rejection reason is stored in the audit log for accountability."

**[Enter reviewer ID and reason, confirm]**

---

### LLM Provider Configuration (1 minute)
**[Screen: .env file or config.py]**

> "The system supports three LLM modes:
>
> **Stub mode** - default, uses heuristics, no external API calls. Perfect for CI testing.
>
> **Ollama mode** - runs locally with models like llama3.1:8b. Great for development without cloud costs.
>
> **Groq mode** - cloud API with fast inference on llama-3.1-70b-versatile.
>
> Switching is just environment variable changes. The same codebase works with all three."

---

### Replay Testing & Accuracy Metrics (1 minute)
**[Screen: LLM_approach_improvement_next_steps.md]**

> "We validate accuracy using a 100-case replay test corpus with gold labels.
>
> Current metrics:
> - Primary classification: 78%
> - Secondary areas: 42%
> - Cross-practice flag: 61%
> - Recommendation logic: 75%
>
> Better heuristics and iterative evaluation is required, to improve the metrics for this legal intake system."

---

### Audit & Compliance Features (45 seconds)
**[Screen: Show audit_logs table or API response]**

> "Every significant action is logged:
> - Conversation creation
> - Message receipt with PII redaction
> - Summary generation with prompt hash
> - Reviewer decisions with before/after state
> - Follow-up scheduling and sends
>
> Historical records are immutable in intent. We preserve append-only semantics throughout."

---

### Closing (30 seconds)
**[Screen: README or summary slide]**

> "To summarize: AI Intake Agent V1 is a compliance-first scaffold that:
>
> - Converts intake conversations to structured JSON
> - Routes to human reviewers before any case-impacting action
> - Maintains full audit trails
> - Keeps policy logic outside the model
>
> It's designed for supervision first - because in legal tech, auditability and human oversight aren't optional features. They're the foundation.
>
> Thank you."

---

## Total Runtime: ~11-12 minutes

## Tips for Recording
1. **Pause briefly** between sections for editing cuts
2. **Zoom in** on JSON when showing summary details
3. **Use a clean browser** (no bookmarks bar, minimal extensions)
4. **Pre-populate** 3-4 pending items so you have enough to demo
5. **Test the approve/modify/reject** flow once before recording

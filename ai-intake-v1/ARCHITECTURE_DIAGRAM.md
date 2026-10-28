# AI Intake Agent V1 - Architecture Diagram

## High-Level System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              INBOUND CHANNELS                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │  GHL Chat    │  │    Email     │  │  Web Form    │  │  Streamlit   │             │
│  │  (webhook)   │  │   (Gmail)    │  │    (API)     │  │     UI       │             │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘             │
│         │                 │                 │                 │                      │
└─────────┼─────────────────┼─────────────────┼─────────────────┼──────────────────────┘
          │                 │                 │                 │
          └─────────────────┴────────┬────────┴─────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           FASTAPI BACKEND (app/)                                     │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                         API LAYER (app/api/)                                 │    │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │    │
│  │  │ routes_intake   │  │ routes_review   │  │ routes_followup │              │    │
│  │  │ - POST messages │  │ - GET queue     │  │ - GET due       │              │    │
│  │  │ - POST finalize │  │ - GET summary   │  │ - POST run      │              │    │
│  │  │ - GET convo     │  │ - POST decision │  │                 │              │    │
│  │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘              │    │
│  └───────────┼────────────────────┼────────────────────┼────────────────────────┘    │
│              │                    │                    │                             │
│              └────────────────────┼────────────────────┘                             │
│                                   ▼                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                      SERVICE LAYER (app/services/)                           │    │
│  │                                                                              │    │
│  │  ┌──────────────────────────────────────────────────────────────────────┐   │    │
│  │  │                    LLM BOUNDARY (llm_agent_core.py)                   │   │    │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                   │   │    │
│  │  │  │ Stub Mode   │  │ Ollama Mode │  │ Groq Mode   │                   │   │    │
│  │  │  │ (heuristic) │  │ (local LLM) │  │ (cloud API) │                   │   │    │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘                   │   │    │
│  │  │                           │                                           │   │    │
│  │  │  LLM TASKS ONLY:          ▼                                           │   │    │
│  │  │  • Classification    ┌─────────────────────────┐                      │   │    │
│  │  │  • Evidence Request  │   System Prompt v1      │                      │   │    │
│  │  │  • Summary Gen       │   (SHA-256 versioned)   │                      │   │    │
│  │  │                      └─────────────────────────┘                      │   │    │
│  │  └──────────────────────────────────────────────────────────────────────┘   │    │
│  │                                                                              │    │
│  │  ┌──────────────────────────────────────────────────────────────────────┐   │    │
│  │  │              DETERMINISTIC LAYER (server-side policy)                 │   │    │
│  │  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐         │   │    │
│  │  │  │    PII     │ │  Evidence  │ │   Cross-   │ │  Follow-up │         │   │    │
│  │  │  │  Redactor  │ │ Checklist  │ │  Practice  │ │  Scheduler │         │   │    │
│  │  │  │  (pii.py)  │ │(evidence.py│ │   Rules    │ │(followup.py│         │   │    │
│  │  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘         │   │    │
│  │  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐         │   │    │
│  │  │  │   Schema   │ │   Audit    │ │   Router   │ │ Quiet-Hours│         │   │    │
│  │  │  │ Validation │ │   Logger   │ │  & Queue   │ │  Opt-Out   │         │   │    │
│  │  │  │ (Pydantic) │ │ (audit.py) │ │(router.py) │ │   Policy   │         │   │    │
│  │  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘         │   │    │
│  │  └──────────────────────────────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                   │                                                  │
└───────────────────────────────────┼──────────────────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            DATABASE LAYER (SQLite/Postgres)                          │
│                                                                                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │
│  │  Prospects  │ │Conversations│ │  Messages   │ │  Intake     │ │  Follow-up  │    │
│  │             │ │             │ │ (sanitized) │ │  Summaries  │ │    Tasks    │    │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘    │
│  ┌─────────────┐ ┌─────────────┐                                                     │
│  │  Audit Log  │ │ LLM Call    │  ← Append-only / Immutable intent                   │
│  │ (immutable) │ │  Records    │  ← Replay & audit support                           │
│  └─────────────┘ └─────────────┘                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           REVIEWER DASHBOARD (/dashboard)                            │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────┐      │
│  │  TABS:  [ Pending ]  [ Approved ]  [ Modified ]  [ Rejected ]             │      │
│  └───────────────────────────────────────────────────────────────────────────┘      │
│                                                                                      │
│  ┌─────────────────────────┐    ┌────────────────────────────────────────────┐      │
│  │      QUEUE LIST         │    │            SUMMARY DETAIL                   │      │
│  │  ┌───────────────────┐  │    │  ┌──────────────────────────────────────┐  │      │
│  │  │ TCPA - route_atty │  │    │  │  Practice Area: TCPA                 │  │      │
│  │  │ Created: 6/14/26  │  │───▶│  │  Confidence: 0.85                    │  │      │
│  │  └───────────────────┘  │    │  │  Fact Pattern: Prospect reports...   │  │      │
│  │  ┌───────────────────┐  │    │  │  Evidence: [x] Call logs [ ] ...     │  │      │
│  │  │ FDCPA - req_evid  │  │    │  │  Recommendation: route_to_attorney   │  │      │
│  │  │ Created: 6/14/26  │  │    │  └──────────────────────────────────────┘  │      │
│  │  └───────────────────┘  │    │                                            │      │
│  │         ...             │    │  ┌──────────┐ ┌──────────┐ ┌──────────┐   │      │
│  └─────────────────────────┘    │  │ APPROVE  │ │  MODIFY  │ │  REJECT  │   │      │
│                                  │  └──────────┘ └──────────┘ └──────────┘   │      │
│                                  └────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow - Intake to Review

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                      │
│   1. PROSPECT          2. PII              3. CLASSIFY           4. EVIDENCE        │
│      MESSAGE              REDACT              (LLM)                 CHECK            │
│                                                                                      │
│   ┌──────────┐        ┌──────────┐        ┌──────────┐        ┌──────────┐          │
│   │ "I keep  │        │ SSN/DOB  │        │  TCPA    │        │ Missing: │          │
│   │ getting  │───────▶│ removed  │───────▶│  0.85    │───────▶│ Call logs│          │
│   │ robocalls│        │          │        │ confidence│       │ Dates    │          │
│   │ ..."     │        │          │        │          │        │          │          │
│   └──────────┘        └──────────┘        └──────────┘        └──────────┘          │
│                                                                     │                │
│                                                                     ▼                │
│   8. AUDIT             7. PERSIST          6. VALIDATE          5. GENERATE         │
│      LOG                  SUMMARY             SCHEMA               SUMMARY           │
│                                                                    (LLM)             │
│   ┌──────────┐        ┌──────────┐        ┌──────────┐        ┌──────────┐          │
│   │ Event:   │        │ DB Write │        │ Pydantic │        │ Neutral  │          │
│   │ summary  │◀───────│ + review │◀───────│ schema   │◀───────│ fact     │          │
│   │ created  │        │ queue    │        │ check    │        │ summary  │          │
│   │          │        │          │        │          │        │          │          │
│   └──────────┘        └──────────┘        └──────────┘        └──────────┘          │
│                             │                                                        │
│                             ▼                                                        │
│                       ┌──────────┐                                                   │
│                       │ REVIEWER │──────▶ Approve / Modify / Reject                  │
│                       │DASHBOARD │        (audit logged with before/after)           │
│                       └──────────┘                                                   │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## LLM vs Deterministic Boundary

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                      │
│    ┌─────────────────────────────┐      ┌─────────────────────────────────────┐     │
│    │      LLM OWNED              │      │       DETERMINISTIC (Server-Side)   │     │
│    │      (model calls)          │      │       (code-enforced policy)        │     │
│    │                             │      │                                     │     │
│    │  ✓ Practice area            │      │  ✓ JSON schema validation           │     │
│    │    classification           │      │  ✓ Compliance checks & blocking     │     │
│    │                             │      │  ✓ Cross-practice must-fire rules   │     │
│    │  ✓ Targeted evidence        │      │  ✓ Routing & queue escalation       │     │
│    │    request generation       │      │  ✓ Follow-up cadence timing         │     │
│    │                             │      │  ✓ Quiet-hours enforcement          │     │
│    │  ✓ Neutral summary          │      │  ✓ Opt-out handling                 │     │
│    │    generation               │      │  ✓ Kill switch behavior             │     │
│    │                             │      │  ✓ PII redaction                    │     │
│    │                             │      │  ✓ Audit logging                    │     │
│    │                             │      │  ✓ Template-based follow-ups        │     │
│    │                             │      │                                     │     │
│    │  ╔═══════════════════════╗  │      │  ╔═════════════════════════════╗    │     │
│    │  ║ Model NEVER decides:  ║  │      │  ║ Human review REQUIRED for:  ║    │     │
│    │  ║ • Case acceptance     ║  │      │  ║ • Case acceptance           ║    │     │
│    │  ║ • Outcome prediction  ║  │      │  ║ • External communications   ║    │     │
│    │  ║ • Legal advice        ║  │      │  ║ • Summary approval          ║    │     │
│    │  ╚═══════════════════════╝  │      │  ╚═════════════════════════════╝    │     │
│    │                             │      │                                     │     │
│    └─────────────────────────────┘      └─────────────────────────────────────┘     │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## LLM Provider Options

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              LLM PROVIDER MODES                                      │
│                                                                                      │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐          │
│  │     STUB MODE       │  │    OLLAMA MODE      │  │     GROQ MODE       │          │
│  │     (Default)       │  │     (Local)         │  │     (Cloud)         │          │
│  │                     │  │                     │  │                     │          │
│  │  LLM_STUB_MODE=true │  │  LLM_STUB_MODE=false│  │  LLM_STUB_MODE=false│          │
│  │                     │  │  LLM_PROVIDER=ollama│  │  LLM_PROVIDER=      │          │
│  │  • No API calls     │  │  LLM_BASE_URL=      │  │    openai_compatible│          │
│  │  • Heuristic-based  │  │   localhost:11434   │  │  LLM_BASE_URL=      │          │
│  │  • CI-friendly      │  │  LLM_MODEL_ID=      │  │   api.groq.com      │          │
│  │  • Free             │  │   llama3.1:8b       │  │  LLM_API_KEY=xxx    │          │
│  │                     │  │                     │  │                     │          │
│  │  Use for:           │  │  Use for:           │  │  Use for:           │          │
│  │  • Testing          │  │  • Development      │  │  • Production eval  │          │
│  │  • CI/CD            │  │  • No cloud costs   │  │  • Higher accuracy  │          │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘          │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## Database Schema Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                DATABASE TABLES                                       │
│                                                                                      │
│  ┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐            │
│  │    PROSPECTS    │       │  CONVERSATIONS  │       │    MESSAGES     │            │
│  ├─────────────────┤       ├─────────────────┤       ├─────────────────┤            │
│  │ id              │──┐    │ id              │──┐    │ id              │            │
│  │ first_name      │  │    │ prospect_id  ◀──┼──┘    │ conversation_id │◀───┐       │
│  │ last_name       │  │    │ channel         │  │    │ role            │    │       │
│  │ email           │  └───▶│ status          │  │    │ content (clean) │    │       │
│  │ phone           │       │ prompt_hash     │  │    │ created_at      │    │       │
│  │ state           │       │ created_at      │  │    └─────────────────┘    │       │
│  │ consent_status  │       └─────────────────┘  │                           │       │
│  └─────────────────┘                            │                           │       │
│                                                 │                           │       │
│  ┌─────────────────┐       ┌─────────────────┐  │    ┌─────────────────┐    │       │
│  │ INTAKE_SUMMARIES│       │  FOLLOW_UP_TASKS│  │    │ LLM_CALL_RECORDS│    │       │
│  ├─────────────────┤       ├─────────────────┤  │    ├─────────────────┤    │       │
│  │ id              │       │ id              │  │    │ id              │    │       │
│  │ conversation_id │◀──────│ summary_id      │  │    │ conversation_id │◀───┤       │
│  │ practice_area   │       │ template_id     │  │    │ provider        │    │       │
│  │ confidence      │       │ attempt_number  │  │    │ model_id        │    │       │
│  │ fact_pattern    │       │ due_at          │  │    │ operation       │    │       │
│  │ recommendation  │       │ sent_at         │  │    │ prompt_hash     │    │       │
│  │ review_status   │       │ blocked_reason  │  │    │ response_preview│    │       │
│  │ reviewer_id     │       └─────────────────┘  │    │ tokens_used     │    │       │
│  │ reviewed_at     │                            │    └─────────────────┘    │       │
│  │ raw_summary_json│                            │                           │       │
│  └─────────────────┘                            └───────────────────────────┘       │
│                                                                                      │
│  ┌─────────────────┐                                                                 │
│  │   AUDIT_LOG     │  ← Append-only by design                                        │
│  ├─────────────────┤                                                                 │
│  │ id              │                                                                 │
│  │ timestamp       │                                                                 │
│  │ actor           │                                                                 │
│  │ action          │                                                                 │
│  │ entity_type     │                                                                 │
│  │ entity_id       │                                                                 │
│  │ before_state    │  ← Original data preserved                                      │
│  │ after_state     │  ← Modified data recorded                                       │
│  └─────────────────┘                                                                 │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## Key Design Principles

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           DESIGN PRINCIPLES                                          │
│                                                                                      │
│   ╔═══════════════════════════════════════════════════════════════════════════╗     │
│   ║  1. SUPERVISION FIRST, INTELLIGENCE SECOND                                 ║     │
│   ║     Every case-impacting action requires human review                      ║     │
│   ╚═══════════════════════════════════════════════════════════════════════════╝     │
│                                                                                      │
│   ╔═══════════════════════════════════════════════════════════════════════════╗     │
│   ║  2. COMPLIANCE BY DESIGN                                                   ║     │
│   ║     No legal advice • No outcome prediction • No implied representation    ║     │
│   ╚═══════════════════════════════════════════════════════════════════════════╝     │
│                                                                                      │
│   ╔═══════════════════════════════════════════════════════════════════════════╗     │
│   ║  3. AUDITABILITY OVER CONVENIENCE                                          ║     │
│   ║     Every action logged • Immutable history • Full before/after tracking   ║     │
│   ╚═══════════════════════════════════════════════════════════════════════════╝     │
│                                                                                      │
│   ╔═══════════════════════════════════════════════════════════════════════════╗     │
│   ║  4. STRUCTURED OUTPUT FIRST                                                ║     │
│   ║     JSON schemas enforced • Pydantic validation • No free-form outputs     ║     │
│   ╚═══════════════════════════════════════════════════════════════════════════╝     │
│                                                                                      │
│   ╔═══════════════════════════════════════════════════════════════════════════╗     │
│   ║  5. POLICY STAYS SERVER-SIDE                                               ║     │
│   ║     Routing, quiet-hours, opt-out, kill switch = deterministic code        ║     │
│   ╚═══════════════════════════════════════════════════════════════════════════╝     │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

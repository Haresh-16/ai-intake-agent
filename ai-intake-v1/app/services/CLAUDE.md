# app/services/CLAUDE.md

## Scope
This folder owns business logic, policy boundaries, orchestration, audit helpers, LLM boundaries, and follow-up rules.

## Architectural split
### Model-owned tasks
- Classification
- Targeted evidence asks
- Neutral summary generation

### Deterministic tasks
- Compliance policy and blockers
- Routing and escalation
- Cross-practice must-fire rules
- Follow-up cadence
- Quiet-hours and opt-out handling
- PII redaction
- Audit logging
- Kill switch handling

## Rules
- If unsure whether logic belongs in the model, keep it in deterministic code.
- Make compliance-critical decisions legible and testable.
- Persist replay metadata for every LLM-backed operation.
- Never let a model output bypass schema validation.
- Preserve prompt versioning and prompt hashing.

## Common checks after edits
- Did the change expand model scope inappropriately?
- Did the change weaken audit coverage?
- Did the change break read-only integration assumptions?
- Did the change update tests and design docs?

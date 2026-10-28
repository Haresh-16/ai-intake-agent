# tests/CLAUDE.md

## Testing expectations
This codebase is compliance-sensitive. Tests are not optional follow-up work.

## Required habits
- Add or update tests with every behavior change.
- Prefer focused tests around schemas, routing, audit behavior, and policy enforcement.
- For any LLM-boundary change, test the validated output shape and attached request metadata.
- For follow-up changes, test quiet-hours, opt-out, and attempt count behavior.
- For schema changes, test both valid and invalid payloads.

## Minimum review questions
- What can fail silently?
- What could bypass human review?
- What could weaken compliance blocking?
- What drifted from the brief?

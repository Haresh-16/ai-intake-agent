# app/api/CLAUDE.md

## Scope
This folder owns API contracts, request/response behavior, and orchestration boundaries. Keep route handlers thin.

## Rules
- Validate inputs at the boundary.
- Do not put business policy directly in route handlers if it belongs in services.
- Keep route behavior explicit and auditable.
- Preserve stable response shapes unless the task explicitly changes the contract.
- If a response shape changes, update schemas, tests, and design-doc.md.

## For intake routes
- Preserve staged intake flow.
- Ensure transcript content is sanitized before persistence.
- Finalization must generate a validated summary before routing.
- Persist audit events for material actions.

## For review routes
- Original summaries are immutable in intent.
- Reviewer modifications must remain auditable.
- Do not bypass role or routing checks.

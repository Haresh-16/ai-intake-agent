# Claude Code Starter Pack for AI Intake Agent

Drop these files into the project repo to improve Claude Code performance and consistency.

Suggested locations:
- `CLAUDE.md` -> repo root
- `.claude/settings.json` -> repo root `.claude/`
- `.claude/hooks/*` -> repo root `.claude/hooks/`
- `.claude/commands/*` -> repo root `.claude/commands/`
- `app/api/CLAUDE.md`, `app/services/CLAUDE.md`, `tests/CLAUDE.md` -> matching subfolders

Recommended daily workflow:
1. Start feature work in plan mode.
2. Ask Claude to identify affected files and invariants before edits.
3. Implement one coherent slice at a time.
4. Run `/project:review-diff` or equivalent review command before commit.
5. Write `NEXT-STEPS.md` before clearing context on long-running work.

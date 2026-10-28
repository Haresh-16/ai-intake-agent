#!/usr/bin/env bash
set -euo pipefail
INPUT="$(cat)"
CMD="$(printf '%s' "$INPUT" | python -c 'import json,sys; raw=sys.stdin.read().strip();

try:data=json.loads(raw) if raw else {}
except Exception:data={}
obj=data.get("tool_input") or {}
print(obj.get("command") or "")')"
if printf '%s' "$CMD" | grep -Eq 'rm -rf /|git push --force|git reset --hard|drop database|truncate .*audit_log'; then
  echo "Blocked: dangerous command matched project safety policy."
  exit 2
fi
exit 0

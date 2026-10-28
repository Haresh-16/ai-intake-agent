#!/usr/bin/env bash
set -euo pipefail
INPUT="$(cat)"
FILE="$(printf '%s' "$INPUT" | python -c 'import json,sys; raw=sys.stdin.read().strip();

try:data=json.loads(raw) if raw else {}
except Exception:data={}
obj=data.get("tool_input") or {}
print(obj.get("file_path") or obj.get("path") or "")')"
case "$FILE" in
  *app/prompts/system_prompt_v1.txt|*secrets*|*.env|*.env.*)
    echo "Blocked: this file is protected. Prompt, env, and secret changes require explicit approval in the task."
    exit 2
    ;;
  *)
    exit 0
    ;;
esac

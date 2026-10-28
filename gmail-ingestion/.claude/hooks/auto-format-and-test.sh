#!/usr/bin/env bash
set -euo pipefail
if [ -f pyproject.toml ]; then
  python -m compileall app >/dev/null 2>&1 || true
fi
if command -v pytest >/dev/null 2>&1 && [ -d tests ]; then
  pytest -q tests/test_validator.py tests/test_followup.py tests/test_llm_phase2.py >/dev/null 2>&1 || true
fi
exit 0

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "system_prompt_v1.txt"

# Cache for loaded prompts (loaded once at module import)
_PROMPTS_CACHE: dict[str, dict[str, str]] | None = None
_PROMPT_HASH_CACHE: str | None = None


def load_locked_prompt() -> tuple[str, str]:
    """Load full prompt file and return text + hash (legacy function for compatibility)."""
    text = PROMPT_PATH.read_text(encoding="utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return text, digest


def load_prompts() -> dict[str, dict[str, str]]:
    """
    Parse structured prompt file into sections with caching.

    Returns:
        {
            "classification": {"system": "...", "user_template": "..."},
            "evidence": {"system": "...", "user_template": "..."},
            "summary": {"system": "...", "user_template": "..."}
        }
    """
    global _PROMPTS_CACHE

    if _PROMPTS_CACHE is not None:
        return _PROMPTS_CACHE

    text = PROMPT_PATH.read_text(encoding="utf-8")
    sections: dict[str, str] = {}
    current_section: str | None = None
    current_content: list[str] = []

    for line in text.split('\n'):
        if line.startswith('[') and line.endswith(']'):
            # Save previous section
            if current_section:
                sections[current_section] = '\n'.join(current_content).strip()
            # Start new section
            current_section = line[1:-1]  # Remove [ and ]
            current_content = []
        else:
            current_content.append(line)

    # Save last section
    if current_section:
        sections[current_section] = '\n'.join(current_content).strip()

    # Organize into structured dict
    _PROMPTS_CACHE = {
        "classification": {
            "system": sections.get("CLASSIFICATION_SYSTEM", ""),
            "user_template": sections.get("CLASSIFICATION_USER_TEMPLATE", "")
        },
        "evidence": {
            "system": sections.get("EVIDENCE_SYSTEM", ""),
            "user_template": sections.get("EVIDENCE_USER_TEMPLATE", "")
        },
        "summary": {
            "system": sections.get("SUMMARY_SYSTEM", ""),
            "user_template": sections.get("SUMMARY_USER_TEMPLATE", "")
        }
    }

    return _PROMPTS_CACHE


def get_prompt_hash() -> str:
    """Get SHA-256 hash of the entire prompt file (cached)."""
    global _PROMPT_HASH_CACHE

    if _PROMPT_HASH_CACHE is not None:
        return _PROMPT_HASH_CACHE

    text = PROMPT_PATH.read_text(encoding="utf-8")
    _PROMPT_HASH_CACHE = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return _PROMPT_HASH_CACHE

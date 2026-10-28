import re

SSN_RE = re.compile(r"\b\d{3}-?\d{2}-?\d{4}\b")
LONG_ACCOUNT_RE = re.compile(r"\b\d{12,19}\b")
DOB_RE = re.compile(r"\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])[/-](?:19|20)?\d{2}\b")


def redact_sensitive_text(text: str) -> str:
    text = SSN_RE.sub("[REDACTED_SSN]", text)
    text = LONG_ACCOUNT_RE.sub("[REDACTED_ACCOUNT]", text)
    text = DOB_RE.sub("[REDACTED_DOB]", text)
    return text


def contains_opt_out(text: str) -> bool:
    lowered = text.lower()
    phrases = [
        "stop",
        "unsubscribe",
        "do not text",
        "dont text",
        "do not contact",
        "opt out",
        "leave me alone",
    ]
    return any(p in lowered for p in phrases)

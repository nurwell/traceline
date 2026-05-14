from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RedactionResult:
    text: str
    changed: bool


SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)(authorization:\s*bearer\s+)[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)(authorization:\s*basic\s+)[A-Za-z0-9+/=-]+"),
    re.compile(r"(?i)(cookie:\s*)[^\s]+"),
    re.compile(r"(?i)((?:api[_-]?key|token|secret|password)=)[^\s&]+"),
    re.compile(r"(?i)((?:x-api-key|x-auth-token):\s*)[^\s]+"),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    re.compile(r"\b(?:postgres|postgresql|mysql|mongodb|redis)://[^\s]+", re.IGNORECASE),
)


def redact_text(text: str) -> RedactionResult:
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub(_replace_secret, redacted)
    return RedactionResult(text=redacted, changed=redacted != text)


def _replace_secret(match: re.Match[str]) -> str:
    if match.lastindex:
        return f"{match.group(1)}[REDACTED]"
    return "[REDACTED]"

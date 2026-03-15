from __future__ import annotations

RISKY_PHRASES = [
    "guarantee",
    "we guarantee",
    "100%",
    "will definitely",
    "we promise",
    "legal advice",
    "financial advice",
]

DISCLAIMER = "Note: We can discuss options and risks, but we don’t guarantee outcomes or provide formal legal/financial advice."


def apply_guardrails(text: str) -> str:
    lower = text.lower()
    if any(phrase in lower for phrase in RISKY_PHRASES):
        if DISCLAIMER not in text:
            return f"{text}\n\n{DISCLAIMER}"
    return text

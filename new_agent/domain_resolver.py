from __future__ import annotations

from typing import Dict, Optional

from .llm_client import LLMClient
from .models import DomainDecision

ALLOWED = {"Consulting", "AI/Tech", "HR", "Finance", "Legal", "General"}


def resolve_domain(
    message: str,
    llm: LLMClient,
    system_prompt: str,
) -> DomainDecision:
    """Only place allowed to set control_domain."""
    classifier_system_prompt = (
        "You are a strict classifier. Output ONLY valid JSON."
    )
    prompt = (
        "Classify the user's request into one of: Consulting, AI/Tech, HR, Finance, Legal, General. "
        "Return ONLY JSON: {\"control_domain\": <Consulting|AI/Tech|HR|Finance|Legal|General>, "
        "\"service_domain\": <short string>, "
        "\"confidence\": <0-1>, "
        "\"evidence\": <short string>}\n\n"
        f"Message: {message}"
    )
    result = llm.generate_json(classifier_system_prompt, prompt)
    control_domain = _normalize_domain(result.get("control_domain"))
    service_domain = _normalize_optional(result.get("service_domain"))
    confidence = result.get("confidence")
    evidence = {
        "message": message,
        "llm_evidence": str(result.get("evidence", "")),
    }

    if control_domain not in ALLOWED:
        control_domain = None

    return DomainDecision(
        control_domain=control_domain,
        service_domain=service_domain,
        confidence=float(confidence) if isinstance(confidence, (int, float)) else 0.0,
        source="llm",
        evidence=evidence,
    )


def _normalize_domain(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    lower = value.strip().lower()
    if lower in {"consulting", "strategy"}:
        return "Consulting"
    if lower in {"ai/tech", "ai", "tech", "ai tech", "ai-tech"}:
        return "AI/Tech"
    if lower == "hr":
        return "HR"
    if lower == "finance":
        return "Finance"
    if lower == "legal":
        return "Legal"
    if lower in {"general", "general business", "business"}:
        return "General"
    if lower == "it":
        return "AI/Tech"
    return None


def _normalize_optional(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None

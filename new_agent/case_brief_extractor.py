from __future__ import annotations

from typing import List, Optional

from .llm_client import LLMClient
from .models import CaseBrief

FIELDS = [
    "contact_name",
    "work_email",
    "problem_summary",
    "desired_outcome",
    "service",
    "urgency",
    "timeline",
    "business_impact",
    "decision_maker",
    "company_name",
    "industry",
    "company_size",
    "role",
    "location",
]


def extract_case_brief(
    message: str,
    llm: Optional[LLMClient] = None,
    system_prompt: str = "",
) -> CaseBrief:
    """Extracts structured fields; does NOT set control_domain."""
    text = message.strip()
    brief = CaseBrief()
    if not text:
        return brief

    if llm:
        prompt = (
            "Extract structured intake fields from the user message. "
            "Return ONLY JSON with keys: "
            "problem_summary, desired_outcome, service, urgency, timeline, "
            "business_impact, decision_maker, company_name, industry, role, location. "
            "Use null if unknown.\n\n"
            f"Message: {text}"
        )
        result = llm.generate_json(system_prompt or "You are a strict JSON extractor.", prompt)
        for field in FIELDS:
            value = result.get(field)
            if value is not None and str(value).strip() != "":
                setattr(brief, field, str(value).strip())
        if brief.problem_summary is None:
            brief.problem_summary = text if len(text) < 200 else text[:200]
        return brief

    brief.problem_summary = text if len(text) < 200 else text[:200]
    return brief


def missing_fields(brief: CaseBrief) -> List[str]:
    missing = []
    for field in FIELDS:
        if getattr(brief, field) in (None, ""):
            missing.append(field)
    return missing

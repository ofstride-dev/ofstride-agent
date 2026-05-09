from __future__ import annotations

from typing import List, Optional

from .llm_client import LLMClient
from .models import CaseBrief

FIELDS = [
    "contact_name",
    # work_email omitted — widget collects phone instead; not required for routing
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
    previous_brief: Optional[CaseBrief] = None,
) -> CaseBrief:
    """Extracts structured fields; does NOT set control_domain. Merges with previous state."""
    text = message.strip()
    
    # Start with previous brief to preserve already-extracted fields
    if previous_brief:
        brief = CaseBrief(
            problem_summary=previous_brief.problem_summary,
            desired_outcome=previous_brief.desired_outcome,
            service=previous_brief.service,
            urgency=previous_brief.urgency,
            timeline=previous_brief.timeline,
            business_impact=previous_brief.business_impact,
            decision_maker=previous_brief.decision_maker,
            contact_name=previous_brief.contact_name,
            work_email=previous_brief.work_email,
            company_name=previous_brief.company_name,
            industry=previous_brief.industry,
            company_size=previous_brief.company_size,
            role=previous_brief.role,
            location=previous_brief.location,
        )
    else:
        brief = CaseBrief()
    
    if not text:
        return brief

    if llm:
        prompt = (
            "Extract structured intake fields from the user message. "
            "Return ONLY valid JSON with these keys (use null for unknown): "
            "contact_name, work_email, problem_summary, desired_outcome, service, urgency, timeline, "
            "business_impact, decision_maker, company_name, industry, company_size, role, location.\n\n"
            f"Message: {text}"
        )
        result = llm.generate_json(system_prompt or "You are a strict JSON extractor. Return ONLY valid JSON.", prompt)
        # Update brief with newly extracted values, but preserve existing ones if not found
        for field in FIELDS:
            value = result.get(field)
            if value is not None and str(value).strip() != "":
                setattr(brief, field, str(value).strip())
        
        # If still no problem_summary, use the message text
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
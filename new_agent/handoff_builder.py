from __future__ import annotations

import json
from typing import Dict

from .llm_client import LLMClient
from .models import HandoffPackage, IntakeState
from .tool_recommender import recommend_tools


INTENT_BUCKETS = [
    "Consulting / strategy",
    "AI / tech help",
    "HR / people",
    "Finance / compliance",
    "Legal-ish",
    "General business",
]


def build_handoff(
    message: str,
    state: IntakeState,
    llm: LLMClient,
) -> HandoffPackage:
    # Build context dict separately — nested dicts inside f-strings
    # are only valid in Python 3.12+. Azure App Service runs 3.11.
    context = {
        "message": message,
        "control_domain": state.control_domain,
        "service_domain": state.service_domain,
        "case_brief": state.case_brief.__dict__,
        "missing_fields": state.missing_fields,
        "stage": state.stage.value,
    }

    prompt = (
        "You are preparing a handoff package for a matching agent that selects the best consultant. "
        "Infer a soft intent bucket and summarize the need. Return ONLY JSON with keys: "
        "intent_bucket, summary, requirements (array), constraints (array), risks (array), "
        "timeline, budget, stakeholders (array). Use null or [] if unknown.\n\n"
        f"Intent buckets: {', '.join(INTENT_BUCKETS)}\n\n"
        "Context (JSON):\n"
        + json.dumps(context, ensure_ascii=False)
    )

    result: Dict[str, object] = llm.generate_json("You are a strict JSON generator.", prompt)
    return HandoffPackage(
        intent_bucket=_as_text(result.get("intent_bucket")),
        summary=_as_text(result.get("summary")),
        contact_name=state.case_brief.contact_name,
        work_email=state.case_brief.work_email,
        requirements=_as_list(result.get("requirements")),
        constraints=_as_list(result.get("constraints")),
        risks=_as_list(result.get("risks")),
        timeline=_as_text(result.get("timeline")),
        budget=_as_text(result.get("budget")),
        stakeholders=_as_list(result.get("stakeholders")),
        recommended_tools=recommend_tools(state, llm),
        evidence={"source": "llm"},
    )


def _as_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return []
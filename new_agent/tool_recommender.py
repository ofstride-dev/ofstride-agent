from __future__ import annotations

import json
from typing import List

from .llm_client import LLMClient
from .models import IntakeState
from .tool_registry import get_tool_registry


def recommend_tools(state: IntakeState, llm: LLMClient) -> List[str]:
    tools = get_tool_registry()

    # Build context dict separately — nested dicts inside f-strings
    # are only valid in Python 3.12+. Azure App Service runs 3.11.
    context = {
        "stage": state.stage.value,
        "missing_fields": state.missing_fields,
        "control_domain": state.control_domain,
        "service_domain": state.service_domain,
        "case_brief": state.case_brief.__dict__,
    }

    prompt = (
        "Pick 1-2 next-step tools from the registry based on the context. "
        "Return ONLY JSON: {\"tools\": [<tool_name>, ...]}.\n\n"
        "Registry:\n"
        + json.dumps([tool.__dict__ for tool in tools], ensure_ascii=False)
        + "\n\nContext (JSON):\n"
        + json.dumps(context, ensure_ascii=False)
    )

    result = llm.generate_json("You are a strict JSON generator.", prompt)
    raw = result.get("tools") if isinstance(result, dict) else None
    if isinstance(raw, list):
        return [str(t).strip() for t in raw if str(t).strip()]
    return []
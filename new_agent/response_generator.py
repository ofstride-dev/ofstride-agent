from __future__ import annotations

import json
from typing import Optional

from .llm_client import LLMClient
from .models import IntakeState


def generate_response(
    message: str,
    state: IntakeState,
    llm: LLMClient,
    system_prompt: str,
    knowledge_text: str,
) -> str:
    context = {
        "stage": state.stage.value,
        "control_domain": state.control_domain,
        "service_domain": state.service_domain,
        "missing_fields": state.missing_fields,
        "case_brief": state.case_brief.__dict__,
        "session_summary": state.session_summary,
        "document_summary": state.document_summary,
        "document_entities": state.document_entities,
    }
    knowledge_block = knowledge_text.strip()
    user_prompt_parts = [
        "User message:",
        message,
        "",
        "Context (JSON):",
        json.dumps(context, ensure_ascii=False, indent=2),
        "",
        "Intent buckets (soft, choose one or blend): Consulting / strategy | AI / tech help | HR / people | Finance / compliance | Legal-ish | General business",
    ]
    if knowledge_block:
        user_prompt_parts += [
            "",
            "Company knowledge (use only if relevant):",
            knowledge_block,
        ]
    user_prompt_parts += [
        "",
        "Instructions:",
        "1) Be conversational, helpful, and confident; do not sound procedural.",
        "2) Maintain an internal running summary of what the user is trying to do (do NOT output this summary).",
        "3) If the user asks about Ofstride services, answer from the knowledge context.",
        "4) Use knowledge as suggestions/examples; never override what the user said.",
        "5) Provide actionable help (ideas, options, tradeoffs) based on intent.",
        "6) Follow the Saarthi flow (greeting, lead capture, intent, discovery, qualification, conversion).",
        "7) If lead capture is missing, ask for name and work email before deep intake.",
        "8) Ask 1–2 natural follow-up questions aligned to the current stage.",
        "9) Keep responses concise and professional.",
    ]
    user_prompt = "\n".join(user_prompt_parts)
    return llm.generate_text(system_prompt, user_prompt) or "Could you share a bit more detail?"

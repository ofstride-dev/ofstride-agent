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
    brief = state.case_brief.__dict__

    # Build a clean known-facts block — only fields that are actually filled
    known = {k: v for k, v in brief.items() if v}

    context_parts = [
        f"Stage: {state.stage.value}",
        f"Known about user: {json.dumps(known, ensure_ascii=False)}",
        f"Still unknown: {state.missing_fields}",
    ]
    if state.session_summary:
        context_parts.append(f"Conversation so far: {state.session_summary}")
    if state.document_summary:
        context_parts.append(f"Document context: {state.document_summary}")

    context_block = "\n".join(context_parts)

    knowledge_block = knowledge_text.strip()

    user_prompt_parts = [
        f"User just said: {message}",
        "",
        context_block,
    ]

    if knowledge_block:
        user_prompt_parts += [
            "",
            "Ofstride services reference (use naturally if relevant, don't dump):",
            knowledge_block[:3000],  # Keep prompt lean
        ]

    user_prompt_parts += [
        "",
        "Reply as Saarthi. Be warm and conversational. One question max. "
        "Never re-ask anything already in 'Known about user'. "
        "Never use numbered lists or bold text. "
        "If you know their name, use it occasionally but not every message. "
        "Keep it short — 2-4 sentences is ideal unless they asked something detailed.",
    ]

    user_prompt = "\n".join(user_prompt_parts)
    return llm.generate_text(system_prompt, user_prompt) or "Could you tell me a bit more about what you're looking for?"
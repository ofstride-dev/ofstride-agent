from __future__ import annotations

import json
import re
from typing import Optional

from .llm_client import LLMClient
from .models import IntakeState


# How many turns before we offer a consultant unprompted
ESCALATION_TURN_THRESHOLD = 4


def generate_response(
    message: str,
    state: IntakeState,
    llm: LLMClient,
    system_prompt: str,
    knowledge_text: str,
) -> dict:
    """
    Returns a dict:
    {
      "text": str,
      "buttons": list[str] | None,   # quick-reply labels
      "escalate": bool               # whether to show Talk to Consultant
    }
    """
    brief = state.case_brief.__dict__
    known = {k: v for k, v in brief.items() if v}

    # Estimate turn count from session summary length as a rough proxy
    turn_count = len(state.session_summary.split("\n")) if state.session_summary else 0
    should_escalate = (
        turn_count >= ESCALATION_TURN_THRESHOLD
        or state.stage.value == "READY"
        or _user_wants_consultant(message)
    )

    # Detect if user is asking about services
    asking_services = bool(re.search(
        r"\b(what|which|tell me|show me|list).{0,20}\b(service|offer|do you|help with|provide)\b",
        message, re.I
    ))

    context_parts = [
        f"Stage: {state.stage.value}",
        f"What we know: {json.dumps(known, ensure_ascii=False)}",
        f"Still missing: {state.missing_fields}",
    ]
    if state.session_summary:
        context_parts.append(f"Conversation so far (including last question Saarthi asked): {state.session_summary}")

    context_block = "\n".join(context_parts)
    knowledge_block = knowledge_text.strip()[:3000]

    # Decide what buttons to suggest to the LLM
    button_hint = ""
    if state.stage.value in ("DISCOVERY", "CLASSIFICATION") and turn_count <= 1:
        button_hint = (
            "After your reply suggest exactly 3 quick-reply buttons as a JSON array on the last line "
            "like this — BUTTONS:[\"Tell me about your services\",\"Book a consultant call\",\"I have more details\"]. "
            "Do not explain the buttons."
        )
    elif asking_services:
        button_hint = (
            "After your reply add: BUTTONS:[\"HR & Talent\",\"Finance & Compliance\",\"IT & AI\",\"Legal\"]"
        )
    elif should_escalate:
        button_hint = (
            "After your reply add: BUTTONS:[\"Book a consultant call\",\"Tell me more\"]"
        )

    priority = "Answer their question directly first." if asking_services else "Continue the conversation naturally."

    user_prompt = "\n".join([
        f"User just said: {message}",
        "",
        context_block,
        "",
        "Ofstride services reference (use only if relevant):",
        knowledge_block,
        "",
        f"Instructions: {priority} "
        "Be warm and conversational — like a knowledgeable friend, not a form. "
        "ONE question max per reply, and only if genuinely needed. "
        "Never re-ask anything already in 'What we know'. "
        "Never use numbered lists, bold, or headers. "
        "Check 'Conversation so far' — never repeat a question already asked. "
        "Accept vague answers and move on — don't push for more detail on the same point twice. "
        "Keep replies to 2-4 sentences unless they asked something detailed. "
        f"{button_hint}",
    ])

    raw = llm.generate_text(system_prompt, user_prompt, temperature=0.7) or "Could you tell me a bit more?"

    # Parse out BUTTONS:[...] if present
    text, buttons = _parse_buttons(raw)
    text = text.strip()

    return {
        "text": text,
        "buttons": buttons,
        "escalate": should_escalate,
    }


def _user_wants_consultant(message: str) -> bool:
    return bool(re.search(
        r"\b(talk to|speak with|speak to|connect me|book|schedule|call|consultant|expert|specialist|meet|meeting)\b",
        message, re.I
    ))


def _parse_buttons(raw: str) -> tuple[str, list[str] | None]:
    """Extract BUTTONS:[...] from the end of the LLM reply."""
    match = re.search(r'BUTTONS:\s*(\[.*?\])\s*$', raw, re.S)
    if match:
        text = raw[:match.start()].strip()
        try:
            buttons = json.loads(match.group(1))
            if isinstance(buttons, list) and buttons:
                return text, [str(b) for b in buttons]
        except json.JSONDecodeError:
            pass
    return raw, None
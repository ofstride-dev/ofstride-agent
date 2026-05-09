from __future__ import annotations

from typing import Dict

from .case_brief_extractor import extract_case_brief, missing_fields
from .conflict_detector import detect_conflicts
from .domain_resolver import resolve_domain
from .escalation_decider import decide_escalation
from .handoff_builder import build_handoff
from .knowledge import load_knowledge
from .llm_client import LLMClient
from .memory_summarizer import update_session_summary
from .models import IntakeState
from .question_policy import determine_stage
from .response_guardrails import apply_guardrails
from .response_generator import generate_response
from .matching_criteria import weights_as_dict
from .tool_registry import get_tool_registry


def handle_message(
    message: str,
    previous_state: IntakeState | None = None,
    system_prompt: str = "",
    knowledge_override: str | None = None,
) -> Dict[str, object]:
    state = previous_state or IntakeState()
    llm = LLMClient()

    # Domain resolution
    domain_decision = resolve_domain(message, llm, system_prompt)
    state.control_domain = domain_decision.control_domain
    state.service_domain = domain_decision.service_domain
    state.domain_confidence = domain_decision.confidence

    # Case brief extraction
    state.case_brief = extract_case_brief(
        message,
        llm=llm,
        system_prompt=system_prompt,
        previous_brief=previous_state.case_brief if previous_state else None,
    )

    # Conflict detection
    if previous_state:
        state.conflict = detect_conflicts(previous_state.case_brief, state.case_brief)

    # Stage determination
    state.missing_fields = missing_fields(state.case_brief)
    state.stage = determine_stage(state.missing_fields)
    state.escalation = decide_escalation(
        confidence=state.domain_confidence,
        conflict=state.conflict.has_conflict,
        missing_fields=state.missing_fields,
    )

    # Knowledge-aware response generation — returns {text, buttons, escalate}
    knowledge_text = load_knowledge(knowledge_override)
    response_obj = generate_response(
        message=message,
        state=state,
        llm=llm,
        system_prompt=system_prompt,
        knowledge_text=knowledge_text,
    )

    response_text = apply_guardrails(response_obj.get("text", ""))
    buttons = response_obj.get("buttons")
    escalate = response_obj.get("escalate", False)

    # Build escalation button if needed and not already present
    if escalate:
        consultant_btn = "Talk to a consultant"
        if not buttons:
            buttons = [consultant_btn]
        elif consultant_btn not in buttons:
            buttons = list(buttons) + [consultant_btn]

    # Session summary — now tracks both sides of the conversation
    state.session_summary = update_session_summary(
        message=message,
        previous_summary=previous_state.session_summary if previous_state else None,
        llm=llm,
        saarthi_last_reply=response_text,
    )

    # Handoff package
    state.handoff = build_handoff(message=message, state=state, llm=llm)

    state.debug = {
        "domain_decision": domain_decision.__dict__,
        "conflict": state.conflict.__dict__,
        "escalation": state.escalation.__dict__,
        "missing_fields": state.missing_fields,
        "stage": state.stage.value,
        "handoff": state.handoff.__dict__,
        "matching_weights": weights_as_dict(),
        "tools": [tool.__dict__ for tool in get_tool_registry()],
        "session_summary": state.session_summary,
        "buttons": buttons,
    }

    return {
        "text": response_text,
        "buttons": buttons,
        "escalate": escalate,
        "debug": state.debug,
        "handoff": state.handoff.__dict__,
        "session_summary": state.session_summary,
        "matching_weights": weights_as_dict(),
        "state": state,
    }
from __future__ import annotations

from typing import List

from .models import EscalationDecision


def decide_escalation(confidence: float, conflict: bool, missing_fields: List[str]) -> EscalationDecision:
    reasons: List[str] = []
    if confidence < 0.4:
        reasons.append("low_confidence")
    if conflict:
        reasons.append("conflict_detected")
    if len(missing_fields) >= 3:
        reasons.append("too_many_missing_fields")
    return EscalationDecision(escalate=bool(reasons), reasons=reasons)

from __future__ import annotations

from typing import List

from .models import CaseBrief, ConflictReport


def detect_conflicts(previous: CaseBrief, current: CaseBrief) -> ConflictReport:
    reasons: List[str] = []
    if previous.problem_summary and current.problem_summary:
        if previous.problem_summary.strip().lower() != current.problem_summary.strip().lower():
            reasons.append("problem_summary_changed")
    return ConflictReport(has_conflict=bool(reasons), reasons=reasons)

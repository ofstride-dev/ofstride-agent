from __future__ import annotations

from .models import IntakeStage, NextQuestionDecision


def determine_stage(missing_fields: list[str]) -> IntakeStage:
    # work_email is optional — widget collects name/phone instead
    if "contact_name" in missing_fields:
        return IntakeStage.LEAD
    if "problem_summary" in missing_fields:
        return IntakeStage.DISCOVERY
    if "service" in missing_fields:
        return IntakeStage.CLASSIFICATION
    if "urgency" in missing_fields:
        return IntakeStage.QUALIFICATION
    if any(f in missing_fields for f in ["company_name", "industry", "role", "location"]):
        return IntakeStage.IDENTITY
    return IntakeStage.READY


def decide_next_question(missing_fields: list[str], stage: IntakeStage) -> NextQuestionDecision:
    if not missing_fields:
        return NextQuestionDecision("Is there anything else you want to add?", ["no_missing_fields"])
    field = missing_fields[0]
    questions = {
        "contact_name": "To personalize this, may I have your name?",
        "work_email": "What’s your work email?",
        "problem_summary": "What’s the main challenge you want help with?",
        "service": "Which specific service are you looking for?",
        "urgency": "What timeline are you aiming for?",
        "company_name": "What’s your company name?",
        "industry": "Which industry are you in?",
        "company_size": "Roughly how large is your company (employees or revenue)?",
        "role": "What’s your role?",
        "location": "Where are you located?",
    }
    return NextQuestionDecision(questions.get(field, "Could you share a bit more detail?"), [f"stage:{stage.value}", f"missing:{field}"])
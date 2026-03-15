from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


@dataclass
class DomainDecision:
    control_domain: Optional[str]
    service_domain: Optional[str]
    confidence: float
    source: str
    evidence: Dict[str, str] = field(default_factory=dict)


@dataclass
class CaseBrief:
    problem_summary: Optional[str] = None
    desired_outcome: Optional[str] = None
    service: Optional[str] = None
    urgency: Optional[str] = None
    timeline: Optional[str] = None
    business_impact: Optional[str] = None
    decision_maker: Optional[str] = None
    contact_name: Optional[str] = None
    work_email: Optional[str] = None
    company_name: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    role: Optional[str] = None
    location: Optional[str] = None


@dataclass
class ConflictReport:
    has_conflict: bool
    reasons: List[str] = field(default_factory=list)


@dataclass
class EscalationDecision:
    escalate: bool
    reasons: List[str] = field(default_factory=list)


@dataclass
class NextQuestionDecision:
    question: str
    reasons: List[str] = field(default_factory=list)


@dataclass
class HandoffPackage:
    intent_bucket: Optional[str] = None
    summary: Optional[str] = None
    contact_name: Optional[str] = None
    work_email: Optional[str] = None
    requirements: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    timeline: Optional[str] = None
    budget: Optional[str] = None
    stakeholders: List[str] = field(default_factory=list)
    recommended_tools: List[str] = field(default_factory=list)
    evidence: Dict[str, str] = field(default_factory=dict)


class IntakeStage(str, Enum):
    LEAD = "LEAD"
    DISCOVERY = "DISCOVERY"
    CLASSIFICATION = "CLASSIFICATION"
    QUALIFICATION = "QUALIFICATION"
    IDENTITY = "IDENTITY"
    READY = "READY"


@dataclass
class IntakeState:
    control_domain: Optional[str] = None
    service_domain: Optional[str] = None
    domain_confidence: float = 0.0
    case_brief: CaseBrief = field(default_factory=CaseBrief)
    conflict: ConflictReport = field(default_factory=lambda: ConflictReport(False))
    escalation: EscalationDecision = field(default_factory=lambda: EscalationDecision(False))
    missing_fields: List[str] = field(default_factory=list)
    stage: IntakeStage = IntakeStage.DISCOVERY
    debug: Dict[str, object] = field(default_factory=dict)
    handoff: HandoffPackage = field(default_factory=HandoffPackage)
    session_summary: Optional[str] = None
    document_summary: Optional[str] = None
    document_entities: Dict[str, List[str]] = field(default_factory=dict)

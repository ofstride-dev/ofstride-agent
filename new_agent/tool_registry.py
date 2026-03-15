from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class Tool:
    name: str
    description: str
    when_to_use: str


def get_tool_registry() -> List[Tool]:
    return [
        Tool(
            name="calendar_booking",
            description="Schedule a discovery or scoping call with a consultant.",
            when_to_use="User wants to proceed or needs a live consultation.",
        ),
        Tool(
            name="crm_log",
            description="Log the lead, summary, and key details in CRM.",
            when_to_use="After a meaningful intake exchange.",
        ),
        Tool(
            name="proposal_draft",
            description="Draft a project proposal or scope outline.",
            when_to_use="Requirements and scope are reasonably clear.",
        ),
        Tool(
            name="doc_intake",
            description="Collect documents (requirements, contracts, briefs).",
            when_to_use="User references existing docs or asks to upload files.",
        ),
        Tool(
            name="matching_agent_handoff",
            description="Send a structured brief to matching agent.",
            when_to_use="When enough context exists to route to a consultant.",
        ),
    ]

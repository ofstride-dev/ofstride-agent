from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .chart_tools import overview, tool_catalog
from .llm_client import LLMClient


@dataclass
class ChartAgentResponse:
    text: str
    tools_used: List[str]
    data: Dict[str, object]


def _build_fallback_summary(data: Dict[str, object]) -> str:
    total_leads = data.get("totalLeads", 0)
    total_matches = data.get("totalMatches", 0)
    match_rate = data.get("matchRate", 0.0)
    top_locations = data.get("topLocations", [])

    location_text = ""
    if isinstance(top_locations, list) and top_locations:
        parts = [f"{item.get('location')} ({item.get('count')})" for item in top_locations]
        location_text = " Top locations: " + ", ".join(parts) + "."

    return (
        f"We have {total_leads} total leads and {total_matches} matched notifications, "
        f"with a {match_rate}% match rate.{location_text}"
    )


class ChartAgent:
    def __init__(self) -> None:
        self.tools = tool_catalog()
        try:
            self.llm = LLMClient()
        except Exception:
            self.llm = None

    def answer(self, question: str) -> ChartAgentResponse:
        data = overview()
        tools_used = ["get_overview"]

        if not self.llm:
            return ChartAgentResponse(
                text=_build_fallback_summary(data),
                tools_used=tools_used,
                data=data,
            )

        system_prompt = (
            "You are an analytics assistant for a consulting website. "
            "Use only the provided data to answer. Do not invent numbers. "
            "If the data is insufficient, say so and suggest what metric is needed."
        )

        user_prompt = (
            f"User question: {question}\n\n"
            f"Available tools: {self.tools}\n\n"
            f"Tool output (get_overview): {data}\n\n"
            "Provide a concise, actionable answer grounded in the data."
        )

        try:
            text = self.llm.generate_text(system_prompt, user_prompt)
        except Exception:
            text = _build_fallback_summary(data)

        return ChartAgentResponse(text=text, tools_used=tools_used, data=data)

from __future__ import annotations

import json
from typing import Dict, List

from .llm_client import LLMClient


def summarize_document(text: str, llm: LLMClient) -> Dict[str, object]:
    prompt = (
        "Summarize the document in 3-5 bullet points and extract key entities. "
        "Return ONLY JSON with keys: summary (string), entities (object with arrays). "
        "Entities keys: companies, people, products, technologies, dates, budgets, locations. "
        "Use empty arrays if none.\n\n"
        f"Document:\n{text[:12000]}"
    )
    result = llm.generate_json("You are a strict JSON generator.", prompt)
    summary = str(result.get("summary") or "").strip()
    entities = result.get("entities") if isinstance(result.get("entities"), dict) else {}
    normalized = {
        "companies": _as_list(entities.get("companies")) if entities else [],
        "people": _as_list(entities.get("people")) if entities else [],
        "products": _as_list(entities.get("products")) if entities else [],
        "technologies": _as_list(entities.get("technologies")) if entities else [],
        "dates": _as_list(entities.get("dates")) if entities else [],
        "budgets": _as_list(entities.get("budgets")) if entities else [],
        "locations": _as_list(entities.get("locations")) if entities else [],
    }
    return {"summary": summary, "entities": normalized}


def _as_list(value: object) -> List[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if value is None:
        return []
    return [str(value).strip()]

from __future__ import annotations

from .llm_client import LLMClient


def update_session_summary(
    message: str,
    previous_summary: str | None,
    llm: LLMClient,
) -> str:
    prompt = (
        "Update the running summary of the user's request in 1-2 sentences. "
        "Keep it concise and factual. If no prior summary, create one. "
        "Return ONLY the summary text.\n\n"
        f"Previous summary: {previous_summary or 'None'}\n"
        f"New message: {message}"
    )
    summary = llm.generate_text("You are a concise summarizer.", prompt)
    return summary.strip() or (previous_summary or "")

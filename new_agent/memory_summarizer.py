from __future__ import annotations

from .llm_client import LLMClient


def update_session_summary(
    message: str,
    previous_summary: str | None,
    llm: LLMClient,
    saarthi_last_reply: str | None = None,
) -> str:
    """
    Maintains a running summary of BOTH sides of the conversation.
    Tracking what Saarthi last asked is critical — without it the LLM
    re-asks the same question on the next turn.
    """
    last_exchange = ""
    if saarthi_last_reply:
        last_exchange = f"Saarthi last said: {saarthi_last_reply}\nUser replied: {message}"
    else:
        last_exchange = f"User said: {message}"

    prompt = (
        "You maintain a running factual summary of a business consulting intake conversation. "
        "Update the summary to include the latest exchange. "
        "Crucially: record what question Saarthi most recently asked so it is never repeated. "
        "Keep it to 3 sentences max. Return ONLY the updated summary text.\n\n"
        f"Previous summary: {previous_summary or 'None'}\n"
        f"Latest exchange:\n{last_exchange}"
    )
    summary = llm.generate_text("You are a concise conversation summarizer.", prompt)
    return summary.strip() or (previous_summary or "")
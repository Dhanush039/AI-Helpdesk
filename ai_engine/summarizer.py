"""ai_engine.summarizer - AI summary of a ticket + its comment thread."""

from . import prompts
from .client import chat_completion, AIResponse


def summarize_ticket(title: str, description: str, comments: list[str]) -> AIResponse:
    """Summarize a ticket and its conversation history for a support agent."""
    thread = "\n".join(f"- {c}" for c in comments) if comments else "(no comments yet)"
    user_prompt = (
        f"Ticket title: {title}\n\n"
        f"Ticket description:\n{description}\n\n"
        f"Comment history:\n{thread}"
    )
    return chat_completion(prompts.SUMMARY_SYSTEM_PROMPT, user_prompt, json_mode=False)

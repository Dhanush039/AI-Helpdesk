"""ai_engine.diagnosis - AI root-cause diagnosis and troubleshooting steps."""

from . import prompts
from .client import chat_completion, AIResponse


def diagnose_ticket(title: str, description: str) -> AIResponse:
    """Ask the AI for a problem summary, possible causes, and troubleshooting steps."""
    user_prompt = f"Ticket title: {title}\n\nTicket description:\n{description}"
    response = chat_completion(
        prompts.DIAGNOSIS_SYSTEM_PROMPT, user_prompt, json_mode=True
    )
    if not response.ok:
        return response

    data = response.data or {}
    data.setdefault("summary", "")
    data.setdefault("possible_causes", [])
    data.setdefault("troubleshooting_steps", [])
    data.setdefault("recommended_resolution", "")
    response.data = data
    return response

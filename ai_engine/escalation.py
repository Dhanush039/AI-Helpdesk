"""ai_engine.escalation - AI recommendation on whether/where to escalate a ticket."""

from . import prompts
from .client import chat_completion, AIResponse

VALID_TEAMS = [
    "L1 Support", "Network L2", "Hardware Team",
    "Security Team", "Application Team", "IAM Team",
]


def recommend_escalation(title: str, description: str) -> AIResponse:
    """Ask the AI whether a ticket should be escalated, and to which team."""
    user_prompt = f"Ticket title: {title}\n\nTicket description:\n{description}"
    response = chat_completion(
        prompts.ESCALATION_SYSTEM_PROMPT, user_prompt, json_mode=True
    )
    if not response.ok:
        return response

    data = response.data or {}
    if data.get("recommended_team") not in VALID_TEAMS:
        data["recommended_team"] = "L1 Support"
    data.setdefault("escalate", False)
    data.setdefault("reason", "")
    response.data = data
    return response

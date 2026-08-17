"""ai_engine.classifier - AI ticket classification (category / priority / issue type)."""

from . import prompts
from .client import chat_completion, AIResponse

VALID_CATEGORIES = [
    "Network", "Hardware", "Software", "Email",
    "Access / IAM", "Security", "Printer", "VPN", "Other",
]
VALID_PRIORITIES = ["Low", "Medium", "High", "Critical"]


def classify_ticket(title: str, description: str) -> AIResponse:
    """Ask the AI to classify a ticket into category / priority / issue type."""
    user_prompt = f"Ticket title: {title}\n\nTicket description:\n{description}"
    response = chat_completion(
        prompts.CLASSIFIER_SYSTEM_PROMPT, user_prompt, json_mode=True
    )
    if not response.ok:
        return response

    data = response.data or {}
    category = data.get("category") if data.get("category") in VALID_CATEGORIES else "Other"
    priority = data.get("priority") if data.get("priority") in VALID_PRIORITIES else "Medium"
    data["category"] = category
    data["priority"] = priority
    data.setdefault("issue_type", "Unspecified")
    response.data = data
    return response

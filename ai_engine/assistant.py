"""ai_engine.assistant - general-purpose AI Support Assistant Q&A for L1 agents."""

from . import prompts
from .client import chat_completion, AIResponse


def ask_assistant(question: str) -> AIResponse:
    """Answer a free-form IT support question with practical, structured guidance."""
    return chat_completion(prompts.ASSISTANT_SYSTEM_PROMPT, question, json_mode=False)

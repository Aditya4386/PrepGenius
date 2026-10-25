"""
llm.py — Groq LLM client integration using LangChain.

Provides configured ChatGroq instances using settings.
"""

import logging
from langchain_groq import ChatGroq
from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Raised when the Groq API call fails in a non-recoverable way."""
    pass


def get_llm(temperature: float = None) -> ChatGroq:
    """
    Return a LangChain ChatGroq instance.
    Uses the model and API key defined in application settings.
    """
    temp = temperature if temperature is not None else settings.GROQ_TEMPERATURE
    kwargs = {
        "model": settings.GROQ_MODEL,
        "api_key": settings.GROQ_API_KEY,
        "temperature": temp,
        "max_tokens": 4000,
    }
    if "gpt-oss" in settings.GROQ_MODEL:
        kwargs["reasoning_format"] = "hidden"
    return ChatGroq(**kwargs)
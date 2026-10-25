"""
llm.py — Centralized LLM provider with NVIDIA Nemotron and Groq support.

Provides task-based model routing, structured output parsing, and
compatibility with LangChain/LangGraph implementations.

Retry behavior is centralized using LangChain's Runnable.with_retry().
Built-in provider retries are disabled to avoid nested retries.
"""

import json
import logging
from enum import Enum
from typing import Any, Dict, Optional, Type, TypeVar

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    NVIDIA = "nvidia"
    GROQ = "groq"


class LLMTask(str, Enum):
    """Task identifiers for model routing."""

    # Resume Analyzer
    RESUME_SECTION_ANALYSIS = "resume_section_analysis"
    RESUME_JOB_MATCHING = "resume_job_matching"
    RESUME_RECOMMENDATIONS = "resume_recommendations"

    # Resume Builder
    RESUME_JOB_DESCRIPTION_PARSING = "resume_job_description_parsing"
    RESUME_QUESTION_GENERATION = "resume_question_generation"
    RESUME_ANSWER_COMPLETENESS = "resume_answer_completeness"
    RESUME_SECTION_DRAFTING = "resume_section_drafting"
    RESUME_FINAL_ASSEMBLY = "resume_final_assembly"

    # Roadmap Generator
    ROADMAP_GAP_ANALYSIS = "roadmap_gap_analysis"
    ROADMAP_PLAN_GENERATION = "roadmap_plan_generation"
    ROADMAP_PLAN_REPAIR = "roadmap_plan_repair"
    ROADMAP_ADAPTATION = "roadmap_adaptation"


class LLMError(Exception):
    """Raised when an LLM API call fails in a non-recoverable way."""
    def __init__(self, message: str, provider: Optional[str] = None, model: Optional[str] = None):
        self.provider = provider
        self.model = model
        super().__init__(message)


class LLMConfigError(Exception):
    """Raised when LLM configuration is invalid."""
    pass


# Task-to-model routing configuration
TASK_MODEL_MAP: Dict[LLMTask, Dict[str, Any]] = {
    # Resume Analyzer
    LLMTask.RESUME_SECTION_ANALYSIS: {
        "provider": LLMProvider.GROQ,
        "model": "openai/gpt-oss-20b",
        "temperature": 0.1,
        "max_tokens": 4000,
    },
    LLMTask.RESUME_JOB_MATCHING: {
        "provider": LLMProvider.NVIDIA,
        "model": "nvidia/nemotron-3-ultra-550b-a55b",
        "temperature": 0.1,
        "max_tokens": 2000,
    },
    LLMTask.RESUME_RECOMMENDATIONS: {
        "provider": LLMProvider.NVIDIA,
        "model": "nvidia/nemotron-3-ultra-550b-a55b",
        "temperature": 0.2,
        "max_tokens": 3000,
    },

    # Resume Builder
    LLMTask.RESUME_JOB_DESCRIPTION_PARSING: {
        "provider": LLMProvider.NVIDIA,
        "model": "nvidia/nemotron-3-ultra-550b-a55b",
        "temperature": 0.1,
        "max_tokens": 2000,
    },
    LLMTask.RESUME_QUESTION_GENERATION: {
        "provider": LLMProvider.NVIDIA,
        "model": "nvidia/nemotron-3-ultra-550b-a55b",
        "temperature": 0.3,
        "max_tokens": 1000,
    },
    LLMTask.RESUME_ANSWER_COMPLETENESS: {
        "provider": LLMProvider.NVIDIA,
        "model": "nvidia/nemotron-3-ultra-550b-a55b",
        "temperature": 0.1,
        "max_tokens": 1000,
    },
    LLMTask.RESUME_SECTION_DRAFTING: {
        "provider": LLMProvider.GROQ,
        "model": "openai/gpt-oss-20b",
        "temperature": 0.2,
        "max_tokens": 3000,
    },
    LLMTask.RESUME_FINAL_ASSEMBLY: {
        "provider": LLMProvider.GROQ,
        "model": "openai/gpt-oss-20b",
        "temperature": 0.1,
        "max_tokens": 4000,
    },

    # Roadmap Generator
    LLMTask.ROADMAP_GAP_ANALYSIS: {
        "provider": LLMProvider.NVIDIA,
        "model": "nvidia/nemotron-3-ultra-550b-a55b",
        "temperature": 0.1,
        "max_tokens": 2000,
    },
    LLMTask.ROADMAP_PLAN_GENERATION: {
        "provider": LLMProvider.GROQ,
        "model": "openai/gpt-oss-20b",
        "temperature": 0.1,
        "max_tokens": 8000,
    },
    LLMTask.ROADMAP_PLAN_REPAIR: {
        "provider": LLMProvider.GROQ,
        "model": "openai/gpt-oss-20b",
        "temperature": 0.1,
        "max_tokens": 6000,
    },
    LLMTask.ROADMAP_ADAPTATION: {
        "provider": LLMProvider.NVIDIA,
        "model": "nvidia/nemotron-3-ultra-550b-a55b",
        "temperature": 0.2,
        "max_tokens": 2000,
    },
}


def _should_retry_exception(exc: BaseException) -> bool:
    """Determine if an exception should trigger a retry."""
    import httpx
    import groq

    # Retry on rate limits (429)
    if isinstance(exc, httpx.HTTPStatusError):
        if exc.response.status_code == 429:
            return True
        # Retry on 5xx server errors
        if 500 <= exc.response.status_code < 600:
            return True
        # Don't retry 4xx client errors (except 429)
        return False

    # Retry on timeouts and connection errors
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError)):
        return True

    # Retry on Groq-specific transient errors
    if isinstance(exc, (groq.RateLimitError, groq.APITimeoutError, groq.InternalServerError, groq.APIConnectionError)):
        return True

    # Don't retry authentication errors, invalid requests, etc.
    if isinstance(exc, (groq.AuthenticationError, groq.BadRequestError, groq.NotFoundError, groq.PermissionDeniedError, groq.UnprocessableEntityError)):
        return False

    if isinstance(exc, (httpx.HTTPStatusError,)):
        # Already handled 429 and 5xx above
        return False

    # Don't retry other exceptions by default
    return False


def _create_retry_config():
    """Create LangChain retry configuration."""
    from langchain_core.runnables.retry import ExponentialJitterParams

    return {
        "retry_if_exception_type": (
            # HTTP and network errors
            ImportError,  # placeholder, will be replaced with actual exception types
        ),
        "wait_exponential_jitter": True,
        "exponential_jitter_params": {
            "initial": 1.0,
            "maximum": 60.0,
            "multiplier": 2.0,
            "jitter": 0.2,
        },
        "stop_after_attempt": 3,
    }


def _make_runnable_with_retry(runnable: Runnable) -> Runnable:
    """Wrap a runnable with centralized retry behavior."""
    import httpx
    import groq
    from langchain_core.runnables.retry import ExponentialJitterParams, RunnableRetry

    class RunnableRetryWithStructuredOutput(RunnableRetry):
        """RunnableRetry subclass that delegates with_structured_output to the bound runnable."""
        def with_structured_output(self, schema: Type[T], **kwargs: Any) -> "StructuredOutputWrapper[T]":
            return self.bound.with_structured_output(schema, **kwargs)

    wrapped = runnable.with_retry(
        retry_if_exception_type=(
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.ReadError,
            httpx.HTTPStatusError,
            groq.RateLimitError,
            groq.APITimeoutError,
            groq.InternalServerError,
            groq.APIConnectionError,
        ),
        wait_exponential_jitter=True,
        exponential_jitter_params=ExponentialJitterParams(
            initial=1.0,
            maximum=60.0,
            multiplier=2.0,
            jitter=0.2,
        ),
        stop_after_attempt=3,
    )

    # Replace with subclass that delegates with_structured_output
    return RunnableRetryWithStructuredOutput(
        bound=wrapped.bound,
        retry_exception_types=wrapped.retry_exception_types,
        wait_exponential_jitter=wrapped.wait_exponential_jitter,
        exponential_jitter_params=wrapped.exponential_jitter_params,
        max_attempt_number=wrapped.max_attempt_number,
        kwargs=wrapped.kwargs,
    )


class NVIDIAChatModel(BaseChatModel):
    """LangChain-compatible wrapper for NVIDIA Nemotron API.

    Built-in retries are DISABLED. Retry behavior is applied centrally
    via LangChain's Runnable.with_retry() in get_llm_for_task().
    """

    model_name: str = "nvidia/nemotron-3-ultra-550b-a55b"
    api_key: str = ""
    base_url: str = "https://integrate.api.nvidia.com/v1"
    temperature: float = 0.2
    max_tokens: int = 4000
    timeout: int = 180
    # Built-in retries DISABLED - handled by LangChain's with_retry()
    max_retries: int = 0

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.api_key:
            raise LLMConfigError("NVIDIA_API_KEY is required but not configured")

    @property
    def _llm_type(self) -> str:
        return "nvidia-nemotron"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate a chat completion without built-in retries."""
        from langchain_core.messages import AIMessage

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": m.type if m.type in ("system", "user", "assistant") else "user", "content": m.content}
                for m in messages
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if stop:
            payload["stop"] = stop

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        import httpx
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )

        # Handle 429 with Retry-After header
        if response.status_code == 429:
            retry_after = response.headers.get("retry-after")
            raise httpx.HTTPStatusError(
                "Rate limited",
                request=response.request,
                response=response,
            )

        if response.status_code == 401:
            raise LLMError("NVIDIA API authentication failed. Check NVIDIA_API_KEY.", provider="nvidia", model=self.model_name)

        if response.status_code == 404:
            raise LLMError(f"Model {self.model_name} not found or not accessible.", provider="nvidia", model=self.model_name)

        response.raise_for_status()
        data = response.json()

        content = data["choices"][0]["message"].get("content", "")
        # Handle reasoning field if present (some NVIDIA models include it)
        reasoning = data["choices"][0]["message"].get("reasoning")
        if reasoning:
            logger.debug(f"Model reasoning (hidden): {reasoning[:200]}")

        message = AIMessage(content=content)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Async generate (falls back to sync for now)."""
        return self._generate(messages, stop, run_manager, **kwargs)

    def with_structured_output(self, schema: Type[T], **kwargs: Any) -> "StructuredOutputWrapper[T]":
        """Return a wrapper that parses structured output."""
        return StructuredOutputWrapper(llm=self, schema=schema)


class StructuredOutputWrapper:
    """Wrapper that invokes the LLM and parses structured JSON output."""

    def __init__(self, llm: NVIDIAChatModel, schema: Type[T]):
        self.llm = llm
        self.schema = schema

    def invoke(self, prompt: str, **kwargs: Any) -> T:
        """Invoke the LLM and parse the response as the schema type."""
        from langchain_core.messages import HumanMessage

        # Add JSON formatting instruction to prompt
        json_instruction = f"\n\nReturn ONLY valid JSON matching this schema:\n{self.schema.model_json_schema()}"
        full_prompt = prompt + json_instruction

        response = self.llm.invoke([HumanMessage(content=full_prompt)], **kwargs)
        content = response.content

        # Extract JSON from markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        content = content.strip()

        try:
            parsed = json.loads(content)
            return self.schema.model_validate(parsed)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM response: {e}")
            logger.debug(f"Raw content: {content[:500]}")
            raise LLMError(f"LLM returned invalid JSON: {e}", provider="nvidia", model=self.llm.model_name) from e


def get_llm_for_task(task: LLMTask, temperature: Optional[float] = None) -> BaseChatModel:
    """
    Get an LLM instance configured for a specific task, wrapped with centralized retry behavior.

    Args:
        task: The task identifier for model routing.
        temperature: Optional temperature override.

    Returns:
        A LangChain-compatible chat model instance with centralized retry behavior.
    """
    config = TASK_MODEL_MAP.get(task)
    if not config:
        raise LLMConfigError(f"No model configuration for task: {task}")

    provider = config.get("provider", LLMProvider.NVIDIA)
    model = config.get("model", settings.NVIDIA_DEFAULT_MODEL)
    temp = temperature if temperature is not None else config.get("temperature", 0.2)
    max_tokens = config.get("max_tokens", 4000)

    if provider == LLMProvider.NVIDIA:
        base_model = NVIDIAChatModel(
            model_name=model,
            api_key=settings.NVIDIA_API_KEY,
            base_url=settings.NVIDIA_BASE_URL,
            temperature=temp,
            max_tokens=max_tokens,
            max_retries=0,  # Disable built-in retries
        )
    elif provider == LLMProvider.GROQ:
        from langchain_groq import ChatGroq
        base_model = ChatGroq(
            model=model,
            api_key=settings.GROQ_API_KEY,
            temperature=temp,
            max_tokens=max_tokens,
            max_retries=0,  # Disable built-in retries
        )
    else:
        raise LLMConfigError(f"Unknown provider: {provider}")

    # Apply centralized retry behavior via LangChain's with_retry()
    return _make_runnable_with_retry(base_model)


def get_llm(temperature: Optional[float] = None) -> BaseChatModel:
    """
    Get the default LLM instance (backward compatibility).

    Uses the configured default provider and model from settings.
    """
    provider = getattr(settings, "LLM_PROVIDER", "nvidia")

    if provider == "nvidia":
        base_model = NVIDIAChatModel(
            model_name=settings.NVIDIA_DEFAULT_MODEL,
            api_key=settings.NVIDIA_API_KEY,
            base_url=settings.NVIDIA_BASE_URL,
            temperature=temperature if temperature is not None else 0.2,
            max_tokens=4000,
            max_retries=0,  # Disable built-in retries
        )
    elif provider == "groq":
        from langchain_groq import ChatGroq
        base_model = ChatGroq(
            model=settings.GROQ_MODEL,
            api_key=settings.GROQ_API_KEY,
            temperature=temperature if temperature is not None else settings.GROQ_TEMPERATURE,
            max_tokens=4000,
            max_retries=0,  # Disable built-in retries
        )
    else:
        raise LLMConfigError(f"Unknown LLM_PROVIDER: {provider}")

    # Apply centralized retry behavior
    return _make_runnable_with_retry(base_model)
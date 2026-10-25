"""
test_retry_behavior.py — Unit tests for centralized retry behavior.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable

from app.shared.llm import (
    get_llm_for_task,
    LLMTask,
    NVIDIAChatModel,
    _make_runnable_with_retry,
    _should_retry_exception,
)
from app.shared.llm import LLMError, LLMConfigError


class TestRetryBehavior:
    """Tests for centralized retry behavior."""

    def test_should_retry_on_rate_limit(self):
        """Test that 429 rate limit errors are retried."""
        import httpx
        request = httpx.Request("POST", "https://api.nvidia.com/v1/chat/completions")
        response = httpx.Response(429, request=request, headers={"retry-after": "5"})
        exc = httpx.HTTPStatusError("Rate limited", request=request, response=response)
        assert _should_retry_exception(exc) is True

    def test_should_retry_on_5xx(self):
        """Test that 5xx server errors are retried."""
        import httpx
        request = httpx.Request("POST", "https://api.nvidia.com/v1/chat/completions")
        response = httpx.Response(500, request=request)
        exc = httpx.HTTPStatusError("Internal Server Error", request=request, response=response)
        assert _should_retry_exception(exc) is True

    def test_should_not_retry_on_401(self):
        """Test that authentication errors are not retried."""
        import httpx
        request = httpx.Request("POST", "https://api.nvidia.com/v1/chat/completions")
        response = httpx.Response(401, request=request)
        exc = httpx.HTTPStatusError("Unauthorized", request=request, response=response)
        assert _should_retry_exception(exc) is False

    def test_should_not_retry_on_400(self):
        """Test that bad request errors are not retried."""
        import httpx
        request = httpx.Request("POST", "https://api.nvidia.com/v1/chat/completions")
        response = httpx.Response(400, request=request)
        exc = httpx.HTTPStatusError("Bad Request", request=request, response=response)
        assert _should_retry_exception(exc) is False

    def test_should_retry_on_timeout(self):
        """Test that timeouts are retried."""
        import httpx
        exc = httpx.TimeoutException("Request timed out")
        assert _should_retry_exception(exc) is True

    def test_should_retry_on_connection_error(self):
        """Test that connection errors are retried."""
        import httpx
        exc = httpx.ConnectError("Connection refused")
        assert _should_retry_exception(exc) is True

    def test_should_retry_on_groq_rate_limit(self):
        """Test that Groq rate limit errors are retried."""
        import groq
        mock_response = MagicMock()
        mock_response.status_code = 429
        exc = groq.RateLimitError("Rate limited", response=mock_response, body={"error": "rate limited"})
        assert _should_retry_exception(exc) is True

    def test_should_retry_on_groq_server_error(self):
        """Test that Groq 5xx errors are retried."""
        import groq
        mock_response = MagicMock()
        mock_response.status_code = 500
        exc = groq.InternalServerError("Server error", response=mock_response, body={"error": "server error"})
        assert _should_retry_exception(exc) is True

    def test_should_not_retry_on_groq_auth_error(self):
        """Test that Groq auth errors are not retried."""
        import groq
        mock_response = MagicMock()
        mock_response.status_code = 401
        exc = groq.AuthenticationError("Invalid API key", response=mock_response, body={"error": "auth error"})
        assert _should_retry_exception(exc) is False

    def test_should_not_retry_on_groq_bad_request(self):
        """Test that Groq bad request errors are not retried."""
        import groq
        mock_response = MagicMock()
        mock_response.status_code = 400
        exc = groq.BadRequestError("Invalid request", response=mock_response, body={"error": "bad request"})
        assert _should_retry_exception(exc) is False


class TestNVIDIAChatModelRetry:
    """Tests for NVIDIAChatModel retry behavior."""

    @pytest.fixture
    def nvidia_model(self):
        """Create an NVIDIAChatModel instance for testing."""
        return NVIDIAChatModel(
            model_name="nvidia/nemotron-3-ultra-550b-a55b",
            api_key="test-key",
            base_url="https://integrate.api.nvidia.com/v1",
            temperature=0.2,
            max_tokens=100,
            timeout=10,
            max_retries=0,
        )

    @patch("httpx.Client.post")
    def test_successful_call(self, mock_post, nvidia_model):
        """Test successful API call returns correct response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello world!", "reasoning": None}}]
        }
        mock_post.return_value = mock_response

        response = nvidia_model.invoke([HumanMessage(content="Hello")])
        assert response.content == "Hello world!"
        assert mock_post.call_count == 1

    @patch("httpx.Client.post")
    def test_rate_limit_raises_httpx_error(self, mock_post, nvidia_model):
        """Test that 429 responses raise HTTPStatusError with retry-after."""
        import httpx
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"retry-after": "5"}
        mock_request = MagicMock()
        mock_response.request = mock_request
        mock_post.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            nvidia_model.invoke([HumanMessage(content="Hello")])

        assert exc_info.value.response.status_code == 429

    @patch("httpx.Client.post")
    def test_auth_error_raises_llm_error(self, mock_post, nvidia_model):
        """Test that 401 raises LLMError."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        with pytest.raises(LLMError) as exc_info:
            nvidia_model.invoke([HumanMessage(content="Hello")])

        assert "authentication failed" in str(exc_info.value).lower()

    @patch("httpx.Client.post")
    def test_model_not_found_raises_llm_error(self, mock_post, nvidia_model):
        """Test that 404 raises LLMError."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_post.return_value = mock_response

        with pytest.raises(LLMError) as exc_info:
            nvidia_model.invoke([HumanMessage(content="Hello")])

        assert "not found" in str(exc_info.value).lower()


class TestRunnableRetryWrapper:
    """Tests for the _make_runnable_with_retry wrapper."""

    def test_wrapper_adds_retry_behavior(self):
        """Test that _make_runnable_with_retry wraps the model with retry behavior."""
        from langchain_core.runnables.retry import RunnableRetry

        # Use a real NVIDIA model with retries disabled
        model = NVIDIAChatModel(
            model_name="test",
            api_key="test",
            base_url="https://test.com",
            temperature=0.2,
            max_tokens=100,
            timeout=10,
            max_retries=0,
        )
        
        wrapped = _make_runnable_with_retry(model)

        from langchain_core.runnables.retry import RunnableRetry
        assert isinstance(wrapped, RunnableRetry)

    def test_retry_config_parameters(self):
        """Test that retry configuration has correct parameters."""
        model = NVIDIAChatModel(
            model_name="test",
            api_key="test",
            base_url="https://test.com",
            temperature=0.2,
            max_tokens=100,
            timeout=10,
            max_retries=0,
        )
        
        wrapped = _make_runnable_with_retry(model)

        assert wrapped.max_attempt_number == 3
        assert wrapped.wait_exponential_jitter is True
        assert wrapped.exponential_jitter_params["initial"] == 1.0
        assert wrapped.exponential_jitter_params["jitter"] == 0.2

    def test_retry_exception_types(self):
        """Test that retry is configured for correct exception types."""
        import httpx
        import groq

        model = NVIDIAChatModel(
            model_name="test",
            api_key="test",
            base_url="https://test.com",
            temperature=0.2,
            max_tokens=100,
            timeout=10,
            max_retries=0,
        )
        
        wrapped = _make_runnable_with_retry(model)

        exception_types = wrapped.retry_exception_types
        assert httpx.TimeoutException in exception_types
        assert httpx.ConnectError in exception_types
        assert httpx.ReadError in exception_types
        assert httpx.HTTPStatusError in exception_types
        assert groq.RateLimitError in exception_types
        assert groq.APITimeoutError in exception_types
        assert groq.InternalServerError in exception_types
        assert groq.APIConnectionError in exception_types


class TestGetLLMForTask:
    """Tests for get_llm_for_task with retry wrapper."""

    def test_get_llm_for_task_returns_wrapped_model(self):
        """Test that get_llm_for_task returns a model with retry wrapper."""
        from langchain_core.runnables.retry import RunnableRetry

        llm = get_llm_for_task(LLMTask.RESUME_SECTION_ANALYSIS)

        # Should be wrapped with retry
        from langchain_core.runnables.retry import RunnableRetry
        assert isinstance(llm, RunnableRetry)

    def test_get_llm_for_task_groq_returns_wrapped_model(self):
        """Test that Groq models are also wrapped with retry."""
        from langchain_core.runnables.retry import RunnableRetry

        llm = get_llm_for_task(LLMTask.RESUME_SECTION_ANALYSIS)

        from langchain_core.runnables.retry import RunnableRetry
        assert isinstance(llm, RunnableRetry)


class TestRetryIntegration:
    """Integration tests for retry behavior with mocked failures."""

    @patch("httpx.Client.post")
    def test_retry_on_5xx_then_success(self, mock_post):
        """Test that 5xx errors are retried and eventually succeed."""
        import httpx

        # First call returns 500, second succeeds
        mock_response_500 = MagicMock()
        mock_response_500.status_code = 500
        mock_response_500.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Internal Server Error", 
            request=MagicMock(), 
            response=MagicMock(status_code=500)
        )

        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {
            "choices": [{"message": {"content": "Success after retry!", "reasoning": None}}]
        }

        mock_post.side_effect = [mock_response_500, mock_response_200]

        from app.shared.llm import NVIDIAChatModel
        model = NVIDIAChatModel(
            model_name="test",
            api_key="test",
            base_url="https://test.com",
            temperature=0.2,
            max_tokens=100,
            timeout=10,
            max_retries=0,
        )

        # The model itself doesn't retry, but the wrapper should
        from app.shared.llm import _make_runnable_with_retry
        wrapped = _make_runnable_with_retry(model)

        response = wrapped.invoke([HumanMessage(content="Test")])
        assert response.content == "Success after retry!"
        assert mock_post.call_count == 2

    @patch("httpx.Client.post")
    def test_retry_exhausted_raises_error(self, mock_post):
        """Test that after max retries, error is raised."""
        import httpx

        # All calls return 500
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Internal Server Error", 
            request=MagicMock(), 
            response=MagicMock(status_code=500)
        )
        mock_post.return_value = mock_response

        from app.shared.llm import NVIDIAChatModel
        model = NVIDIAChatModel(
            model_name="test",
            api_key="test",
            base_url="https://test.com",
            temperature=0.2,
            max_tokens=100,
            timeout=10,
            max_retries=0,
        )

        from app.shared.llm import _make_runnable_with_retry
        wrapped = _make_runnable_with_retry(model)

        with pytest.raises(httpx.HTTPStatusError):
            wrapped.invoke([HumanMessage(content="Test")])

        # Should have been called 3 times (max_attempt_number=3 means 3 total attempts)
        assert mock_post.call_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
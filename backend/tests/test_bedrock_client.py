"""
Unit tests for backend/bedrock_client.py

Tests cover:
  - Valid tool-use response → CoachingResponse returned
  - Malformed response → retry once → BedrockError on second failure
  - Non-2xx status → BedrockError immediately (no retry)
  - ClientError → BedrockError immediately (no retry)
  - TOOL_SCHEMA and SYSTEM_PROMPT constants have expected shape/content

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
"""
from __future__ import annotations

import json
import sys
import types
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is on the path so imports resolve
sys.path.insert(0, ".")

from backend.bedrock_client import (  # noqa: E402
    SYSTEM_PROMPT,
    TOOL_SCHEMA,
    BedrockError,
    _parse_response,
    invoke_bedrock,
)
from backend.models import CoachingResponse, Metrics  # noqa: E402


# ---------------------------------------------------------------------------
# Helper builders
# ---------------------------------------------------------------------------

def _make_valid_response_body(
    tips: list[str] | None = None,
    drill: str = "Catch-up drill: extend each arm fully before starting the next stroke.",
) -> dict:
    """Build a well-formed Bedrock response body with a tool_use block."""
    if tips is None:
        tips = [
            "Improve your flip-turn push-off angle to reduce wall time.",
            "Maintain a higher elbow position during the catch phase.",
            "Reduce your stroke rate slightly and focus on glide distance.",
        ]
    return {
        "id": "msg_01XFDUDYJgAACTu3p9k2WYLR",
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "tool_use",
                "id": "toolu_01T1x1fJ34qAmk2tzvAqgeEA",
                "name": "submit_coaching_response",
                "input": {"tips": tips, "drill": drill},
            }
        ],
        "model": "claude-3-5-sonnet-20240620",
        "stop_reason": "tool_use",
        "usage": {"input_tokens": 100, "output_tokens": 80},
    }


def _make_boto3_response(body_dict: dict, http_status: int = 200) -> dict:
    """Wrap a dict in a fake boto3 invoke_model response."""
    return {
        "ResponseMetadata": {"HTTPStatusCode": http_status},
        "body": BytesIO(json.dumps(body_dict).encode()),
    }


def _make_metrics() -> Metrics:
    return Metrics(pace=95.0, swolf=38.0, stroke_rate=30.0)


# ---------------------------------------------------------------------------
# TOOL_SCHEMA and SYSTEM_PROMPT constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_tool_schema_name(self):
        assert TOOL_SCHEMA["name"] == "submit_coaching_response"

    def test_tool_schema_has_input_schema(self):
        assert "input_schema" in TOOL_SCHEMA
        schema = TOOL_SCHEMA["input_schema"]
        assert schema["type"] == "object"
        assert "tips" in schema["properties"]
        assert "drill" in schema["properties"]
        assert "required" in schema
        assert set(schema["required"]) == {"tips", "drill"}

    def test_tool_schema_tips_array_constraints(self):
        tips_schema = TOOL_SCHEMA["input_schema"]["properties"]["tips"]
        assert tips_schema["type"] == "array"
        assert tips_schema["minItems"] == 3
        assert tips_schema["maxItems"] == 3
        assert tips_schema["items"]["maxLength"] == 300

    def test_tool_schema_drill_max_length(self):
        drill_schema = TOOL_SCHEMA["input_schema"]["properties"]["drill"]
        assert drill_schema["maxLength"] == 500

    def test_system_prompt_mentions_tool(self):
        assert "submit_coaching_response" in SYSTEM_PROMPT

    def test_system_prompt_mentions_coach_persona(self):
        assert "coach" in SYSTEM_PROMPT.lower()


# ---------------------------------------------------------------------------
# _parse_response helper
# ---------------------------------------------------------------------------


class TestParseResponse:
    def test_valid_response_returns_coaching_response(self):
        body = _make_valid_response_body()
        result = _parse_response(body)
        assert isinstance(result, CoachingResponse)
        assert len(result.tips) == 3
        assert isinstance(result.drill, str) and result.drill

    def test_missing_tool_use_block_returns_none(self):
        body = {"content": [{"type": "text", "text": "Hello"}]}
        assert _parse_response(body) is None

    def test_empty_content_returns_none(self):
        assert _parse_response({"content": []}) is None

    def test_wrong_tips_count_returns_none(self):
        body = _make_valid_response_body(tips=["only one tip"])
        # CoachingResponse invariant will reject 1 tip; _parse_response returns None
        assert _parse_response(body) is None

    def test_missing_tips_key_returns_none(self):
        body = {
            "content": [
                {
                    "type": "tool_use",
                    "name": "submit_coaching_response",
                    "input": {"drill": "Some drill"},
                }
            ]
        }
        assert _parse_response(body) is None

    def test_non_list_tips_returns_none(self):
        body = {
            "content": [
                {
                    "type": "tool_use",
                    "name": "submit_coaching_response",
                    "input": {"tips": "not a list", "drill": "drill"},
                }
            ]
        }
        assert _parse_response(body) is None

    def test_non_string_drill_returns_none(self):
        body = {
            "content": [
                {
                    "type": "tool_use",
                    "name": "submit_coaching_response",
                    "input": {"tips": ["A", "B", "C"], "drill": 12345},
                }
            ]
        }
        assert _parse_response(body) is None


# ---------------------------------------------------------------------------
# invoke_bedrock — success path
# ---------------------------------------------------------------------------


class TestInvokeBedrockSuccess:
    def test_valid_response_returns_coaching_response(self):
        metrics = _make_metrics()
        valid_body = _make_valid_response_body()
        mock_response = _make_boto3_response(valid_body)

        mock_client = MagicMock()
        mock_client.invoke_model.return_value = mock_response

        with patch("backend.bedrock_client.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_client
            result = invoke_bedrock(metrics)

        assert isinstance(result, CoachingResponse)
        assert len(result.tips) == 3
        assert isinstance(result.drill, str) and result.drill

    def test_invoke_model_called_with_tool_choice(self):
        metrics = _make_metrics()
        valid_body = _make_valid_response_body()
        mock_response = _make_boto3_response(valid_body)

        mock_client = MagicMock()
        mock_client.invoke_model.return_value = mock_response

        with patch("backend.bedrock_client.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_client
            invoke_bedrock(metrics)

        call_kwargs = mock_client.invoke_model.call_args
        body_str = call_kwargs[1]["body"] if "body" in call_kwargs[1] else call_kwargs[0][1]
        body = json.loads(body_str)
        assert body["tool_choice"] == {"type": "tool", "name": "submit_coaching_response"}

    def test_metrics_included_in_prompt(self):
        metrics = _make_metrics()
        valid_body = _make_valid_response_body()
        mock_response = _make_boto3_response(valid_body)

        mock_client = MagicMock()
        mock_client.invoke_model.return_value = mock_response

        with patch("backend.bedrock_client.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_client
            invoke_bedrock(metrics)

        call_kwargs = mock_client.invoke_model.call_args
        body_str = call_kwargs[1]["body"] if "body" in call_kwargs[1] else call_kwargs[0][1]
        body = json.loads(body_str)
        user_content = body["messages"][0]["content"]
        # Metric values should appear in the user message
        assert "95.0" in user_content
        assert "38.0" in user_content
        assert "30.0" in user_content


# ---------------------------------------------------------------------------
# invoke_bedrock — retry on schema-invalid response
# ---------------------------------------------------------------------------


class TestInvokeBedrockRetry:
    def test_invalid_then_valid_retries_once_and_succeeds(self):
        """First call returns invalid schema; second call returns valid."""
        metrics = _make_metrics()

        invalid_body = {"content": [{"type": "text", "text": "Oops, no tool call"}]}
        valid_body = _make_valid_response_body()

        responses = [
            _make_boto3_response(invalid_body),
            _make_boto3_response(valid_body),
        ]

        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = responses

        with patch("backend.bedrock_client.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_client
            result = invoke_bedrock(metrics)

        assert isinstance(result, CoachingResponse)
        assert mock_client.invoke_model.call_count == 2

    def test_two_invalid_responses_raises_bedrock_error(self):
        """Both attempts return invalid schema → BedrockError."""
        metrics = _make_metrics()

        invalid_body = {"content": [{"type": "text", "text": "No tool call here"}]}
        responses = [
            _make_boto3_response(invalid_body),
            _make_boto3_response(invalid_body),
        ]

        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = responses

        with patch("backend.bedrock_client.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_client
            with pytest.raises(BedrockError):
                invoke_bedrock(metrics)

        assert mock_client.invoke_model.call_count == 2

    def test_exactly_one_retry_on_invalid_schema(self):
        """Confirm no more than 2 total calls are made even with repeated failures."""
        metrics = _make_metrics()
        invalid_body = {"content": []}
        # Build each response independently so each has its own fresh BytesIO
        responses = [_make_boto3_response(invalid_body) for _ in range(5)]

        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = responses

        with patch("backend.bedrock_client.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_client
            with pytest.raises(BedrockError):
                invoke_bedrock(metrics)

        # Must not exceed 2 calls (initial + 1 retry)
        assert mock_client.invoke_model.call_count == 2


# ---------------------------------------------------------------------------
# invoke_bedrock — no retry on non-2xx or ClientError
# ---------------------------------------------------------------------------


class TestInvokeBedrockNoRetryOnError:
    def test_client_error_raises_bedrock_error_immediately(self):
        """ClientError → BedrockError, no retry."""
        from botocore.exceptions import ClientError

        metrics = _make_metrics()
        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "denied"}},
            "InvokeModel",
        )

        with patch("backend.bedrock_client.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_client
            with pytest.raises(BedrockError):
                invoke_bedrock(metrics)

        assert mock_client.invoke_model.call_count == 1  # no retry

    def test_generic_exception_raises_bedrock_error_immediately(self):
        """Any network-level exception → BedrockError, no retry."""
        metrics = _make_metrics()
        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = ConnectionError("Network unreachable")

        with patch("backend.bedrock_client.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_client
            with pytest.raises(BedrockError):
                invoke_bedrock(metrics)

        assert mock_client.invoke_model.call_count == 1  # no retry

    def test_non_2xx_http_status_raises_bedrock_error_immediately(self):
        """Non-2xx HTTP status in ResponseMetadata → BedrockError, no retry."""
        metrics = _make_metrics()
        # Simulate a 503 body that boto3 somehow passes through (shouldn't happen
        # normally, but we guard explicitly)
        non_2xx_response = {
            "ResponseMetadata": {"HTTPStatusCode": 503},
            "body": BytesIO(b'{"error": "Service Unavailable"}'),
        }

        mock_client = MagicMock()
        mock_client.invoke_model.return_value = non_2xx_response

        with patch("backend.bedrock_client.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_client
            with pytest.raises(BedrockError):
                invoke_bedrock(metrics)

        assert mock_client.invoke_model.call_count == 1  # no retry

    def test_bedrock_error_has_http_status_502(self):
        """BedrockError instances must carry http_status == 502."""
        err = BedrockError("something went wrong")
        assert err.http_status == 502

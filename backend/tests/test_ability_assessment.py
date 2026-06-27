"""
Unit tests for ability assessment in backend/bedrock_client.py

Tests cover:
  - Valid tool-use response → AbilityAssessment returned
  - Malformed response → retry once → BedrockError on second failure
  - Non-2xx status → BedrockError immediately (no retry)
  - ABILITY_ASSESSMENT_TOOL_SCHEMA and ABILITY_ASSESSMENT_SYSTEM_PROMPT have expected shape

Requirements: 7.1-7.12, 8.1-8.7
"""
from __future__ import annotations

import json
import sys
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is on the path so imports resolve
sys.path.insert(0, ".")

from backend.bedrock_client import (  # noqa: E402
    ABILITY_ASSESSMENT_SYSTEM_PROMPT,
    ABILITY_ASSESSMENT_TOOL_SCHEMA,
    BedrockError,
    _parse_ability_assessment_response,
    generate_ability_assessment,
)
from backend.models import Metrics, AbilityAssessment  # noqa: E402


# ---------------------------------------------------------------------------
# Helper builders
# ---------------------------------------------------------------------------

def _make_valid_ability_assessment_response(
    percentile_estimate: str = "top 25%",
    local_ranking: str = "estimated 5th out of 50 swimmers in your area",
    national_ranking: str = "estimated top 30% nationally",
    competitive_analysis: str = "Based on your metrics, you are competitive at the local level.",
) -> dict:
    """Build a well-formed Bedrock response body with ability assessment tool_use block."""
    return {
        "id": "msg_01XFDUDYJgAACTu3p9k2WYLR",
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "tool_use",
                "id": "toolu_01T1x1fJ34qAmk2tzvAqgeEA",
                "name": "submit_ability_assessment",
                "input": {
                    "percentile_estimate": percentile_estimate,
                    "local_ranking": local_ranking,
                    "national_ranking": national_ranking,
                    "competitive_analysis": competitive_analysis,
                },
            }
        ],
        "model": "claude-3-5-sonnet-20240620",
        "stop_reason": "tool_use",
        "usage": {"input_tokens": 200, "output_tokens": 150},
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
# ABILITY_ASSESSMENT_TOOL_SCHEMA and SYSTEM_PROMPT constants
# ---------------------------------------------------------------------------


class TestAbilityAssessmentConstants:
    def test_tool_schema_name(self):
        assert ABILITY_ASSESSMENT_TOOL_SCHEMA["name"] == "submit_ability_assessment"

    def test_tool_schema_has_input_schema(self):
        assert "input_schema" in ABILITY_ASSESSMENT_TOOL_SCHEMA
        schema = ABILITY_ASSESSMENT_TOOL_SCHEMA["input_schema"]
        assert schema["type"] == "object"
        assert "percentile_estimate" in schema["properties"]
        assert "local_ranking" in schema["properties"]
        assert "national_ranking" in schema["properties"]
        assert "competitive_analysis" in schema["properties"]
        assert set(schema["required"]) == {
            "percentile_estimate",
            "local_ranking",
            "national_ranking",
            "competitive_analysis",
        }

    def test_tool_schema_field_constraints(self):
        schema = ABILITY_ASSESSMENT_TOOL_SCHEMA["input_schema"]["properties"]
        assert schema["percentile_estimate"]["maxLength"] == 100
        assert schema["local_ranking"]["maxLength"] == 200
        assert schema["national_ranking"]["maxLength"] == 200
        assert schema["competitive_analysis"]["maxLength"] == 800

    def test_system_prompt_mentions_tool(self):
        assert "submit_ability_assessment" in ABILITY_ASSESSMENT_SYSTEM_PROMPT

    def test_system_prompt_mentions_coach_persona(self):
        assert "coach" in ABILITY_ASSESSMENT_SYSTEM_PROMPT.lower()


# ---------------------------------------------------------------------------
# _parse_ability_assessment_response helper
# ---------------------------------------------------------------------------


class TestParseAbilityAssessmentResponse:
    def test_valid_response_returns_ability_assessment(self):
        body = _make_valid_ability_assessment_response()
        result = _parse_ability_assessment_response(body)
        assert isinstance(result, AbilityAssessment)
        assert result.percentile_estimate == "top 25%"
        assert "5th out of 50" in result.local_ranking
        assert "top 30%" in result.national_ranking
        assert result.competitive_analysis

    def test_missing_tool_use_block_returns_none(self):
        body = {"content": [{"type": "text", "text": "Hello"}]}
        assert _parse_ability_assessment_response(body) is None

    def test_empty_content_returns_none(self):
        assert _parse_ability_assessment_response({"content": []}) is None

    def test_empty_percentile_estimate_returns_none(self):
        body = _make_valid_ability_assessment_response(percentile_estimate="")
        assert _parse_ability_assessment_response(body) is None

    def test_empty_local_ranking_returns_none(self):
        body = _make_valid_ability_assessment_response(local_ranking="")
        assert _parse_ability_assessment_response(body) is None

    def test_missing_field_returns_none(self):
        body = {
            "content": [
                {
                    "type": "tool_use",
                    "name": "submit_ability_assessment",
                    "input": {
                        "percentile_estimate": "top 25%",
                        "local_ranking": "estimated 5th",
                        # Missing national_ranking and competitive_analysis
                    },
                }
            ]
        }
        assert _parse_ability_assessment_response(body) is None


# ---------------------------------------------------------------------------
# generate_ability_assessment integration
# ---------------------------------------------------------------------------


class TestGenerateAbilityAssessmentSuccess:
    """Tests for successful ability assessment generation."""

    @patch("backend.bedrock_client.boto3.client")
    def test_invoke_model_called_with_correct_parameters(self, mock_boto_client):
        """generate_ability_assessment calls boto3 with correct model ID and parameters."""
        mock_client_instance = MagicMock()
        mock_boto_client.return_value = mock_client_instance
        
        valid_body = _make_valid_ability_assessment_response()
        mock_client_instance.invoke_model.return_value = _make_boto3_response(valid_body)

        metrics = _make_metrics()
        result = generate_ability_assessment(
            metrics=metrics,
            age=25,
            nationality="USA",
            locality="California",
            ability_level="intermediate",
        )

        assert isinstance(result, AbilityAssessment)
        mock_client_instance.invoke_model.assert_called_once()
        call_args = mock_client_instance.invoke_model.call_args
        
        # Verify the request body contains profile data
        body_json = json.loads(call_args[1]["body"])
        user_message = body_json["messages"][0]["content"]
        assert "Age: 25" in user_message
        assert "USA" in user_message
        assert "California" in user_message
        assert "intermediate" in user_message
        assert "95.0" in user_message  # pace


class TestGenerateAbilityAssessmentRetry:
    """Tests for retry logic on invalid responses."""

    @patch("backend.bedrock_client.boto3.client")
    def test_retry_on_malformed_response(self, mock_boto_client):
        """generate_ability_assessment retries once on malformed response."""
        mock_client_instance = MagicMock()
        mock_boto_client.return_value = mock_client_instance

        # First call: malformed response
        malformed_body = {"content": []}
        # Second call: valid response
        valid_body = _make_valid_ability_assessment_response()

        mock_client_instance.invoke_model.side_effect = [
            _make_boto3_response(malformed_body),
            _make_boto3_response(valid_body),
        ]

        metrics = _make_metrics()
        result = generate_ability_assessment(
            metrics=metrics,
            age=25,
            nationality="USA",
            locality="California",
            ability_level="intermediate",
        )

        assert isinstance(result, AbilityAssessment)
        assert mock_client_instance.invoke_model.call_count == 2

    @patch("backend.bedrock_client.boto3.client")
    def test_raises_bedrock_error_after_retry(self, mock_boto_client):
        """generate_ability_assessment raises BedrockError after retry fails."""
        mock_client_instance = MagicMock()
        mock_boto_client.return_value = mock_client_instance

        # Both calls return malformed responses
        malformed_body = {"content": []}
        mock_client_instance.invoke_model.side_effect = [
            _make_boto3_response(malformed_body),
            _make_boto3_response(malformed_body),
        ]

        metrics = _make_metrics()
        with pytest.raises(BedrockError, match="AI coach unavailable for ability assessment"):
            generate_ability_assessment(
                metrics=metrics,
                age=25,
                nationality="USA",
                locality="California",
                ability_level="intermediate",
            )

        assert mock_client_instance.invoke_model.call_count == 2


class TestGenerateAbilityAssessmentErrors:
    """Tests for immediate error cases (network, HTTP errors)."""

    @patch("backend.bedrock_client.boto3.client")
    def test_non_2xx_status_raises_bedrock_error(self, mock_boto_client):
        """generate_ability_assessment raises BedrockError on non-2xx HTTP status."""
        from botocore.exceptions import ClientError

        mock_client_instance = MagicMock()
        mock_boto_client.return_value = mock_client_instance

        # Simulate ClientError
        mock_client_instance.invoke_model.side_effect = ClientError(
            {"Error": {"Code": "ServiceUnavailable", "Message": "Service unavailable"}},
            "InvokeModel",
        )

        metrics = _make_metrics()
        with pytest.raises(BedrockError, match="AI coach unavailable"):
            generate_ability_assessment(
                metrics=metrics,
                age=25,
                nationality="USA",
                locality="California",
                ability_level="intermediate",
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

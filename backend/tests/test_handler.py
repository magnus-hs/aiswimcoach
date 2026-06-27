"""
Unit tests for backend/handler.py

Tests cover the handler pipeline wiring and error mapping:
  - MultipartParseError → HTTP 400
  - StorageError → HTTP 500
  - FitParseError → HTTP 422
  - MetricsMissingError → HTTP 422
  - BedrockError → HTTP 502
  - DynamoDB failure → logged, HTTP 200 still returned
  - Full success pipeline → HTTP 200 with coaching JSON

Requirements: 2.2, 2.3, 3.1, 3.3, 3.4, 4.1, 5.1, 6.1, 6.3, 7.1
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from backend.handler import handler, http_200
from backend.models import CoachingResponse, Metrics


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

MOCK_EVENT = {
    "body": "base64data",
    "isBase64Encoded": True,
    "headers": {"Content-Type": "multipart/form-data; boundary=----abc"},
}

MOCK_CONTEXT = MagicMock()

SAMPLE_METRICS = Metrics(pace=95.0, swolf=38.0, stroke_rate=30.0)
SAMPLE_COACHING = CoachingResponse(
    tips=["Tip one", "Tip two", "Tip three"],
    drill="Catch-up drill",
)


def _assert_error_response(response: dict, status_code: int, error_substring: str) -> None:
    """Assert the response is an error with the expected status and message."""
    assert response["statusCode"] == status_code
    assert response["headers"]["Content-Type"] == "application/json"
    assert response["headers"]["Access-Control-Allow-Origin"] == "*"
    body = json.loads(response["body"])
    assert "error" in body
    assert error_substring in body["error"]


# ---------------------------------------------------------------------------
# Error mapping tests
# ---------------------------------------------------------------------------


class TestMultipartParseError:
    """MultipartParseError from parse_multipart → HTTP 400."""

    @patch("backend.handler.parse_multipart")
    def test_returns_400(self, mock_parse: MagicMock) -> None:
        from backend.multipart_parser import ParseError as MultipartParseError
        mock_parse.side_effect = MultipartParseError("No FIT file found in request")

        response = handler(MOCK_EVENT, MOCK_CONTEXT)

        _assert_error_response(response, 400, "No FIT file found in request")

    @patch("backend.handler.parse_multipart")
    def test_does_not_call_downstream(self, mock_parse: MagicMock) -> None:
        from backend.multipart_parser import ParseError as MultipartParseError
        mock_parse.side_effect = MultipartParseError("missing")

        with patch("backend.handler.store_in_s3") as mock_s3:
            handler(MOCK_EVENT, MOCK_CONTEXT)
            mock_s3.assert_not_called()


class TestStorageError:
    """StorageError from store_in_s3 → HTTP 500."""

    @patch("backend.handler.parse_multipart", return_value=b"fitbytes")
    @patch("backend.handler.store_in_s3")
    def test_returns_500(self, mock_s3: MagicMock, mock_parse: MagicMock) -> None:
        from backend.s3_store import StorageError
        mock_s3.side_effect = StorageError("Failed to store file")

        response = handler(MOCK_EVENT, MOCK_CONTEXT)

        _assert_error_response(response, 500, "Failed to store file")


class TestFitParseError:
    """FitParseError from parse_fit → HTTP 422."""

    @patch("backend.handler.parse_multipart", return_value=b"fitbytes")
    @patch("backend.handler.store_in_s3", return_value="uploads/uuid.fit")
    @patch("backend.handler.parse_fit")
    def test_malformed_file_returns_422(
        self, mock_fit: MagicMock, mock_s3: MagicMock, mock_parse: MagicMock
    ) -> None:
        from backend.fit_parser import ParseError as FitParseError
        mock_fit.side_effect = FitParseError("Malformed FIT file: bad header")

        response = handler(MOCK_EVENT, MOCK_CONTEXT)

        _assert_error_response(response, 422, "Malformed FIT file")


class TestMetricsMissingError:
    """MetricsMissingError from parse_fit → HTTP 422 listing missing metrics."""

    @patch("backend.handler.parse_multipart", return_value=b"fitbytes")
    @patch("backend.handler.store_in_s3", return_value="uploads/uuid.fit")
    @patch("backend.handler.parse_fit")
    def test_missing_metrics_returns_422(
        self, mock_fit: MagicMock, mock_s3: MagicMock, mock_parse: MagicMock
    ) -> None:
        from backend.fit_parser import MetricsMissingError
        mock_fit.side_effect = MetricsMissingError(["pace", "SWOLF"])

        response = handler(MOCK_EVENT, MOCK_CONTEXT)

        _assert_error_response(response, 422, "Missing metrics: pace, SWOLF")


class TestBedrockError:
    """BedrockError from invoke_bedrock → HTTP 502."""

    @patch("backend.handler.parse_multipart", return_value=b"fitbytes")
    @patch("backend.handler.store_in_s3", return_value="uploads/uuid.fit")
    @patch("backend.handler.parse_fit", return_value=SAMPLE_METRICS)
    @patch("backend.handler.invoke_bedrock")
    def test_returns_502(
        self, mock_bedrock: MagicMock, mock_fit: MagicMock,
        mock_s3: MagicMock, mock_parse: MagicMock
    ) -> None:
        from backend.bedrock_client import BedrockError
        mock_bedrock.side_effect = BedrockError("AI coach unavailable")

        response = handler(MOCK_EVENT, MOCK_CONTEXT)

        _assert_error_response(response, 502, "AI coach unavailable")


class TestDynamoDBBestEffort:
    """DynamoDB failure is logged but does not block HTTP 200."""

    @patch("backend.handler.parse_multipart", return_value=b"fitbytes")
    @patch("backend.handler.store_in_s3", return_value="uploads/uuid.fit")
    @patch("backend.handler.parse_fit", return_value=SAMPLE_METRICS)
    @patch("backend.handler.invoke_bedrock", return_value=SAMPLE_COACHING)
    @patch("backend.handler.save_to_dynamodb")
    def test_dynamo_error_still_returns_200(
        self, mock_dynamo: MagicMock, mock_bedrock: MagicMock,
        mock_fit: MagicMock, mock_s3: MagicMock, mock_parse: MagicMock
    ) -> None:
        mock_dynamo.side_effect = RuntimeError("DynamoDB unreachable")

        response = handler(MOCK_EVENT, MOCK_CONTEXT)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["tips"] == ["Tip one", "Tip two", "Tip three"]
        assert body["drill"] == "Catch-up drill"


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


class TestSuccessPipeline:
    """Full pipeline success → HTTP 200 with coaching JSON."""

    @patch("backend.handler.parse_multipart", return_value=b"fitbytes")
    @patch("backend.handler.store_in_s3", return_value="uploads/uuid.fit")
    @patch("backend.handler.parse_fit", return_value=SAMPLE_METRICS)
    @patch("backend.handler.invoke_bedrock", return_value=SAMPLE_COACHING)
    @patch("backend.handler.save_to_dynamodb")
    def test_returns_200_with_coaching(
        self, mock_dynamo: MagicMock, mock_bedrock: MagicMock,
        mock_fit: MagicMock, mock_s3: MagicMock, mock_parse: MagicMock
    ) -> None:
        response = handler(MOCK_EVENT, MOCK_CONTEXT)

        assert response["statusCode"] == 200
        assert response["headers"]["Content-Type"] == "application/json"
        assert response["headers"]["Access-Control-Allow-Origin"] == "*"

        body = json.loads(response["body"])
        assert body["tips"] == ["Tip one", "Tip two", "Tip three"]
        assert body["drill"] == "Catch-up drill"

    @patch("backend.handler.parse_multipart", return_value=b"fitbytes")
    @patch("backend.handler.store_in_s3", return_value="uploads/uuid.fit")
    @patch("backend.handler.parse_fit", return_value=SAMPLE_METRICS)
    @patch("backend.handler.invoke_bedrock", return_value=SAMPLE_COACHING)
    @patch("backend.handler.save_to_dynamodb")
    def test_pipeline_calls_in_order(
        self, mock_dynamo: MagicMock, mock_bedrock: MagicMock,
        mock_fit: MagicMock, mock_s3: MagicMock, mock_parse: MagicMock
    ) -> None:
        handler(MOCK_EVENT, MOCK_CONTEXT)

        # Verify each stage was called with the expected arguments
        mock_parse.assert_called_once_with(MOCK_EVENT)
        mock_s3.assert_called_once_with(b"fitbytes")
        mock_fit.assert_called_once_with(b"fitbytes")
        mock_bedrock.assert_called_once_with(SAMPLE_METRICS)
        mock_dynamo.assert_called_once_with("uploads/uuid.fit", SAMPLE_METRICS, SAMPLE_COACHING)


# ---------------------------------------------------------------------------
# http_200 helper
# ---------------------------------------------------------------------------


class TestHttp200Helper:
    """The http_200 helper returns a correctly-shaped proxy response."""

    def test_response_shape(self) -> None:
        response = http_200(SAMPLE_COACHING)

        assert response["statusCode"] == 200
        assert response["headers"]["Content-Type"] == "application/json"
        assert response["headers"]["Access-Control-Allow-Origin"] == "*"

        body = json.loads(response["body"])
        assert body == {"tips": ["Tip one", "Tip two", "Tip three"], "drill": "Catch-up drill"}

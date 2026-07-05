"""
Unit tests for handler notes routes and AI chat integration.

Tests cover:
  - POST /notes: success (201), validation failure (400), storage failure (500)
  - GET /notes: success (200), storage failure (500)
  - DELETE /notes: success (200), not found (404), wrong owner (404)
  - AI chat: history retrieval failure → still returns response
  - AI chat: notes retrieval failure → still returns response
  - AI chat: conversation_history in body → passes to prompt assembler

Requirements: 1.5, 1.6, 3.1, 3.3, 3.5, 3.6, 3.8, 5.4
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from handler import (
    _handle_create_note,
    _handle_get_notes,
    _handle_delete_note,
    _handle_ai_chat,
)
from notes_service import NotFoundError as NotesNotFoundError, TrainingNote


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

MOCK_CONTEXT = MagicMock()


def _make_event(body: dict | None = None, user_id: str = "test-user", **extra) -> dict:
    """Build a minimal event dict for handler tests."""
    event = {
        "auth_context": {"user_id": user_id},
        "headers": {"Authorization": "Bearer mock-jwt-token"},
    }
    if body is not None:
        event["body"] = json.dumps(body)
    event.update(extra)
    return event


def _parse_response(response: dict) -> tuple[int, dict]:
    """Extract status code and parsed body from a handler response."""
    status = response["statusCode"]
    body = json.loads(response["body"])
    return status, body


# ---------------------------------------------------------------------------
# POST /notes tests
# ---------------------------------------------------------------------------


class TestCreateNote:
    """Tests for _handle_create_note (POST /notes)."""

    @patch("middleware.verify_token", return_value={"user_id": "test-user", "email": "test@example.com"})
    @patch("handler.notes_service.create_note")
    def test_success_returns_201(self, mock_create: MagicMock, mock_verify: MagicMock) -> None:
        """Successful note creation returns 201 with note data."""
        mock_create.return_value = TrainingNote(
            user_id="test-user",
            note_id="note-123",
            text="Shoulder felt tight",
            timestamp="2025-01-15T10:30:00+00:00",
        )
        event = _make_event(body={"text": "Shoulder felt tight"})

        response = _handle_create_note(event, MOCK_CONTEXT)

        status, body = _parse_response(response)
        assert status == 201
        assert body["note_id"] == "note-123"
        assert body["text"] == "Shoulder felt tight"
        assert body["timestamp"] == "2025-01-15T10:30:00+00:00"
        mock_create.assert_called_once_with("test-user", "Shoulder felt tight", session_id=None)

    @patch("middleware.verify_token", return_value={"user_id": "test-user", "email": "test@example.com"})
    @patch("handler.notes_service.create_note")
    def test_validation_failure_returns_400(self, mock_create: MagicMock, mock_verify: MagicMock) -> None:
        """Empty note text triggers ValueError from service → 400."""
        mock_create.side_effect = ValueError("Note text must not be empty")
        event = _make_event(body={"text": ""})

        response = _handle_create_note(event, MOCK_CONTEXT)

        status, body = _parse_response(response)
        assert status == 400
        assert "empty" in body["error"].lower()

    @patch("middleware.verify_token", return_value={"user_id": "test-user", "email": "test@example.com"})
    @patch("handler.notes_service.create_note")
    def test_too_long_text_returns_400(self, mock_create: MagicMock, mock_verify: MagicMock) -> None:
        """Text exceeding 500 chars triggers ValueError → 400."""
        mock_create.side_effect = ValueError("Note text must not exceed 500 characters")
        event = _make_event(body={"text": "x" * 501})

        response = _handle_create_note(event, MOCK_CONTEXT)

        status, body = _parse_response(response)
        assert status == 400
        assert "500" in body["error"]

    @patch("middleware.verify_token", return_value={"user_id": "test-user", "email": "test@example.com"})
    @patch("handler.notes_service.create_note")
    def test_storage_failure_returns_500(self, mock_create: MagicMock, mock_verify: MagicMock) -> None:
        """DynamoDB write failure → 500."""
        mock_create.side_effect = RuntimeError("DynamoDB unreachable")
        event = _make_event(body={"text": "Valid note text"})

        response = _handle_create_note(event, MOCK_CONTEXT)

        status, body = _parse_response(response)
        assert status == 500
        assert "create note" in body["error"].lower()

    @patch("middleware.verify_token", return_value={"user_id": "test-user", "email": "test@example.com"})
    def test_invalid_json_body_returns_400(self, mock_verify: MagicMock) -> None:
        """Malformed JSON body → 400."""
        event = _make_event()
        event["body"] = "not-json{"

        response = _handle_create_note(event, MOCK_CONTEXT)

        status, body = _parse_response(response)
        assert status == 400
        assert "json" in body["error"].lower()

    @patch("middleware.verify_token", return_value={"user_id": "test-user", "email": "test@example.com"})
    @patch("handler.notes_service.create_note")
    def test_non_string_text_returns_400(self, mock_create: MagicMock, mock_verify: MagicMock) -> None:
        """Non-string text field → 400."""
        event = _make_event(body={"text": 12345})

        response = _handle_create_note(event, MOCK_CONTEXT)

        status, body = _parse_response(response)
        assert status == 400
        assert "string" in body["error"].lower()
        mock_create.assert_not_called()


# ---------------------------------------------------------------------------
# GET /notes tests
# ---------------------------------------------------------------------------


class TestGetNotes:
    """Tests for _handle_get_notes (GET /notes)."""

    @patch("middleware.verify_token", return_value={"user_id": "test-user", "email": "test@example.com"})
    @patch("handler.notes_service.get_notes")
    def test_success_returns_200_with_notes(self, mock_get: MagicMock, mock_verify: MagicMock) -> None:
        """Successful retrieval returns 200 with notes list."""
        mock_get.return_value = [
            TrainingNote(user_id="test-user", note_id="n1", text="Note 1", timestamp="2025-01-15T10:00:00+00:00"),
            TrainingNote(user_id="test-user", note_id="n2", text="Note 2", timestamp="2025-01-14T10:00:00+00:00"),
        ]
        event = _make_event()

        response = _handle_get_notes(event, MOCK_CONTEXT)

        status, body = _parse_response(response)
        assert status == 200
        assert len(body["notes"]) == 2
        assert body["notes"][0]["note_id"] == "n1"
        assert body["notes"][1]["note_id"] == "n2"
        mock_get.assert_called_once_with("test-user", session_id=None)

    @patch("middleware.verify_token", return_value={"user_id": "test-user", "email": "test@example.com"})
    @patch("handler.notes_service.get_notes")
    def test_empty_notes_returns_200_with_empty_list(self, mock_get: MagicMock, mock_verify: MagicMock) -> None:
        """No notes for user → 200 with empty list."""
        mock_get.return_value = []
        event = _make_event()

        response = _handle_get_notes(event, MOCK_CONTEXT)

        status, body = _parse_response(response)
        assert status == 200
        assert body["notes"] == []

    @patch("middleware.verify_token", return_value={"user_id": "test-user", "email": "test@example.com"})
    @patch("handler.notes_service.get_notes")
    def test_storage_failure_returns_500(self, mock_get: MagicMock, mock_verify: MagicMock) -> None:
        """DynamoDB query failure → 500."""
        mock_get.side_effect = RuntimeError("DynamoDB unreachable")
        event = _make_event()

        response = _handle_get_notes(event, MOCK_CONTEXT)

        status, body = _parse_response(response)
        assert status == 500
        assert "retrieve notes" in body["error"].lower()


# ---------------------------------------------------------------------------
# DELETE /notes tests
# ---------------------------------------------------------------------------


class TestDeleteNote:
    """Tests for _handle_delete_note (DELETE /notes/{note_id})."""

    @patch("middleware.verify_token", return_value={"user_id": "test-user", "email": "test@example.com"})
    @patch("handler.notes_service.delete_note")
    def test_success_returns_200(self, mock_delete: MagicMock, mock_verify: MagicMock) -> None:
        """Successful deletion returns 200 with confirmation message."""
        mock_delete.return_value = True
        event = _make_event(note_id="note-123")

        response = _handle_delete_note(event, MOCK_CONTEXT)

        status, body = _parse_response(response)
        assert status == 200
        assert body["message"] == "Note deleted"
        mock_delete.assert_called_once_with("test-user", "note-123")

    @patch("middleware.verify_token", return_value={"user_id": "test-user", "email": "test@example.com"})
    @patch("handler.notes_service.delete_note")
    def test_not_found_returns_404(self, mock_delete: MagicMock, mock_verify: MagicMock) -> None:
        """Note doesn't exist → NotFoundError → 404."""
        # Use the same NotesNotFoundError class the handler imports
        from handler import NotesNotFoundError as HandlerNotFoundError
        mock_delete.side_effect = HandlerNotFoundError("Note not found")
        event = _make_event(note_id="nonexistent-id")

        response = _handle_delete_note(event, MOCK_CONTEXT)

        status, body = _parse_response(response)
        assert status == 404
        assert "not found" in body["error"].lower()

    @patch("middleware.verify_token", return_value={"user_id": "test-user", "email": "test@example.com"})
    @patch("handler.notes_service.delete_note")
    def test_wrong_owner_returns_404(self, mock_delete: MagicMock, mock_verify: MagicMock) -> None:
        """Note belongs to another user → NotFoundError → 404."""
        from handler import NotesNotFoundError as HandlerNotFoundError
        mock_delete.side_effect = HandlerNotFoundError("Note not found")
        event = _make_event(note_id="other-users-note")

        response = _handle_delete_note(event, MOCK_CONTEXT)

        status, body = _parse_response(response)
        assert status == 404
        assert "not found" in body["error"].lower()

    @patch("middleware.verify_token", return_value={"user_id": "test-user", "email": "test@example.com"})
    @patch("handler.notes_service.delete_note")
    def test_storage_failure_returns_500(self, mock_delete: MagicMock, mock_verify: MagicMock) -> None:
        """DynamoDB error during deletion → 500."""
        mock_delete.side_effect = RuntimeError("DynamoDB unreachable")
        event = _make_event(note_id="note-123")

        response = _handle_delete_note(event, MOCK_CONTEXT)

        status, body = _parse_response(response)
        assert status == 500
        assert "delete note" in body["error"].lower()


# ---------------------------------------------------------------------------
# AI chat integration tests
# ---------------------------------------------------------------------------


class TestAIChatHistoryFailure:
    """AI chat still returns response when chat history retrieval fails."""

    @patch("middleware.verify_token", return_value={"user_id": "test-user", "email": "test@example.com"})
    @patch("handler.chat_history_store.get_history")
    @patch("handler.notes_service.get_notes")
    @patch("handler.get_user_sessions", return_value=[])
    @patch("handler.boto3.resource")
    @patch("handler.boto3.client")
    def test_history_failure_still_returns_response(
        self,
        mock_boto_client: MagicMock,
        mock_boto_resource: MagicMock,
        mock_sessions: MagicMock,
        mock_get_notes: MagicMock,
        mock_get_history: MagicMock,
        mock_verify: MagicMock,
    ) -> None:
        """When chat_history_store.get_history raises, AI chat continues."""
        mock_get_history.side_effect = RuntimeError("S3 unreachable")
        mock_get_notes.return_value = []

        # Mock DynamoDB profile lookup
        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": {}}
        mock_boto_resource.return_value.Table.return_value = mock_table

        # Mock Bedrock response
        mock_bedrock = MagicMock()
        mock_bedrock.invoke_model.return_value = {
            "body": MagicMock(read=MagicMock(return_value=json.dumps({
                "content": [{"type": "text", "text": "AI response despite history failure"}]
            }).encode()))
        }
        mock_boto_client.return_value = mock_bedrock

        event = _make_event(body={"prompt": "How is my technique?"})

        with patch("handler.chat_history_store.append_entry"):
            response = _handle_ai_chat(event, MOCK_CONTEXT)

        status, body = _parse_response(response)
        assert status == 200
        assert "response" in body
        assert body["response"] == "AI response despite history failure"


class TestAIChatNotesFailure:
    """AI chat still returns response when notes retrieval fails."""

    @patch("middleware.verify_token", return_value={"user_id": "test-user", "email": "test@example.com"})
    @patch("handler.chat_history_store.get_history", return_value=[])
    @patch("handler.notes_service.get_notes")
    @patch("handler.get_user_sessions", return_value=[])
    @patch("handler.boto3.resource")
    @patch("handler.boto3.client")
    def test_notes_failure_still_returns_response(
        self,
        mock_boto_client: MagicMock,
        mock_boto_resource: MagicMock,
        mock_sessions: MagicMock,
        mock_get_notes: MagicMock,
        mock_get_history: MagicMock,
        mock_verify: MagicMock,
    ) -> None:
        """When notes_service.get_notes raises, AI chat continues."""
        mock_get_notes.side_effect = RuntimeError("DynamoDB unreachable")

        # Mock DynamoDB profile lookup
        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": {}}
        mock_boto_resource.return_value.Table.return_value = mock_table

        # Mock Bedrock response
        mock_bedrock = MagicMock()
        mock_bedrock.invoke_model.return_value = {
            "body": MagicMock(read=MagicMock(return_value=json.dumps({
                "content": [{"type": "text", "text": "AI response despite notes failure"}]
            }).encode()))
        }
        mock_boto_client.return_value = mock_bedrock

        event = _make_event(body={"prompt": "How is my technique?"})

        with patch("handler.chat_history_store.append_entry"):
            response = _handle_ai_chat(event, MOCK_CONTEXT)

        status, body = _parse_response(response)
        assert status == 200
        assert "response" in body
        assert body["response"] == "AI response despite notes failure"


class TestAIChatConversationHistory:
    """AI chat passes conversation_history from body to prompt assembler."""

    @patch("middleware.verify_token", return_value={"user_id": "test-user", "email": "test@example.com"})
    @patch("handler.chat_history_store.get_history", return_value=[])
    @patch("handler.notes_service.get_notes", return_value=[])
    @patch("handler.get_user_sessions", return_value=[])
    @patch("handler.boto3.resource")
    @patch("handler.boto3.client")
    @patch("handler.build_chat_messages")
    def test_conversation_history_passed_to_assembler(
        self,
        mock_build: MagicMock,
        mock_boto_client: MagicMock,
        mock_boto_resource: MagicMock,
        mock_sessions: MagicMock,
        mock_get_notes: MagicMock,
        mock_get_history: MagicMock,
        mock_verify: MagicMock,
    ) -> None:
        """conversation_history from request body is used as effective_history."""
        # Set up prompt assembler mock
        mock_build.return_value = ("system prompt", [{"role": "user", "content": "test"}])

        # Mock DynamoDB profile lookup
        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": {}}
        mock_boto_resource.return_value.Table.return_value = mock_table

        # Mock Bedrock response
        mock_bedrock = MagicMock()
        mock_bedrock.invoke_model.return_value = {
            "body": MagicMock(read=MagicMock(return_value=json.dumps({
                "content": [{"type": "text", "text": "AI response with history"}]
            }).encode()))
        }
        mock_boto_client.return_value = mock_bedrock

        conversation_history = [
            {"role": "user", "content": "What is my SWOLF trend?"},
            {"role": "assistant", "content": "Your SWOLF has improved..."},
        ]
        event = _make_event(body={
            "prompt": "Can you elaborate?",
            "conversation_history": conversation_history,
        })

        with patch("handler.chat_history_store.append_entry"):
            response = _handle_ai_chat(event, MOCK_CONTEXT)

        status, body = _parse_response(response)
        assert status == 200

        # Verify build_chat_messages was called with the client-provided conversation_history
        mock_build.assert_called_once()
        call_kwargs = mock_build.call_args
        # The conversation_history argument should be the client-provided one
        assert call_kwargs[1]["conversation_history"] == conversation_history or \
            call_kwargs[0][1] == conversation_history

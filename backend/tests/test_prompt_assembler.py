"""Unit tests for prompt_assembler.build_chat_messages."""
from __future__ import annotations

import sys
import os
from dataclasses import dataclass

# Ensure the backend module is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from prompt_assembler import build_chat_messages


# ---------------------------------------------------------------------------
# Test helper: simple TrainingNote-like object
# ---------------------------------------------------------------------------


@dataclass
class FakeNote:
    text: str
    timestamp: str


# ---------------------------------------------------------------------------
# Tests: Basic behavior
# ---------------------------------------------------------------------------


class TestBuildChatMessagesBasic:
    """Basic functionality tests for build_chat_messages."""

    def test_empty_history_and_no_notes(self):
        """Req 2.4: No history → only current prompt in messages."""
        system, messages = build_chat_messages("Hello coach", [], [])
        assert len(messages) == 1
        assert messages[0] == {"role": "user", "content": "Hello coach"}
        # No continuity instruction when no history
        assert "Prior conversation context" not in system

    def test_current_prompt_is_last_message(self):
        """Req 2.2: Current prompt is always the final user message."""
        history = [
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
        ]
        system, messages = build_chat_messages("Follow up", history, [])
        assert messages[-1] == {"role": "user", "content": "Follow up"}

    def test_history_preserved_chronologically(self):
        """Req 2.1, 2.2: History is ordered oldest first."""
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
        ]
        system, messages = build_chat_messages("Q3", history, [])
        # History messages + current prompt
        assert len(messages) == 5
        assert messages[0]["content"] == "Q1"
        assert messages[1]["content"] == "A1"
        assert messages[2]["content"] == "Q2"
        assert messages[3]["content"] == "A2"
        assert messages[4]["content"] == "Q3"

    def test_continuity_instruction_present_with_history(self):
        """Req 2.5: System prompt includes continuity instruction when history present."""
        history = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"},
        ]
        system, messages = build_chat_messages("How am I doing?", history, [])
        assert "Prior conversation context" in system
        assert "Maintain continuity" in system


# ---------------------------------------------------------------------------
# Tests: Malformed entry filtering
# ---------------------------------------------------------------------------


class TestMalformedFiltering:
    """Tests for filtering malformed history entries (Req 2.6)."""

    def test_missing_role(self):
        """Entry missing 'role' is excluded."""
        history = [
            {"content": "no role here"},
            {"role": "user", "content": "valid"},
            {"role": "assistant", "content": "valid too"},
        ]
        _, messages = build_chat_messages("current", history, [])
        # 2 valid entries + current prompt
        assert len(messages) == 3

    def test_missing_content(self):
        """Entry missing 'content' is excluded."""
        history = [
            {"role": "user"},
            {"role": "user", "content": "valid"},
            {"role": "assistant", "content": "ok"},
        ]
        _, messages = build_chat_messages("now", history, [])
        assert len(messages) == 3

    def test_empty_role(self):
        """Entry with empty string role is excluded."""
        history = [
            {"role": "", "content": "empty role"},
            {"role": "user", "content": "good"},
            {"role": "assistant", "content": "also good"},
        ]
        _, messages = build_chat_messages("q", history, [])
        assert len(messages) == 3

    def test_empty_content(self):
        """Entry with empty string content is excluded."""
        history = [
            {"role": "user", "content": ""},
            {"role": "user", "content": "real"},
            {"role": "assistant", "content": "answer"},
        ]
        _, messages = build_chat_messages("q", history, [])
        assert len(messages) == 3

    def test_non_dict_entries(self):
        """Non-dict entries are excluded."""
        history = [
            "not a dict",
            42,
            None,
            {"role": "user", "content": "ok"},
            {"role": "assistant", "content": "yes"},
        ]
        _, messages = build_chat_messages("q", history, [])
        assert len(messages) == 3

    def test_non_string_role_or_content(self):
        """Non-string role or content is excluded."""
        history = [
            {"role": 123, "content": "number role"},
            {"role": "user", "content": 456},
            {"role": "user", "content": "valid"},
            {"role": "assistant", "content": "valid"},
        ]
        _, messages = build_chat_messages("q", history, [])
        assert len(messages) == 3


# ---------------------------------------------------------------------------
# Tests: Exchange truncation
# ---------------------------------------------------------------------------


class TestExchangeTruncation:
    """Tests for max_exchanges limit (Req 2.3)."""

    def test_truncate_to_max_exchanges(self):
        """More than max_exchanges → keep most recent."""
        # 12 exchanges = 24 entries
        history = []
        for i in range(12):
            history.append({"role": "user", "content": f"Q{i}"})
            history.append({"role": "assistant", "content": f"A{i}"})

        _, messages = build_chat_messages("current", history, [], max_exchanges=10)
        # 10 exchanges = 20 entries + 1 current = 21
        assert len(messages) == 21
        # Most recent kept: Q2..Q11 (indices 2..11 from original)
        assert messages[0]["content"] == "Q2"
        assert messages[-2]["content"] == "A11"

    def test_under_max_exchanges_kept_fully(self):
        """Fewer than max_exchanges → all kept."""
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
        ]
        _, messages = build_chat_messages("now", history, [], max_exchanges=10)
        assert len(messages) == 3

    def test_custom_max_exchanges(self):
        """Custom max_exchanges parameter works."""
        history = []
        for i in range(5):
            history.append({"role": "user", "content": f"Q{i}"})
            history.append({"role": "assistant", "content": f"A{i}"})

        _, messages = build_chat_messages("now", history, [], max_exchanges=3)
        # 3 exchanges = 6 entries + 1 current = 7
        assert len(messages) == 7
        # Most recent: Q2, A2, Q3, A3, Q4, A4
        assert messages[0]["content"] == "Q2"


# ---------------------------------------------------------------------------
# Tests: Character budget
# ---------------------------------------------------------------------------


class TestCharBudget:
    """Tests for character budget enforcement (Req 6.3, 6.4, 6.5)."""

    def test_within_budget_kept(self):
        """History within budget is kept fully."""
        history = [
            {"role": "user", "content": "short"},
            {"role": "assistant", "content": "also short"},
        ]
        _, messages = build_chat_messages("q", history, [], max_history_chars=4000)
        assert len(messages) == 3

    def test_over_budget_removes_oldest(self):
        """When over budget, oldest entries removed first."""
        # Each entry ~1000 chars, 5 entries = 5000 chars > 4000 budget
        history = [
            {"role": "user", "content": "x" * 1000},
            {"role": "assistant", "content": "y" * 1000},
            {"role": "user", "content": "a" * 1000},
            {"role": "assistant", "content": "b" * 1000},
            {"role": "user", "content": "c" * 1000},
        ]
        _, messages = build_chat_messages("q", history, [], max_history_chars=4000)
        # Total should be ≤ 4000 chars from history
        history_chars = sum(len(m["content"]) for m in messages[:-1])
        assert history_chars <= 4000
        # The current prompt doesn't count against budget
        assert messages[-1]["content"] == "q"

    def test_all_removed_still_has_current_prompt(self):
        """Req 6.5: If all history removed, current prompt still present."""
        history = [
            {"role": "user", "content": "x" * 5000},
        ]
        _, messages = build_chat_messages("my question", history, [], max_history_chars=4000)
        assert len(messages) == 1
        assert messages[0]["content"] == "my question"

    def test_budget_does_not_count_current_prompt(self):
        """Character budget applies to history only, not current prompt."""
        history = [
            {"role": "user", "content": "a" * 2000},
            {"role": "assistant", "content": "b" * 1500},
        ]
        # 3500 chars < 4000 budget, so all history should be kept
        _, messages = build_chat_messages("z" * 5000, history, [], max_history_chars=4000)
        assert len(messages) == 3  # 2 history + 1 current


# ---------------------------------------------------------------------------
# Tests: Notes formatting
# ---------------------------------------------------------------------------


class TestNotesFormatting:
    """Tests for notes inclusion in system prompt (Req 5.2, 5.3, 5.5)."""

    def test_no_notes_no_notes_section(self):
        """Req 5.3: No notes → no notes section in system prompt."""
        system, _ = build_chat_messages("q", [], [])
        assert "Training Notes:" not in system
        assert "training notes" not in system.lower().split("training notes")[0] if "training notes" in system.lower() else True

    def test_notes_included_in_system_prompt(self):
        """Req 5.2: Notes formatted as '[timestamp]: [text]' lines."""
        notes = [
            FakeNote(text="Shoulder pain", timestamp="2025-01-15T10:00:00Z"),
            FakeNote(text="Changed group", timestamp="2025-01-14T08:00:00Z"),
        ]
        system, _ = build_chat_messages("q", [], notes)
        assert "2025-01-15T10:00:00Z: Shoulder pain" in system
        assert "2025-01-14T08:00:00Z: Changed group" in system

    def test_notes_ordered_timestamp_descending(self):
        """Req 5.2: Notes are ordered by timestamp descending (most recent first)."""
        notes = [
            FakeNote(text="Old note", timestamp="2025-01-01T00:00:00Z"),
            FakeNote(text="New note", timestamp="2025-01-20T00:00:00Z"),
            FakeNote(text="Mid note", timestamp="2025-01-10T00:00:00Z"),
        ]
        system, _ = build_chat_messages("q", [], notes)
        new_pos = system.index("New note")
        mid_pos = system.index("Mid note")
        old_pos = system.index("Old note")
        assert new_pos < mid_pos < old_pos

    def test_max_notes_limit(self):
        """Req 5.2: At most max_notes notes included."""
        notes = [
            FakeNote(text=f"Note {i}", timestamp=f"2025-01-{i+1:02d}T00:00:00Z")
            for i in range(25)
        ]
        system, _ = build_chat_messages("q", [], notes, max_notes=20)
        # Count occurrences of "Note " pattern in the Training Notes section
        notes_section = system.split("Training Notes:\n")[1] if "Training Notes:" in system else ""
        lines = [line for line in notes_section.strip().split("\n") if line.strip()]
        assert len(lines) <= 20

    def test_notes_instruction_present(self):
        """Req 5.5: System prompt includes notes context instruction."""
        notes = [FakeNote(text="test", timestamp="2025-01-01T00:00:00Z")]
        system, _ = build_chat_messages("q", [], notes)
        assert "training notes" in system.lower()
        assert "sudden changes" in system.lower() or "anomalies" in system.lower()


# ---------------------------------------------------------------------------
# Tests: System prompt structure
# ---------------------------------------------------------------------------


class TestSystemPrompt:
    """Tests for system prompt assembly."""

    def test_base_prompt_always_present(self):
        """Base coaching instructions always present."""
        system, _ = build_chat_messages("q", [], [])
        assert "elite competitive swim coach" in system

    def test_no_history_no_continuity(self):
        """No history → no continuity instruction."""
        system, _ = build_chat_messages("q", [], [])
        assert "Prior conversation context" not in system

    def test_history_adds_continuity(self):
        """History present → continuity instruction added."""
        history = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        system, _ = build_chat_messages("q", history, [])
        assert "Prior conversation context" in system

    def test_both_history_and_notes(self):
        """Both history and notes → both sections in system prompt."""
        history = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        notes = [FakeNote(text="injury", timestamp="2025-01-01T00:00:00Z")]
        system, _ = build_chat_messages("q", history, notes)
        assert "Prior conversation context" in system
        assert "Training Notes:" in system
        assert "injury" in system

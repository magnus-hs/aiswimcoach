"""Unit tests and property tests for prompt_assembler.build_chat_messages."""
from __future__ import annotations

import sys
import os
from dataclasses import dataclass

from hypothesis import given, settings, assume
from hypothesis import strategies as st

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
        assert "Prior conversation" in system
        assert "continuity" in system


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
        assert "swim coach" in system.lower()

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


# ---------------------------------------------------------------------------
# Property Tests
# ---------------------------------------------------------------------------

# Feature: ai-coach-context, Property 3: Prompt includes at most 10 most-recent exchanges
# **Validates: Requirements 1.4, 2.3**


# Strategy: generate a list of exchanges (each exchange is a pair of user + assistant messages)
# Use short content (10-50 chars) so the character budget (4000) is never the limiting factor.
_short_content = st.text(
    alphabet=st.characters(categories=("L", "N", "P", "Z")),
    min_size=10,
    max_size=50,
).filter(lambda s: s.strip())


def _exchange_strategy():
    """Generate a flat conversation_history list with paired user/assistant messages."""
    return st.integers(min_value=0, max_value=30).flatmap(
        lambda n: st.lists(
            st.tuples(_short_content, _short_content),
            min_size=n,
            max_size=n,
        ).map(
            lambda pairs: [
                msg
                for user_content, assistant_content in pairs
                for msg in [
                    {"role": "user", "content": user_content},
                    {"role": "assistant", "content": assistant_content},
                ]
            ]
        )
    )


class TestPropertyMaxExchanges:
    """Property 3: Prompt includes at most 10 most-recent exchanges."""

    @given(history=_exchange_strategy(), prompt=_short_content)
    @settings(max_examples=100)
    def test_property_prompt_includes_at_most_10_recent_exchanges(self, history, prompt):
        """For any history of N exchanges, output includes min(N, 10) exchanges
        and they are the most recent."""
        num_exchanges = len(history) // 2

        system, messages = build_chat_messages(
            current_prompt=prompt,
            conversation_history=history,
            notes=[],
            max_exchanges=10,
            max_history_chars=4000,
        )

        # The last message is always the current prompt
        assert messages[-1] == {"role": "user", "content": prompt}

        # History messages (everything except the final current prompt)
        history_messages = messages[:-1]

        # Number of exchanges in output
        output_exchanges = len(history_messages) // 2

        # Property: output includes min(N, 10) exchanges
        expected_exchanges = min(num_exchanges, 10)
        assert output_exchanges == expected_exchanges

        # Property: the included exchanges are the most recent ones
        # The original exchanges (from the input history)
        original_exchanges = [
            (history[i]["content"], history[i + 1]["content"])
            for i in range(0, len(history), 2)
        ]
        # The most recent `expected_exchanges` from the original
        expected_recent = original_exchanges[-expected_exchanges:] if expected_exchanges > 0 else []

        # The output exchanges
        output_exchange_pairs = [
            (history_messages[i]["content"], history_messages[i + 1]["content"])
            for i in range(0, len(history_messages), 2)
        ]

        assert output_exchange_pairs == expected_recent


# Feature: ai-coach-context, Property 4: Conversation history chronological ordering
# **Validates: Requirements 2.1, 2.2**


class TestPropertyChronologicalOrdering:
    """Property 4: Conversation history chronological ordering.

    For any valid history entries, assert messages array is chronological
    (oldest first) with current prompt last.
    """

    @given(
        num_exchanges=st.integers(min_value=0, max_value=15),
        prompt=_short_content,
    )
    @settings(max_examples=100)
    def test_property_conversation_history_chronological_ordering(self, num_exchanges, prompt):
        """Messages array preserves chronological order (oldest first)
        with the current prompt as the final message."""
        # Generate history with identifiable content (index in content)
        # so we can verify ordering is preserved.
        history = []
        for i in range(num_exchanges):
            history.append({"role": "user", "content": f"user_msg_{i}"})
            history.append({"role": "assistant", "content": f"asst_msg_{i}"})

        _, messages = build_chat_messages(
            current_prompt=prompt,
            conversation_history=history,
            notes=[],
            max_exchanges=10,
            max_history_chars=4000,
        )

        # The current prompt is always the final message
        assert messages[-1] == {"role": "user", "content": prompt}

        # History messages (everything before the current prompt)
        history_messages = messages[:-1]

        # If there are history messages, verify chronological order (oldest first)
        # Extract the indices from the identifiable content to check ordering
        if history_messages:
            indices = []
            for msg in history_messages:
                content = msg["content"]
                # Extract the index from "user_msg_N" or "asst_msg_N"
                if content.startswith("user_msg_"):
                    indices.append(int(content.split("_")[-1]))
                elif content.startswith("asst_msg_"):
                    indices.append(int(content.split("_")[-1]))

            # Indices should be non-decreasing (chronological order preserved)
            # Within an exchange, user and assistant share the same index
            for j in range(len(indices) - 1):
                assert indices[j] <= indices[j + 1], (
                    f"Messages not in chronological order: index {indices[j]} "
                    f"followed by {indices[j + 1]} at position {j}"
                )

        # Verify alternating user/assistant pattern in history messages
        for j in range(0, len(history_messages), 2):
            assert history_messages[j]["role"] == "user"
            if j + 1 < len(history_messages):
                assert history_messages[j + 1]["role"] == "assistant"


# ---------------------------------------------------------------------------
# Feature: ai-coach-context, Property 5: Malformed entries filtered
# ---------------------------------------------------------------------------


# Strategy: generate valid history entries (dict with non-empty role & content strings)
_valid_entry_strategy = st.fixed_dictionaries(
    {
        "role": st.sampled_from(["user", "assistant"]),
        "content": st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "P")),
            min_size=1,
            max_size=10,
        ),
    }
)

# Strategy: generate various kinds of malformed entries
_malformed_entry_strategy = st.one_of(
    # Not a dict at all
    st.integers(),
    st.none(),
    st.text(max_size=5),
    st.lists(st.integers(), max_size=2),
    # Dict missing "role"
    st.fixed_dictionaries({"content": st.text(min_size=1, max_size=5)}),
    # Dict missing "content"
    st.fixed_dictionaries({"role": st.text(min_size=1, max_size=5)}),
    # Dict with empty role
    st.fixed_dictionaries(
        {"role": st.just(""), "content": st.text(min_size=1, max_size=5)}
    ),
    # Dict with empty content
    st.fixed_dictionaries(
        {"role": st.sampled_from(["user", "assistant"]), "content": st.just("")}
    ),
    # Dict with whitespace-only role
    st.fixed_dictionaries(
        {
            "role": st.sampled_from(["   ", "\t", "\n"]),
            "content": st.text(min_size=1, max_size=5),
        }
    ),
    # Dict with whitespace-only content
    st.fixed_dictionaries(
        {
            "role": st.sampled_from(["user", "assistant"]),
            "content": st.sampled_from(["   ", "\t", "\n", "  \n  "]),
        }
    ),
    # Dict with non-string role
    st.fixed_dictionaries(
        {"role": st.integers(), "content": st.text(min_size=1, max_size=5)}
    ),
    # Dict with non-string content
    st.fixed_dictionaries(
        {"role": st.sampled_from(["user", "assistant"]), "content": st.integers()}
    ),
)


class TestPropertyMalformedEntriesFiltered:
    """Property 5: Malformed entries filtered.

    **Validates: Requirements 2.6**
    """

    @given(
        valid_entries=st.lists(
            _valid_entry_strategy, min_size=0, max_size=10
        ),
        malformed_entries=st.lists(
            _malformed_entry_strategy, min_size=0, max_size=10
        ),
        seed=st.randoms(use_true_random=False),
    )
    @settings(max_examples=100)
    def test_property_malformed_entries_filtered(
        self, valid_entries, malformed_entries, seed
    ):
        """For any mix of valid and malformed entries, output contains exactly
        valid entries and zero malformed entries.

        **Validates: Requirements 2.6**
        """
        # Interleave valid and malformed entries using a seeded random shuffle
        mixed = valid_entries + malformed_entries
        seed.shuffle(mixed)

        _, messages = build_chat_messages(
            "test prompt",
            mixed,
            [],
            max_exchanges=100,
            max_history_chars=100000,
            max_notes=0,
        )

        # The last message is always the current prompt
        assert messages[-1] == {"role": "user", "content": "test prompt"}

        # All history messages (everything except the last) must come from valid entries
        history_messages = messages[:-1]

        # The function groups into pairs, so it may not include an unpaired valid entry
        # at the end. But every included message MUST be from the valid set.
        for msg in history_messages:
            assert isinstance(msg, dict)
            assert "role" in msg and "content" in msg
            assert isinstance(msg["role"], str) and msg["role"].strip()
            assert isinstance(msg["content"], str) and msg["content"].strip()
            # Verify this message's content matches one of the valid entries
            assert any(
                v["role"] == msg["role"] and v["content"] == msg["content"]
                for v in valid_entries
            ), f"Message {msg} not found in valid entries"

        # No malformed entry should appear in output - verify by checking
        # that all output messages have valid structure (non-empty string role & content)
        for msg in history_messages:
            assert isinstance(msg.get("role"), str) and len(msg["role"].strip()) > 0
            assert isinstance(msg.get("content"), str) and len(msg["content"].strip()) > 0

        # Count: history messages should not exceed valid entry count
        # (may be less since pairing drops trailing singles)
        assert len(history_messages) <= len(valid_entries)


# ---------------------------------------------------------------------------
# Feature: ai-coach-context, Property 10: Notes in prompt limited and formatted
# **Validates: Requirements 5.2**
# ---------------------------------------------------------------------------


# Strategy: generate a list of FakeNote objects with ISO 8601 timestamps in descending order
def _notes_strategy():
    """Generate 0 to 200 FakeNote objects ordered by timestamp descending."""
    note_text = st.text(
        alphabet=st.characters(categories=("L", "N", "P", "Z")),
        min_size=1,
        max_size=100,
    ).filter(lambda s: s.strip())

    return st.integers(min_value=0, max_value=200).flatmap(
        lambda n: st.lists(
            st.tuples(
                note_text,
                st.integers(min_value=1, max_value=1000000),
            ),
            min_size=n,
            max_size=n,
        ).map(
            lambda pairs: [
                FakeNote(
                    text=text,
                    timestamp=f"2025-01-{(idx // 24) + 1:02d}T{idx % 24:02d}:00:00Z",
                )
                for idx, (text, _) in enumerate(pairs)
            ]
        )
    )


class TestPropertyNotesLimitedAndFormatted:
    """Property 10: Notes in prompt limited and formatted."""

    @given(notes=_notes_strategy(), prompt=_short_content)
    @settings(max_examples=100)
    def test_property_notes_in_prompt_limited_and_formatted(self, notes, prompt):
        """For any set of 0–200 notes, assert prompt includes ≤ 20 notes
        formatted as '[timestamp]: [text]' per line, ordered timestamp desc."""
        system, messages = build_chat_messages(
            current_prompt=prompt,
            conversation_history=[],
            notes=notes,
            max_notes=20,
        )

        # Extract note lines from the system prompt
        # Each included note is formatted as "{timestamp}: {text}"
        included_notes = []
        for note in notes[:20]:
            expected_line = f"{note.timestamp}: {note.text}"
            if expected_line in system:
                included_notes.append(note)

        # Property 1: At most 20 notes included
        assert len(included_notes) <= 20

        # Property 2: Exactly min(len(notes), 20) notes are included
        expected_count = min(len(notes), 20)
        assert len(included_notes) == expected_count

        # Property 3: Each included note is formatted as "[timestamp]: [text]"
        for note in notes[:20]:
            expected_line = f"{note.timestamp}: {note.text}"
            assert expected_line in system

        # Property 4: Notes appear in the order they were provided (timestamp desc)
        if len(included_notes) >= 2:
            for i in range(len(included_notes) - 1):
                pos_current = system.index(
                    f"{included_notes[i].timestamp}: {included_notes[i].text}"
                )
                pos_next = system.index(
                    f"{included_notes[i + 1].timestamp}: {included_notes[i + 1].text}"
                )
                assert pos_current < pos_next, (
                    f"Note at index {i} should appear before note at index {i+1} "
                    f"(timestamp descending order)"
                )

        # Property 5: Notes beyond the limit of 20 are NOT in the prompt
        for note in notes[20:]:
            excluded_line = f"{note.timestamp}: {note.text}"
            assert excluded_line not in system


# ---------------------------------------------------------------------------
# Feature: ai-coach-context, Property 11: Character-budget truncation
# **Validates: Requirements 6.3, 6.4**
# ---------------------------------------------------------------------------


# Strategy: generate exchanges with varied content lengths (some short, some long)
# to test both under-budget and over-budget scenarios.
# Use st.integers for length + a fixed char to avoid slow text generation.
_varied_content_budget = st.one_of(
    # Short content (10-50 chars) - likely under budget
    st.integers(min_value=10, max_value=50).map(lambda n: "a" * n),
    # Medium content (200-800 chars) - may push over budget
    st.integers(min_value=200, max_value=800).map(lambda n: "b" * n),
    # Long content (1000-2000 chars) - likely over budget with a few entries
    st.integers(min_value=1000, max_value=2000).map(lambda n: "c" * n),
)


@st.composite
def _varied_exchange_strategy_budget(draw):
    """Generate a flat conversation_history list with varied content lengths."""
    n = draw(st.integers(min_value=0, max_value=15))
    history = []
    for _ in range(n):
        user_content = draw(_varied_content_budget)
        asst_content = draw(_varied_content_budget)
        history.append({"role": "user", "content": user_content})
        history.append({"role": "assistant", "content": asst_content})
    return history


class TestPropertyCharBudgetTruncation:
    """Property 11: Character-budget truncation.

    For any history, assert total chars of included exchanges <= 4000 after
    truncation, and oldest entries removed first.

    **Validates: Requirements 6.3, 6.4**
    """

    @given(
        history=_varied_exchange_strategy_budget(),
        prompt=st.integers(min_value=1, max_value=100).map(lambda n: "q" * n),
    )
    @settings(max_examples=100)
    def test_property_character_budget_truncation(self, history, prompt):
        """For any history, total chars of included exchanges <= 4000 after
        truncation, and oldest entries are removed first."""
        max_budget = 4000

        _, messages = build_chat_messages(
            current_prompt=prompt,
            conversation_history=history,
            notes=[],
            max_exchanges=10,
            max_history_chars=max_budget,
        )

        # The current prompt is always the last message
        assert messages[-1] == {"role": "user", "content": prompt}

        # History messages = everything except the last message (current prompt)
        history_messages = messages[:-1]

        # Property 1: Total character count of history exchanges <= max_budget
        total_chars = sum(len(m["content"]) for m in history_messages)
        assert total_chars <= max_budget, (
            f"History chars {total_chars} exceeds budget {max_budget}"
        )

        # Property 2: Oldest entries removed first
        # After exchange-count truncation (max 10), the function keeps the most
        # recent exchanges. The character budget then removes from the front
        # (oldest remaining) until within budget.
        #
        # To verify oldest-first removal: the included exchanges must be a
        # contiguous suffix of the post-exchange-count-truncated history.
        # i.e., if we had exchanges [E0, E1, ..., En] after count truncation,
        # the included ones must be [Ek, Ek+1, ..., En] for some k.

        # Reconstruct what the exchange-count-truncated history looks like
        valid_history = [
            entry for entry in history
            if isinstance(entry, dict)
            and isinstance(entry.get("role"), str)
            and isinstance(entry.get("content"), str)
            and entry["role"].strip()
            and entry["content"].strip()
        ]

        # Group into exchanges
        exchanges_input = []
        i = 0
        while i + 1 < len(valid_history):
            exchanges_input.append(
                (valid_history[i]["content"], valid_history[i + 1]["content"])
            )
            i += 2

        # Apply exchange count limit (keep most recent 10)
        if len(exchanges_input) > 10:
            exchanges_input = exchanges_input[-10:]

        # Now verify included history is a contiguous suffix
        output_exchanges = []
        j = 0
        while j + 1 < len(history_messages):
            output_exchanges.append(
                (history_messages[j]["content"], history_messages[j + 1]["content"])
            )
            j += 2

        if output_exchanges:
            # The output must be the tail of exchanges_input
            n_output = len(output_exchanges)
            expected_suffix = exchanges_input[-n_output:]
            assert output_exchanges == expected_suffix, (
                "Included exchanges are not a contiguous suffix of the "
                "exchange-count-truncated history (oldest-first removal violated)"
            )

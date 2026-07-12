"""Prompt assembler for AI Swim Coach context-aware conversations.

Builds the system prompt and messages array for Bedrock invocation,
incorporating conversation history and user training notes.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DrillContext:
    """Aggregated drill information for AI coaching context."""

    drill_count: int
    drill_distance_m: float
    drill_time_seconds: float
    drill_position: str  # "beginning", "middle", "end", or "throughout"


def compute_drill_context(
    splits: list[dict], pool_length_m: float
) -> DrillContext | None:
    """Compute drill summary from session splits.

    Args:
        splits: List of split dicts with 'stroke' and 'time_seconds' fields.
        pool_length_m: Pool length in meters.

    Returns:
        DrillContext if drills exist, None otherwise.
    """
    drill_indices = [
        i for i, s in enumerate(splits) if s.get("stroke") == "drill"
    ]
    if not drill_indices:
        return None

    drill_count = len(drill_indices)
    drill_distance = drill_count * pool_length_m
    drill_time = sum(
        splits[i].get("time_seconds", 0) for i in drill_indices
    )

    # Determine position
    total = len(splits)
    if total <= 1:
        position = "throughout"
    else:
        avg_position = sum(drill_indices) / len(drill_indices)
        relative = avg_position / (total - 1)
        if relative <= 0.33:
            position = "beginning"
        elif relative >= 0.67:
            position = "end"
        elif all(
            total * 0.33 <= i < total * 0.67 for i in drill_indices
        ):
            position = "middle"
        else:
            position = "throughout"

    return DrillContext(
        drill_count=drill_count,
        drill_distance_m=drill_distance,
        drill_time_seconds=drill_time,
        drill_position=position,
    )


def format_drill_context(ctx: DrillContext) -> str:
    """Format drill context into a readable string for the coaching prompt."""
    minutes = int(ctx.drill_time_seconds // 60)
    seconds = int(ctx.drill_time_seconds % 60)
    if minutes > 0:
        time_str = f"{minutes}m {seconds:02d}s"
    else:
        time_str = f"{seconds}s"
    return (
        f"Drill work: {ctx.drill_count} drill lengths "
        f"({ctx.drill_distance_m:.0f}m, {time_str}), "
        f"positioned at the {ctx.drill_position} of the session."
    )


def _get_note_field(note, field: str) -> str:
    """Access a note field via attribute or dict access."""
    if hasattr(note, field):
        return getattr(note, field, "")
    if isinstance(note, dict):
        return note.get(field, "")
    return ""


def build_chat_messages(
    current_prompt: str,
    conversation_history: list[dict],
    notes: list,
    max_exchanges: int = 10,
    max_history_chars: int = 4000,
    max_notes: int = 20,
    session_splits: list[dict] | None = None,
    pool_length_m: float = 25.0,
) -> tuple[str, list[dict]]:
    """
    Assemble a system prompt and messages array for Bedrock invocation.

    Args:
        current_prompt: The user's current question/prompt.
        conversation_history: List of {"role": "user"|"assistant", "content": "..."} dicts.
        notes: List of TrainingNote objects (or dicts with text + timestamp).
        max_exchanges: Maximum number of exchanges (user+assistant pairs) to include.
        max_history_chars: Maximum total characters for all history content.
        max_notes: Maximum number of notes to include in the system prompt.
        session_splits: Optional list of split dicts with 'stroke' and 'time_seconds' fields.
        pool_length_m: Pool length in meters (default 25.0).

    Returns:
        A tuple of (system_prompt, messages) where messages is the array
        ready for Bedrock invocation.
    """
    # 1. Filter malformed history entries
    valid_history = []
    for entry in conversation_history:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role")
        content = entry.get("content")
        if (
            isinstance(role, str)
            and isinstance(content, str)
            and role.strip()
            and content.strip()
        ):
            valid_history.append(entry)

    # 2. Group into exchanges (pairs of consecutive user + assistant messages)
    # 3. History arrives in chronological order (oldest first)
    exchanges = []
    i = 0
    while i + 1 < len(valid_history):
        exchanges.append((valid_history[i], valid_history[i + 1]))
        i += 2

    # 4. If more than max_exchanges, keep only the most recent
    if len(exchanges) > max_exchanges:
        exchanges = exchanges[-max_exchanges:]

    # 5. Apply character budget
    while exchanges:
        total_chars = sum(
            len(ex[0]["content"]) + len(ex[1]["content"]) for ex in exchanges
        )
        if total_chars <= max_history_chars:
            break
        exchanges.pop(0)  # Remove oldest exchange

    # 6. Format notes (up to max_notes, most recent first)
    formatted_notes_lines = []
    for note in notes[:max_notes]:
        timestamp = _get_note_field(note, "timestamp")
        text = _get_note_field(note, "text")
        if timestamp or text:
            formatted_notes_lines.append(f"{timestamp}: {text}")

    # 7. Build system prompt
    system_parts = [
        "You are an expert AI swim coach. Provide personalized, actionable "
        "coaching advice based on the swimmer's data, training history, and goals. "
        "Be conversational and friendly — like a knowledgeable coach chatting poolside. "
        "Keep answers concise (2-4 short paragraphs max). Use plain language, not bullet points or numbered lists. "
        "Address the swimmer directly as 'you'. Ask follow-up questions when it helps.",
        "IMPORTANT: You must only discuss topics related to swimming, swim training, "
        "technique, fitness, recovery, nutrition for swimmers, race preparation, "
        "pool sessions, open water, and the user's swim data. If the user asks about "
        "anything unrelated to swimming or their training, politely decline and remind "
        "them you're here to help with their swimming.",
    ]

    if formatted_notes_lines:
        notes_block = "\n".join(formatted_notes_lines)
        system_parts.append(
            "The user has provided personal training notes. Use these to explain "
            "anomalies or context changes:\n" + notes_block
        )

    if session_splits is not None:
        drill_ctx = compute_drill_context(session_splits, pool_length_m)
        if drill_ctx is not None:
            system_parts.append(format_drill_context(drill_ctx))

    if exchanges:
        system_parts.append(
            "Prior conversation history is included for continuity. "
            "Reference previous answers when relevant."
        )

    system_prompt = "\n\n".join(system_parts)

    # 8. Build messages array: history entries + current prompt
    messages = []
    for ex in exchanges:
        messages.append({"role": ex[0]["role"], "content": ex[0]["content"]})
        messages.append({"role": ex[1]["role"], "content": ex[1]["content"]})

    messages.append({"role": "user", "content": current_prompt})

    # 9. Return
    return system_prompt, messages

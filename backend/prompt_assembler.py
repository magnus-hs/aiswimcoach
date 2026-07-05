"""Prompt assembler for AI Swim Coach context-aware conversations.

Builds the system prompt and messages array for Bedrock invocation,
incorporating conversation history and user training notes.
"""


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
        "coaching advice based on the swimmer's data, training history, and goals."
    ]

    if formatted_notes_lines:
        notes_block = "\n".join(formatted_notes_lines)
        system_parts.append(
            "The user has provided personal training notes. Use these to explain "
            "anomalies or context changes:\n" + notes_block
        )

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

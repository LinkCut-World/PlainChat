"""Storage layer for PlainChat conversation history."""

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import Conversation, Message, SearchResult


_HISTORY_FILE_PATH: Optional[Path] = None


def set_history_file_path(path: str | Path) -> None:
    """Configure where conversation history is stored."""
    global _HISTORY_FILE_PATH
    _HISTORY_FILE_PATH = Path(path).expanduser()


def _get_history_file_path() -> Path:
    if _HISTORY_FILE_PATH is None:
        raise RuntimeError(
            "History file path is not configured. Host app must call "
            "set_history_file_path(...) before using storage."
        )
    _HISTORY_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return _HISTORY_FILE_PATH


def _load_raw_data() -> dict:
    file_path = _get_history_file_path()
    if not file_path.exists():
        return {"conversations": []}

    try:
        return json.loads(file_path.read_text(encoding="utf-8")) or {"conversations": []}
    except (json.JSONDecodeError, OSError):
        return {"conversations": []}


def _save_raw_data(data: dict) -> None:
    file_path = _get_history_file_path()
    file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_all_conversations() -> List[Conversation]:
    raw_data = _load_raw_data()
    conversations = [Conversation.from_dict(c) for c in raw_data.get("conversations", [])]
    return sorted(conversations, key=lambda c: c.updated_at, reverse=True)


def get_conversation(conv_id: str) -> Optional[Conversation]:
    raw_data = _load_raw_data()
    for c in raw_data.get("conversations", []):
        if c.get("id") == conv_id:
            return Conversation.from_dict(c)
    return None


def create_conversation(extras: Optional[Dict[str, Any]] = None) -> Conversation:
    now = time.time()
    conversation = Conversation(
        id=str(uuid.uuid4()),
        created_at=now,
        updated_at=now,
        extras=dict(extras or {}),
        messages=[],
    )

    raw_data = _load_raw_data()
    raw_data["conversations"].insert(0, conversation.to_dict())
    _save_raw_data(raw_data)
    return conversation


def add_message(conv_id: str, role: str, content: str) -> Optional[Message]:
    raw_data = _load_raw_data()
    conversations = raw_data.get("conversations", [])

    for i, c in enumerate(conversations):
        if c.get("id") == conv_id:
            now = time.time()
            message = Message(
                id=str(uuid.uuid4()),
                conversation_id=conv_id,
                role=role,
                content=content,
                timestamp=now,
            )

            c.setdefault("messages", []).append(message.to_dict())
            c["updated_at"] = now

            conversations.pop(i)
            conversations.insert(0, c)
            _save_raw_data(raw_data)
            return message

    return None


def delete_conversation(conv_id: str) -> bool:
    raw_data = _load_raw_data()
    conversations = raw_data.get("conversations", [])

    for i, c in enumerate(conversations):
        if c.get("id") == conv_id:
            conversations.pop(i)
            raw_data["conversations"] = conversations
            _save_raw_data(raw_data)
            return True

    return False


def search_conversations(query: str) -> List[SearchResult]:
    raw_data = _load_raw_data()
    conversations = [Conversation.from_dict(c) for c in raw_data.get("conversations", [])]

    results: List[SearchResult] = []
    query_lower = query.strip().lower() if query else ""

    for conv in conversations:
        title = conv.get_first_user_message() or "(No question)"

        match_content: Optional[str] = None

        if not query_lower:
            match_content = conv.get_first_assistant_message()
            if match_content:
                match_content = match_content[:50] + "..." if len(match_content) > 50 else match_content
        else:
            for msg in conv.messages:
                content_lower = msg.content.lower()
                pos = content_lower.find(query_lower)
                if pos != -1:
                    start = max(0, pos - 30)
                    end = min(len(msg.content), pos + len(query) + 30)
                    match_content = msg.content[start:end]
                    if start > 0:
                        match_content = "..." + match_content
                    if end < len(msg.content):
                        match_content += "..."
                    break

            if not match_content and conv.extras:
                searchable_extras = json.dumps(conv.extras, ensure_ascii=False).lower()
                if query_lower in searchable_extras:
                    prompt_text = conv.extras.get("prefill_query")
                    if isinstance(prompt_text, str) and prompt_text.strip():
                        match_content = f"Prefill: {prompt_text}"
                    else:
                        match_content = f"Extras: {json.dumps(conv.extras, ensure_ascii=False)}"

        if not query_lower or match_content:
            results.append(
                SearchResult(
                    conversation_id=conv.id,
                    title=title,
                    match_content=match_content,
                    updated_at=conv.updated_at,
                    extras=conv.extras,
                )
            )

    results.sort(key=lambda r: r.updated_at, reverse=True)
    return results


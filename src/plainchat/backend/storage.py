"""Storage layer for PlainChat conversation history."""

import json
import os
import time
import uuid
from pathlib import Path
from typing import List, Optional

from .models import Conversation, Message, SearchResult


_HISTORY_FILE = "history.json"


def _default_data_dir() -> Path:
    """
    Default data directory.

    - If host app sets SHANBEI_DATA_DIR, we follow it (for compatibility with 扇贝).
    - Otherwise, we default to `<cwd>/data`, so the app is portable as a standalone CLI.
    """
    env = os.environ.get("SHANBEI_DATA_DIR")
    if env:
        return Path(env)
    return Path.cwd() / "data"


def _get_history_file_path() -> Path:
    data_dir = _default_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / _HISTORY_FILE


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


def create_conversation(word: Optional[str] = None) -> Conversation:
    now = time.time()
    conversation = Conversation(
        id=str(uuid.uuid4()),
        word=word,
        created_at=now,
        updated_at=now,
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


def search_conversations(query: str, limit: int = 50) -> List[SearchResult]:
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

            if not match_content and conv.word and query_lower in conv.word.lower():
                match_content = f"Word: {conv.word}"

        if not query_lower or match_content:
            results.append(
                SearchResult(
                    conversation_id=conv.id,
                    word=conv.word,
                    title=title,
                    match_content=match_content,
                    updated_at=conv.updated_at,
                )
            )

    results.sort(key=lambda r: r.updated_at, reverse=True)
    return results[:limit]


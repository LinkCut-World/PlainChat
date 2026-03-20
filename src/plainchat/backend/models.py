"""Data models for conversation storage."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Message:
    """Represents a single message in a conversation."""

    id: str
    conversation_id: str
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: float

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        return cls(
            id=data["id"],
            conversation_id=data["conversation_id"],
            role=data["role"],
            content=data["content"],
            timestamp=data["timestamp"],
        )


@dataclass
class Conversation:
    """Represents a conversation session."""

    id: str
    created_at: float
    updated_at: float
    extras: Dict[str, Any] = field(default_factory=dict)
    messages: List[Message] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "extras": self.extras,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": [msg.to_dict() for msg in self.messages],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Conversation":
        extras = data.get("extras")
        if not isinstance(extras, dict):
            extras = {}
        if "word" in data and data.get("word") is not None:
            extras.setdefault("word", data.get("word"))

        return cls(
            id=data["id"],
            extras=extras,
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            messages=[Message.from_dict(m) for m in data.get("messages", [])],
        )

    def get_first_user_message(self) -> Optional[str]:
        for msg in self.messages:
            if msg.role == "user":
                return msg.content
        return None

    def get_first_assistant_message(self) -> Optional[str]:
        for msg in self.messages:
            if msg.role == "assistant":
                return msg.content
        return None


@dataclass
class SearchResult:
    """Represents a search result for conversation history."""

    conversation_id: str
    title: str
    match_content: Optional[str]
    updated_at: float
    extras: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "conversation_id": self.conversation_id,
            "extras": self.extras,
            "title": self.title,
            "match_content": self.match_content,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SearchResult":
        return cls(
            conversation_id=data["conversation_id"],
            extras=data.get("extras") if isinstance(data.get("extras"), dict) else {},
            title=data["title"],
            match_content=data.get("match_content"),
            updated_at=data["updated_at"],
        )


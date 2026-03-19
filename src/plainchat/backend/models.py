"""Data models for conversation storage."""

from dataclasses import dataclass, field
from typing import List, Optional


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
    word: Optional[str]  # Optional contextual word (can be used by host apps)
    created_at: float
    updated_at: float
    messages: List[Message] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "word": self.word,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": [msg.to_dict() for msg in self.messages],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Conversation":
        return cls(
            id=data["id"],
            word=data.get("word"),
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
    word: Optional[str]
    title: str
    match_content: Optional[str]
    updated_at: float

    def to_dict(self) -> dict:
        return {
            "conversation_id": self.conversation_id,
            "word": self.word,
            "title": self.title,
            "match_content": self.match_content,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SearchResult":
        return cls(
            conversation_id=data["conversation_id"],
            word=data.get("word"),
            title=data["title"],
            match_content=data.get("match_content"),
            updated_at=data["updated_at"],
        )


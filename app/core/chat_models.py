"""Chat data model shared by saved-mode and offline-mode sessions."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum


class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatSessionStatus(str, Enum):
    ACTIVE = "Active"
    ARCHIVED = "Archived"


@dataclass
class ChatMessage:
    role: ChatRole
    content: str
    created_at: float = field(default_factory=time.time)


@dataclass
class ChatSession:
    """A saved-mode conversation. Offline-mode conversations never become a
    ChatSession and are never persisted -- see offline_session.py.
    """

    id: str
    title: str
    model_id: str
    status: ChatSessionStatus = ChatSessionStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    messages: list[ChatMessage] = field(default_factory=list)

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())

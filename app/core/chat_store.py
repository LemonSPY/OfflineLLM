"""SQLite-backed persistence for saved-mode chats.

This is intentionally never used by offline-mode sessions (see
offline_session.py) -- saved-mode is the only mode where conversation
content is written to disk.
"""

from __future__ import annotations

import os
import sqlite3
import time

from .chat_models import ChatMessage, ChatRole, ChatSession, ChatSessionStatus

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    model_id TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_messages_session_id ON messages(session_id);
"""


class SqliteChatStore:
    def __init__(self, database_path: str):
        os.makedirs(os.path.dirname(database_path), exist_ok=True)
        self._conn = sqlite3.connect(database_path, check_same_thread=False)
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def create_session(self, title: str, model_id: str) -> ChatSession:
        session = ChatSession(id=ChatSession.new_id(), title=title, model_id=model_id)
        self._conn.execute(
            "INSERT INTO sessions (id, title, model_id, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (session.id, session.title, session.model_id, session.status.value,
             session.created_at, session.updated_at),
        )
        self._conn.commit()
        return session

    def list_sessions(self, include_archived: bool) -> list[ChatSession]:
        if include_archived:
            rows = self._conn.execute(
                "SELECT id, title, model_id, status, created_at, updated_at "
                "FROM sessions ORDER BY updated_at DESC"
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT id, title, model_id, status, created_at, updated_at "
                "FROM sessions WHERE status = ? ORDER BY updated_at DESC",
                (ChatSessionStatus.ACTIVE.value,),
            ).fetchall()
        return [self._row_to_session(row) for row in rows]

    def get_session(self, session_id: str) -> ChatSession | None:
        row = self._conn.execute(
            "SELECT id, title, model_id, status, created_at, updated_at "
            "FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            return None

        session = self._row_to_session(row)
        for role, content, created_at in self._conn.execute(
            "SELECT role, content, created_at FROM messages "
            "WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ):
            session.messages.append(ChatMessage(role=ChatRole(role), content=content, created_at=created_at))
        return session

    def append_message(self, session_id: str, message: ChatMessage) -> None:
        self._conn.execute(
            "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, message.role.value, message.content, message.created_at),
        )
        self._conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (time.time(), session_id),
        )
        self._conn.commit()

    def rename_session(self, session_id: str, new_title: str) -> None:
        self._conn.execute("UPDATE sessions SET title = ? WHERE id = ?", (new_title, session_id))
        self._conn.commit()

    def set_archived(self, session_id: str, archived: bool) -> None:
        status = ChatSessionStatus.ARCHIVED if archived else ChatSessionStatus.ACTIVE
        self._conn.execute("UPDATE sessions SET status = ? WHERE id = ?", (status.value, session_id))
        self._conn.commit()

    def delete_session(self, session_id: str) -> None:
        self._conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        self._conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    @staticmethod
    def _row_to_session(row) -> ChatSession:
        session_id, title, model_id, status, created_at, updated_at = row
        return ChatSession(
            id=session_id,
            title=title,
            model_id=model_id,
            status=ChatSessionStatus(status),
            created_at=created_at,
            updated_at=updated_at,
        )

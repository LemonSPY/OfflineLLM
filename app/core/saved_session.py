"""Drives a saved-mode chat: every user/assistant message is appended to the
SqliteChatStore as it's produced, so the conversation survives app restarts
and shows up in the archive/delete list.
"""

from __future__ import annotations

from typing import Iterator

from . import chat_engine
from .chat_models import ChatMessage, ChatRole, ChatSession
from .chat_store import SqliteChatStore
from .llama_server import LlamaServerProcess


class SavedSessionEngine:
    def __init__(self, store: SqliteChatStore, server: LlamaServerProcess, session: ChatSession):
        self._store = store
        self._server = server
        self.session = session

    def send(self, user_message: str) -> Iterator[str]:
        user_chat_message = ChatMessage(role=ChatRole.USER, content=user_message)
        self.session.messages.append(user_chat_message)
        self._store.append_message(self.session.id, user_chat_message)

        # Stream against history that ends on the user's turn only - an empty
        # trailing assistant message here would get formatted into the prompt
        # by the model's chat template as a *closed* empty turn, confusing
        # the model into generating an incoherent new turn instead of a
        # continuation. The real assistant message is appended only once we
        # have its content.
        reply = ""
        for chunk in chat_engine.stream_reply(self._server, self.session.messages):
            reply += chunk
            yield chunk

        assistant_message = ChatMessage(role=ChatRole.ASSISTANT, content=reply)
        self.session.messages.append(assistant_message)
        self._store.append_message(self.session.id, assistant_message)

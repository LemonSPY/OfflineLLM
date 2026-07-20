"""An ephemeral chat session: messages live only in this object's memory for
the lifetime of the session.

Nothing here is ever handed to SqliteChatStore, written to a file, or
logged. When the session ends, call close() -- the backing llama-server
process is killed and, once this object is released, there is nothing left
on disk or in a database that could reveal the conversation happened.
"""

from __future__ import annotations

from typing import Iterator

from . import chat_engine
from .chat_models import ChatMessage, ChatRole
from .llama_server import LlamaServerProcess, ServerLifecycleKind
from .model_manager import ModelInfo


class OfflineSessionEngine:
    def __init__(self, llama_server_exe_path: str, model: ModelInfo):
        self.messages: list[ChatMessage] = []
        self._server = LlamaServerProcess(llama_server_exe_path, model, ServerLifecycleKind.OFFLINE)

    def start(self) -> None:
        self._server.start()

    def send(self, user_message: str) -> Iterator[str]:
        self.messages.append(ChatMessage(role=ChatRole.USER, content=user_message))

        # Stream against history that ends on the user's turn only - an empty
        # trailing assistant message here would get formatted into the prompt
        # by the model's chat template as a *closed* empty turn, confusing
        # the model into generating an incoherent new turn instead of a
        # continuation. The real assistant message is appended only once we
        # have its content.
        reply = ""
        for chunk in chat_engine.stream_reply(self._server, self.messages):
            reply += chunk
            yield chunk

        self.messages.append(ChatMessage(role=ChatRole.ASSISTANT, content=reply))

    def close(self) -> None:
        """Ends the session: kills the offline llama-server process and
        clears the in-memory transcript. After this returns, no artifact of
        the conversation remains anywhere.
        """
        self._server.stop()
        self.messages.clear()

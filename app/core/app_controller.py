"""Ties the storage/engine pieces together behind a small, UI-framework-
agnostic API. All network/process calls here are synchronous and blocking --
the UI layer is responsible for running them off the main thread.
"""

from __future__ import annotations

import enum
from typing import Callable, Iterator

from . import app_paths
from .chat_models import ChatMessage, ChatSession
from .chat_store import SqliteChatStore
from .llama_server import LlamaServerProcess, ServerLifecycleKind
from .model_download import DownloadProgress, ModelDownloadService
from .model_manager import ModelInfo, ModelManager
from .offline_session import OfflineSessionEngine
from .saved_session import SavedSessionEngine


class ChatMode(enum.Enum):
    NONE = "none"
    SAVED = "saved"
    OFFLINE = "offline"


class AppController:
    def __init__(self):
        self.chat_store = SqliteChatStore(app_paths.CHAT_DATABASE_PATH)
        self.model_manager = ModelManager(app_paths.MODELS_DIRECTORY)
        self.model_download_service = ModelDownloadService(app_paths.MODELS_DIRECTORY)

        self.mode = ChatMode.NONE
        self.active_saved_session_id: str | None = None

        self._shared_saved_server: LlamaServerProcess | None = None
        self._saved_engine: SavedSessionEngine | None = None
        self._offline_engine: OfflineSessionEngine | None = None

    # -- Models -----------------------------------------------------------

    def list_available_models(self) -> list[ModelInfo]:
        return self.model_manager.list_available_models()

    def download_model(
        self,
        source_url: str,
        file_name: str,
        on_progress: Callable[[DownloadProgress], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> str:
        return self.model_download_service.download(source_url, file_name, on_progress, should_cancel)

    # -- Saved sessions -----------------------------------------------------

    def list_saved_sessions(self, include_archived: bool) -> list[ChatSession]:
        return self.chat_store.list_sessions(include_archived)

    def start_new_saved_chat(self, model: ModelInfo) -> ChatSession:
        session = self.chat_store.create_session("New chat", model.id)
        self.open_saved_chat(session.id)
        return session

    def open_saved_chat(self, session_id: str) -> ChatSession:
        self._close_offline_session()

        session = self.chat_store.get_session(session_id)
        if session is None:
            raise ValueError("Session not found.")

        model = self.model_manager.find_by_id(session.model_id)
        if model is None:
            raise ValueError(f"Model '{session.model_id}' is no longer available.")

        self._ensure_shared_saved_server(model)
        self._saved_engine = SavedSessionEngine(self.chat_store, self._shared_saved_server, session)
        self.active_saved_session_id = session_id
        self.mode = ChatMode.SAVED
        return session

    def archive_session(self, session_id: str, archived: bool) -> None:
        self.chat_store.set_archived(session_id, archived)

    def delete_session(self, session_id: str) -> None:
        if self.active_saved_session_id == session_id:
            self.close_current_chat()
        self.chat_store.delete_session(session_id)

    # -- Offline sessions -----------------------------------------------------

    def start_new_offline_chat(self, model: ModelInfo) -> None:
        self._close_offline_session()
        engine = OfflineSessionEngine(app_paths.LLAMA_SERVER_EXE_PATH, model)
        engine.start()
        self._offline_engine = engine
        self.active_saved_session_id = None
        self.mode = ChatMode.OFFLINE

    # -- Messaging -----------------------------------------------------

    def send_message(self, text: str) -> Iterator[str]:
        if self.mode is ChatMode.OFFLINE and self._offline_engine is not None:
            yield from self._offline_engine.send(text)
        elif self.mode is ChatMode.SAVED and self._saved_engine is not None:
            yield from self._saved_engine.send(text)

    # -- Lifecycle -----------------------------------------------------

    def close_current_chat(self) -> None:
        """Leaving an offline chat tears down its server process and
        discards its transcript immediately -- that's the entire point of
        offline mode.
        """
        self._close_offline_session()
        self._saved_engine = None
        self.active_saved_session_id = None
        self.mode = ChatMode.NONE

    def shutdown(self) -> None:
        self._close_offline_session()
        if self._shared_saved_server is not None:
            self._shared_saved_server.stop()
            self._shared_saved_server = None
        self.chat_store.close()

    def _close_offline_session(self) -> None:
        if self._offline_engine is not None:
            self._offline_engine.close()
            self._offline_engine = None

    def _ensure_shared_saved_server(self, model: ModelInfo) -> None:
        if self._shared_saved_server is not None and self._shared_saved_server.model.id == model.id:
            return

        if self._shared_saved_server is not None:
            self._shared_saved_server.stop()

        self._shared_saved_server = LlamaServerProcess(
            app_paths.LLAMA_SERVER_EXE_PATH, model, ServerLifecycleKind.SAVED
        )
        self._shared_saved_server.start()

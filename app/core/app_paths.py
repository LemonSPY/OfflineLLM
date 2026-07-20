"""Central place for the on-disk locations saved-mode data lives in.

Offline-mode sessions never use any of these -- that's the whole point of
offline mode (see offline_session.py).
"""

import os
import sys


def _base_dir() -> str:
    local_app_data = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(local_app_data, "OfflineLlm")


BASE_DIR = _base_dir()
CHAT_DATABASE_PATH = os.path.join(BASE_DIR, "chats.db")
MODELS_DIRECTORY = os.path.join(BASE_DIR, "models")


def _app_root() -> str:
    """Directory containing the running app (frozen exe or app/main.py)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


LLAMA_SERVER_EXE_PATH = os.path.join(_app_root(), "Engine", "llama-server.exe")

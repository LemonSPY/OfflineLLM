"""Downloads a .gguf model file into the models directory ModelManager scans.

Writes to a ".partial" file and only renames it to the final name once the
download completes successfully, so a cancelled/failed download never shows
up as a selectable (but truncated/corrupt) model.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Optional

import requests


@dataclass(frozen=True)
class DownloadProgress:
    bytes_received: int
    total_bytes: Optional[int]

    @property
    def fraction_complete(self) -> float | None:
        if self.total_bytes:
            return self.bytes_received / self.total_bytes
        return None


class ModelDownloadService:
    def __init__(self, models_directory: str):
        self._models_directory = models_directory
        os.makedirs(self._models_directory, exist_ok=True)

    def download(
        self,
        source_url: str,
        file_name: str,
        on_progress: Callable[[DownloadProgress], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> str:
        if not file_name.lower().endswith(".gguf"):
            file_name += ".gguf"

        final_path = os.path.join(self._models_directory, file_name)
        partial_path = final_path + ".partial"

        with requests.get(source_url, stream=True, timeout=30) as response:
            response.raise_for_status()
            total_bytes = response.headers.get("Content-Length")
            total_bytes = int(total_bytes) if total_bytes else None

            bytes_received = 0
            with open(partial_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1 << 20):
                    if should_cancel is not None and should_cancel():
                        f.close()
                        os.remove(partial_path)
                        raise InterruptedError("Download cancelled")

                    if not chunk:
                        continue
                    f.write(chunk)
                    bytes_received += len(chunk)
                    if on_progress is not None:
                        on_progress(DownloadProgress(bytes_received, total_bytes))

        os.replace(partial_path, final_path)
        return final_path

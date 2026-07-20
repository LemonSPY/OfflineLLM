"""Discovers locally available .gguf models.

Model choice is deliberately left to the user rather than a hardcoded
default -- this just lists what's on disk.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelInfo:
    id: str
    display_name: str
    file_path: str
    file_size_bytes: int

    @property
    def file_size_gib(self) -> float:
        return self.file_size_bytes / 1024 / 1024 / 1024


class ModelManager:
    def __init__(self, models_directory: str):
        self._models_directory = models_directory
        os.makedirs(self._models_directory, exist_ok=True)

    def list_available_models(self) -> list[ModelInfo]:
        if not os.path.isdir(self._models_directory):
            return []

        models = []
        for root, _dirs, files in os.walk(self._models_directory):
            for name in files:
                if not name.lower().endswith(".gguf"):
                    continue
                path = os.path.join(root, name)
                model_id = os.path.splitext(name)[0]
                models.append(ModelInfo(
                    id=model_id,
                    display_name=model_id,
                    file_path=path,
                    file_size_bytes=os.path.getsize(path),
                ))

        models.sort(key=lambda m: m.display_name.lower())
        return models

    def find_by_id(self, model_id: str) -> ModelInfo | None:
        for model in self.list_available_models():
            if model.id.lower() == model_id.lower():
                return model
        return None

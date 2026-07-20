"""Streams chat completions from a running llama-server instance's
OpenAI-compatible /v1/chat/completions endpoint (localhost only).
"""

from __future__ import annotations

import json
from typing import Iterator

import requests

from .chat_models import ChatMessage
from .llama_server import LlamaServerProcess

_ROLE_TO_API = {
    "user": "user",
    "assistant": "assistant",
    "system": "system",
}


def stream_reply(server: LlamaServerProcess, history: list[ChatMessage]) -> Iterator[str]:
    payload = {
        "model": "local",
        "stream": True,
        "messages": [
            {"role": _ROLE_TO_API.get(m.role.value, "user"), "content": m.content}
            for m in history
        ],
    }

    with requests.post(server.base_url + "v1/chat/completions", json=payload, stream=True, timeout=120) as response:
        response.raise_for_status()

        for raw_line in response.iter_lines(decode_unicode=True):
            if not raw_line or not raw_line.startswith("data:"):
                continue

            data = raw_line[len("data:"):].strip()
            if data == "[DONE]":
                return

            chunk = json.loads(data)
            delta = chunk["choices"][0]["delta"]
            content = delta.get("content")
            if content:
                yield content

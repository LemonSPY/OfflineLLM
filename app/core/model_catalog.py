"""A small curated starting list of well-known instruction-tuned models in
quantized GGUF form, sized against a 16GB GPU memory budget. Deliberately
short and editable rather than an exhaustive catalog -- the app also accepts
any direct .gguf URL the user provides (see the "custom URL" path in the
download dialog), so an out-of-date entry here is an inconvenience, not a
hard dependency.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelCatalogEntry:
    id: str
    display_name: str
    description: str
    source_url: str
    approx_size_gib: float


CURATED: list[ModelCatalogEntry] = [
    ModelCatalogEntry(
        id="qwen2.5-14b-instruct-q4_k_m",
        display_name="Qwen2.5 14B Instruct (Q4_K_M)",
        description="Strong all-rounder for chat, coding, and reasoning. ~9GB - fits a 16GB GPU with room for a large context.",
        source_url="https://huggingface.co/Qwen/Qwen2.5-14B-Instruct-GGUF/resolve/main/qwen2.5-14b-instruct-q4_k_m.gguf",
        approx_size_gib=8.9,
    ),
    ModelCatalogEntry(
        id="llama-3.1-8b-instruct-q4_k_m",
        display_name="Llama 3.1 8B Instruct (Q4_K_M)",
        description="Smaller footprint, leaves more headroom for a longer context window. ~5GB.",
        source_url="https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
        approx_size_gib=4.9,
    ),
    ModelCatalogEntry(
        id="mistral-7b-instruct-v0.3-q4_k_m",
        display_name="Mistral 7B Instruct v0.3 (Q4_K_M)",
        description="Lightweight general-purpose model. ~4.4GB.",
        source_url="https://huggingface.co/bartowski/Mistral-7B-Instruct-v0.3-GGUF/resolve/main/Mistral-7B-Instruct-v0.3-Q4_K_M.gguf",
        approx_size_gib=4.4,
    ),
    ModelCatalogEntry(
        id="phi-3.5-mini-instruct-q4_k_m",
        display_name="Phi-3.5 Mini Instruct (Q4_K_M)",
        description="Small and fast, good for quick answers on modest hardware. ~2.4GB.",
        source_url="https://huggingface.co/bartowski/Phi-3.5-mini-instruct-GGUF/resolve/main/Phi-3.5-mini-instruct-Q4_K_M.gguf",
        approx_size_gib=2.4,
    ),
]

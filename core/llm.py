"""Minimal Ollama client."""

from __future__ import annotations

import ollama
from typing import Optional

DEFAULT_MODEL = "openbmb/minicpm5-2b"

def generate(prompt: str, model: str = DEFAULT_MODEL, system: Optional[str] = None) -> str:
    """Call the local model and return the response text."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = ollama.chat(model=model, messages=messages)
    return response["message"]["content"]

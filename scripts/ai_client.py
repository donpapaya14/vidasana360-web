"""
AI client con fallback Groq → GitHub Models.
Adaptado de youtube-bot/src/research.py
"""

import json
import logging
import os
import time

from groq import Groq
from openai import OpenAI

log = logging.getLogger(__name__)

GROQ_MODEL = "llama-3.3-70b-versatile"
GITHUB_MODEL = "DeepSeek-V3-0324"


def _get_groq_client():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise ValueError("GROQ_API_KEY no configurada")
    return Groq(api_key=key)


def _get_github_client():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN no configurado")
    return OpenAI(
        base_url="https://models.inference.ai.azure.com",
        api_key=token,
    )


def call_groq(prompt: str, temperature: float = 0.7, max_tokens: int = 4096) -> dict:
    """Llama a Groq con formato JSON forzado."""
    client = _get_groq_client()
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return json.loads(response.choices[0].message.content)


def call_github(prompt: str, temperature: float = 0.7) -> dict:
    """Llama a GitHub Models (DeepSeek-V3). Limpia markdown fences."""
    client = _get_github_client()
    response = client.chat.completions.create(
        model=GITHUB_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    text = response.choices[0].message.content.strip()
    # Strip markdown code fences
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    return json.loads(text.strip())


def call_ai(prompt: str, temperature: float = 0.7, max_retries: int = 2) -> dict:
    """Groq primary con fallback a GitHub Models. Retry con backoff."""
    for attempt in range(max_retries):
        try:
            return call_groq(prompt, temperature)
        except Exception as e:
            log.warning("Groq intento %d falló: %s", attempt + 1, e)
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)

    log.info("Groq agotado. Intentando GitHub Models...")
    try:
        return call_github(prompt, temperature)
    except Exception as e:
        log.error("GitHub Models también falló: %s", e)
        raise RuntimeError("Ambos proveedores AI fallaron") from e

"""
AI client con fallback Groq → GitHub Models.
Usa siempre el modelo de mayor calidad (70b).
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


def call_groq(prompt: str, temperature: float = 0.7) -> dict:
    client = _get_groq_client()
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=temperature,
        max_tokens=4096,
    )
    return json.loads(response.choices[0].message.content)


def call_github(prompt: str, temperature: float = 0.7) -> dict:
    client = _get_github_client()
    response = client.chat.completions.create(
        model=GITHUB_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    text = response.choices[0].message.content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    return json.loads(text.strip())


def call_ai(prompt: str, temperature: float = 0.7, **kwargs) -> dict:
    """Groq 70b primary, GitHub Models fallback. Retry con backoff."""
    for attempt in range(3):
        try:
            return call_groq(prompt, temperature)
        except Exception as e:
            wait = 10 * (attempt + 1)
            log.warning("Groq intento %d: %s. Esperando %ds...", attempt + 1, str(e)[:80], wait)
            time.sleep(wait)

    log.info("Groq agotado. Intentando GitHub Models...")
    for attempt in range(2):
        try:
            return call_github(prompt, temperature)
        except Exception as e:
            if attempt < 1:
                time.sleep(30)
            log.warning("GitHub Models intento %d: %s", attempt + 1, str(e)[:80])

    raise RuntimeError("Ambos proveedores AI fallaron")

"""
AI client con fallback Groq → GitHub Models.
Usa 8b-instant para research (ahorra tokens) y 70b para contenido.
"""

import json
import logging
import os
import time

from groq import Groq
from openai import OpenAI

log = logging.getLogger(__name__)

GROQ_MODEL_FAST = "llama-3.1-8b-instant"      # Research: barato
GROQ_MODEL_QUALITY = "llama-3.3-70b-versatile"  # Content: calidad
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


def call_groq(prompt: str, temperature: float = 0.7, max_tokens: int = 4096, fast: bool = False) -> dict:
    """Llama a Groq. fast=True usa modelo 8b (4x menos tokens)."""
    client = _get_groq_client()
    model = GROQ_MODEL_FAST if fast else GROQ_MODEL_QUALITY
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return json.loads(response.choices[0].message.content)


def call_github(prompt: str, temperature: float = 0.7) -> dict:
    """Llama a GitHub Models (DeepSeek-V3)."""
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


def call_ai(prompt: str, temperature: float = 0.7, max_retries: int = 3, fast: bool = False) -> dict:
    """Groq primary con fallback a GitHub Models."""
    for attempt in range(max_retries):
        try:
            return call_groq(prompt, temperature, fast=fast)
        except Exception as e:
            wait = 10 * (attempt + 1)
            log.warning("Groq intento %d falló: %s. Esperando %ds...", attempt + 1, str(e)[:100], wait)
            time.sleep(wait)

    log.info("Groq agotado. Intentando GitHub Models...")
    for attempt in range(2):
        try:
            return call_github(prompt, temperature)
        except Exception as e:
            wait = 30 * (attempt + 1)
            log.warning("GitHub Models intento %d falló: %s. Esperando %ds...", attempt + 1, str(e)[:100], wait)
            if attempt < 1:
                time.sleep(wait)

    raise RuntimeError("Ambos proveedores AI fallaron")

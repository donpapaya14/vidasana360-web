"""
AI client: round-robin Groq / GitHub / NVIDIA.
Distribuye carga entre proveedores para maximizar tokens gratuitos.
Fallback inmediato si uno falla — timeout 60s por llamada.
"""

import json
import logging
import os
import re as _re
import time

from groq import Groq
from openai import OpenAI

log = logging.getLogger(__name__)

GROQ_MODEL = "llama-3.3-70b-versatile"
GITHUB_MODEL = "DeepSeek-V3-0324"
NVIDIA_MODEL = "deepseek-ai/deepseek-v4-flash"

# Orden: Groq (rápido) → GitHub (fiable) → NVIDIA (504 frecuente, último recurso)
PROVIDERS = ["groq", "github", "nvidia"]
_call_count = 0


def _parse_json(text: str) -> dict:
    """Limpia markdown/think tags y parsea JSON."""
    text = text.strip()
    if "<think>" in text:
        text = _re.sub(r"<think>.*?</think>", "", text, flags=_re.DOTALL).strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    return json.loads(text.strip())


def _call_groq(prompt: str, temperature: float = 0.7) -> dict:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise ValueError("GROQ_API_KEY no configurada")
    client = Groq(api_key=key, timeout=60.0, max_retries=0)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=temperature,
        max_tokens=8192,
    )
    return json.loads(response.choices[0].message.content)


def _call_github(prompt: str, temperature: float = 0.7) -> dict:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN no configurado")
    client = OpenAI(
        base_url="https://models.inference.ai.azure.com",
        api_key=token,
        timeout=120.0,
        max_retries=0,
    )
    response = client.chat.completions.create(
        model=GITHUB_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=8192,
    )
    return _parse_json(response.choices[0].message.content)


def _call_nvidia(prompt: str, temperature: float = 0.7) -> dict:
    key = os.getenv("NVIDIA_API_KEY")
    if not key:
        raise ValueError("NVIDIA_API_KEY no configurada")
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=key,
        timeout=90.0,
        max_retries=0,
    )
    response = client.chat.completions.create(
        model=NVIDIA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=8192,
    )
    return _parse_json(response.choices[0].message.content)


_PROVIDER_MAP = {
    "groq": _call_groq,
    "github": _call_github,
    "nvidia": _call_nvidia,
}


def call_ai(prompt: str, temperature: float = 0.7, **kwargs) -> dict:
    """Round-robin entre proveedores + fallback inmediato.

    Distribuye calls: art1→Groq/GitHub, art2→GitHub/NVIDIA, art3→NVIDIA/Groq...
    Si uno falla, salta al siguiente sin esperar. Max 1 retry por proveedor.
    """
    global _call_count
    article_idx = int(os.getenv("ARTICLE_INDEX", "1")) - 1
    rotation = (article_idx * 2 + _call_count) % len(PROVIDERS)
    _call_count += 1

    order = PROVIDERS[rotation:] + PROVIDERS[:rotation]

    errors = []
    for provider_name in order:
        func = _PROVIDER_MAP[provider_name]
        try:
            result = func(prompt, temperature)
            log.info("✓ %s", provider_name)
            return result
        except Exception as e:
            err = str(e)
            errors.append(f"{provider_name}: {err[:100]}")
            log.warning("✗ %s: %s", provider_name, err[:100])
            if "429" in err:
                time.sleep(15)
            else:
                time.sleep(3)

    raise RuntimeError(f"Todos los proveedores fallaron: {'; '.join(errors)}")

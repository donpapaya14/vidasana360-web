"""
AI client: round-robin Groq / NVIDIA / GitHub Models.
Distribuye carga entre proveedores para maximizar tokens gratuitos.
Fallback inmediato si uno falla — sin perder tiempo en retries largos.
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
NVIDIA_MODEL = "deepseek-ai/deepseek-v4-flash"
GITHUB_MODEL = "DeepSeek-V3-0324"

PROVIDERS = ["groq", "nvidia", "github"]
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
    client = Groq(api_key=key)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=temperature,
        max_tokens=8192,
    )
    return json.loads(response.choices[0].message.content)


def _call_nvidia(prompt: str, temperature: float = 0.7) -> dict:
    key = os.getenv("NVIDIA_API_KEY")
    if not key:
        raise ValueError("NVIDIA_API_KEY no configurada")
    client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=key)
    response = client.chat.completions.create(
        model=NVIDIA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=8192,
    )
    return _parse_json(response.choices[0].message.content)


def _call_github(prompt: str, temperature: float = 0.7) -> dict:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN no configurado")
    client = OpenAI(base_url="https://models.inference.ai.azure.com", api_key=token)
    response = client.chat.completions.create(
        model=GITHUB_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=8192,
    )
    return _parse_json(response.choices[0].message.content)


_PROVIDER_MAP = {
    "groq": _call_groq,
    "nvidia": _call_nvidia,
    "github": _call_github,
}


def call_ai(prompt: str, temperature: float = 0.7, **kwargs) -> dict:
    """Round-robin entre proveedores + fallback inmediato.

    Distribuye calls: art1→Groq/NVIDIA, art2→NVIDIA/GitHub, art3→GitHub/Groq...
    Si uno falla, salta al siguiente sin esperar. Retry 1x por proveedor.
    """
    global _call_count
    article_idx = int(os.getenv("ARTICLE_INDEX", "1")) - 1
    rotation = (article_idx * 2 + _call_count) % len(PROVIDERS)
    _call_count += 1

    order = PROVIDERS[rotation:] + PROVIDERS[:rotation]

    errors = []
    for provider_name in order:
        func = _PROVIDER_MAP[provider_name]
        for attempt in range(2):
            try:
                result = func(prompt, temperature)
                log.info("✓ %s (intento %d)", provider_name, attempt + 1)
                return result
            except Exception as e:
                err = str(e)
                errors.append(f"{provider_name}[{attempt+1}]: {err[:80]}")
                log.warning("%s intento %d: %s", provider_name, attempt + 1, err[:80])
                if "429" in err:
                    time.sleep(10)
                    break  # 429 = rate limit, saltar a siguiente proveedor
                time.sleep(5)

    raise RuntimeError(f"Todos los proveedores fallaron: {'; '.join(errors)}")

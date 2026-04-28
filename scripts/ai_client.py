"""
AI client: Groq (rápido) → NVIDIA (potente) → GitHub Models (emergencia).
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
    text = response.choices[0].message.content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    text = text.strip()
    if "<think>" in text:
        text = _re.sub(r"<think>.*?</think>", "", text, flags=_re.DOTALL).strip()
    return json.loads(text)


def _call_github(prompt: str, temperature: float = 0.7) -> dict:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN no configurado")
    client = OpenAI(base_url="https://models.inference.ai.azure.com", api_key=token)
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
    """Groq → NVIDIA → GitHub Models. Retry con backoff para 429."""
    # 1. Groq (fast, reliable)
    for attempt in range(3):
        try:
            return _call_groq(prompt, temperature)
        except Exception as e:
            err = str(e)
            log.warning("Groq %d: %s", attempt + 1, err[:80])
            wait = 30 * (attempt + 1) if "429" in err else 5 * (attempt + 1)
            time.sleep(wait)

    # 2. NVIDIA (powerful but can timeout)
    for attempt in range(2):
        try:
            return _call_nvidia(prompt, temperature)
        except Exception as e:
            log.warning("NVIDIA %d: %s", attempt + 1, str(e)[:80])
            time.sleep(10)

    # 3. GitHub Models (last resort)
    for attempt in range(2):
        try:
            return _call_github(prompt, temperature)
        except Exception as e:
            log.warning("GitHub %d: %s", attempt + 1, str(e)[:80])
            if attempt < 1:
                time.sleep(30)

    raise RuntimeError("Los 3 proveedores AI fallaron")

"""
AI client: NVIDIA (DeepSeek V4 Flash) → Groq → GitHub Models.
3 proveedores para máxima disponibilidad.
"""

import json
import logging
import os
import time

from openai import OpenAI
from groq import Groq

log = logging.getLogger(__name__)

NVIDIA_MODEL = "deepseek-ai/deepseek-v4-flash"
GROQ_MODEL = "llama-3.3-70b-versatile"
GITHUB_MODEL = "DeepSeek-V3-0324"


def _call_nvidia(prompt: str, temperature: float = 0.7) -> dict:
    """NVIDIA API — DeepSeek V4 Flash (mejor modelo, gratis)."""
    key = os.getenv("NVIDIA_API_KEY")
    if not key:
        raise ValueError("NVIDIA_API_KEY no configurada")
    client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=key)
    response = client.chat.completions.create(
        model=NVIDIA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=4096,
    )
    text = response.choices[0].message.content.strip()
    # Strip markdown fences
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    # Strip thinking tags if present
    text = text.strip()
    if "<think>" in text:
        import re
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    return json.loads(text)


def _call_groq(prompt: str, temperature: float = 0.7) -> dict:
    """Groq — Llama 3.3 70B (fallback 1)."""
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise ValueError("GROQ_API_KEY no configurada")
    client = Groq(api_key=key)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=temperature,
        max_tokens=4096,
    )
    return json.loads(response.choices[0].message.content)


def _call_github(prompt: str, temperature: float = 0.7) -> dict:
    """GitHub Models — DeepSeek V3 (fallback 2)."""
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
    """NVIDIA → Groq → GitHub Models. Triple fallback."""
    # 1. Try NVIDIA (best model, free)
    for attempt in range(2):
        try:
            return _call_nvidia(prompt, temperature)
        except Exception as e:
            log.warning("NVIDIA intento %d: %s", attempt + 1, str(e)[:80])
            time.sleep(5)

    # 2. Try Groq (fast, limited tokens)
    for attempt in range(2):
        try:
            return _call_groq(prompt, temperature)
        except Exception as e:
            log.warning("Groq intento %d: %s", attempt + 1, str(e)[:80])
            time.sleep(10)

    # 3. Try GitHub Models (slow, very limited)
    for attempt in range(2):
        try:
            return _call_github(prompt, temperature)
        except Exception as e:
            log.warning("GitHub intento %d: %s", attempt + 1, str(e)[:80])
            if attempt < 1:
                time.sleep(30)

    raise RuntimeError("Los 3 proveedores AI fallaron")

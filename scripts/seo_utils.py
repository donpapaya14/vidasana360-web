"""Utilidades SEO: slugs, internal linking."""

import re
from slugify import slugify


def generate_slug(title: str) -> str:
    """Genera slug SEO-friendly desde título en español."""
    return slugify(title, max_length=80, word_boundary=True)


def estimate_reading_time(text: str) -> int:
    """Estima minutos de lectura (200 palabras/min para español)."""
    words = len(text.split())
    return max(1, round(words / 200))


def clean_markdown(text: str) -> str:
    """Limpia artefactos comunes de generación AI en markdown."""
    # Remove markdown code fences if AI wraps in them
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]

    # Fix double blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Ensure text ends with newline
    if not text.endswith('\n'):
        text += '\n'

    return text

#!/usr/bin/env python3
"""
Genera un artículo SEO completo en Markdown.
Pipeline: plan_topic → research AI → generate content AI → write markdown
Adaptado del patrón youtube-bot/src/research.py + main.py
"""

import json
import logging
import os
import sys
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

# Add scripts dir to path
sys.path.insert(0, str(Path(__file__).parent))

from ai_client import call_ai
from topic_planner import plan_topic, get_existing_titles
from seo_utils import generate_slug, estimate_reading_time, clean_markdown

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

BLOG_DIR = Path(__file__).parent.parent / "src" / "content" / "blog"
CATEGORY_NAMES = {
    "nutricion": "Nutrición",
    "ejercicio": "Ejercicio",
    "mente": "Salud Mental",
    "longevidad": "Longevidad",
    "recetas": "Recetas Saludables",
}


def research_topic(category: str, formula: str, existing_titles: list[str]) -> dict:
    """Paso 1: Investiga y elige un tema concreto con outline."""
    existing_str = "\n".join(f"- {t}" for t in existing_titles[:15]) if existing_titles else "Ninguno"

    prompt = f"""Eres un editor de un blog de salud basado en evidencia científica en español.
Categoría: {CATEGORY_NAMES.get(category, category)}

GENERA UN TEMA para un artículo SEO largo (1500-2000 palabras) sobre:
{formula}

ARTÍCULOS YA PUBLICADOS (NO repetir estos temas):
{existing_str}

REGLAS CRÍTICAS:
- Tema NUEVO, diferente a los ya publicados
- Debe ser buscable en Google (keyword research mental)
- Título SEO: max 70 chars, incluir keyword principal
- Meta description: max 160 chars, llamativa y con keyword
- Outline con 5-7 secciones H2 lógicas
- CADA sección debe incluir al menos 1 estudio/fuente real

Responde SOLO JSON:
{{
  "title": "título SEO optimizado max 70 chars",
  "description": "meta description max 160 chars con keyword",
  "keyword": "keyword principal para SEO",
  "secondary_keywords": ["keyword2", "keyword3", "keyword4"],
  "outline": [
    {{"h2": "Título sección 1", "points": ["punto a cubrir", "estudio a citar"]}},
    {{"h2": "Título sección 2", "points": ["punto", "estudio"]}},
    ...
  ],
  "sources_preview": ["Nombre estudio/revista 1", "Nombre estudio/revista 2", "..."]
}}"""

    data = call_ai(prompt, temperature=0.8)
    log.info("Tema investigado: %s", data.get("title", "?"))
    return data


def generate_content(category: str, topic_data: dict) -> dict:
    """Paso 2: Genera el artículo completo con fuentes."""
    outline_str = json.dumps(topic_data["outline"], ensure_ascii=False, indent=2)

    prompt = f"""Escribe un artículo completo de blog en español sobre salud/bienestar.

TÍTULO: {topic_data['title']}
CATEGORÍA: {CATEGORY_NAMES.get(category, category)}
KEYWORD PRINCIPAL: {topic_data['keyword']}
KEYWORDS SECUNDARIAS: {', '.join(topic_data.get('secondary_keywords', []))}

OUTLINE A SEGUIR:
{outline_str}

REGLAS CRÍTICAS DE CONTENIDO:
1. CADA afirmación de salud DEBE tener fuente: "(Universidad X, año)" o "(Estudio en Revista Y, año)"
2. CERO afirmaciones sin fuente verificable. Si no puedes citar un estudio real, NO lo incluyas
3. NO recomendar tratamientos médicos — siempre "consulta con tu médico"
4. Datos REALES: cifras, porcentajes, nombres de universidades, revistas científicas
5. Tono: informativo, cercano, como explicar a un amigo inteligente
6. Usar TÚ para dirigirte al lector
7. Incluir consejos prácticos y aplicables en cada sección

REGLAS DE FORMATO:
1. Usar ## para H2 y ### para H3
2. Listas con - o números cuando sea apropiado
3. Negrita para términos clave con **texto**
4. 1500-2000 palabras de contenido
5. NO incluir el título H1 (se pone automáticamente)
6. Último H2: "Resumen práctico" con bullets de acción

REGLAS SEO:
1. Incluir keyword principal en primer párrafo
2. Keywords secundarias distribuidas naturalmente
3. H2 deben incluir variaciones de la keyword cuando sea natural
4. Párrafos cortos (3-4 líneas máximo)

Responde SOLO JSON:
{{
  "content": "contenido markdown completo del artículo (sin título H1)",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "sources": [
    "Apellido, A. (año). Título del estudio. Revista, volumen(número)",
    "Institución (año). Título del informe/guía",
    "..."
  ]
}}"""

    data = call_ai(prompt, temperature=0.6, max_retries=2)
    log.info("Artículo generado: %d caracteres", len(data.get("content", "")))
    return data


def write_markdown(category: str, topic_data: dict, content_data: dict) -> Path:
    """Escribe el archivo markdown con frontmatter."""
    title = topic_data["title"]
    slug = generate_slug(title)
    content = clean_markdown(content_data["content"])
    reading_time = estimate_reading_time(content)
    sources = content_data.get("sources", topic_data.get("sources_preview", []))
    tags = content_data.get("tags", topic_data.get("secondary_keywords", []))
    today = date.today().isoformat()

    # Format sources as YAML array
    sources_yaml = "\n".join(f'  - "{s}"' for s in sources)
    tags_yaml = json.dumps(tags, ensure_ascii=False)

    frontmatter = f"""---
title: "{title}"
description: "{topic_data['description']}"
pubDate: {today}
category: "{category}"
tags: {tags_yaml}
author: "VidaSana360"
readingTime: {reading_time}
sources:
{sources_yaml}
draft: false
---"""

    BLOG_DIR.mkdir(parents=True, exist_ok=True)
    file_path = BLOG_DIR / f"{slug}.md"

    # Avoid overwriting
    if file_path.exists():
        slug = f"{slug}-{today}"
        file_path = BLOG_DIR / f"{slug}.md"

    file_path.write_text(f"{frontmatter}\n\n{content}", encoding="utf-8")
    log.info("Artículo escrito: %s", file_path)
    return file_path


def notify_telegram(message: str):
    """Notificación Telegram (mismo patrón que youtube-bot/src/publisher.py)."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return

    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
            timeout=30,
        )
    except Exception as e:
        log.warning("Telegram falló: %s", e)


def main():
    log.info("=== Generando artículo SEO ===")

    # Step 1: Plan topic
    plan = plan_topic()
    category = plan["category"]
    formula = plan["formula"]
    log.info("Categoría: %s | Fórmula: %s", category, formula[:60])

    # Step 2: Research
    topic_data = research_topic(category, formula, plan["existing_titles"])

    # Step 3: Generate content
    content_data = generate_content(category, topic_data)

    # Step 4: Write markdown
    file_path = write_markdown(category, topic_data, content_data)

    # Step 5: Notify
    title = topic_data["title"]
    msg = (
        f"<b>📝 Nuevo artículo VidaSana360</b>\n"
        f"<b>Título:</b> {title}\n"
        f"<b>Categoría:</b> {CATEGORY_NAMES.get(category, category)}\n"
        f"<b>Archivo:</b> {file_path.name}"
    )
    notify_telegram(msg)

    log.info("=== Artículo completado: %s ===", title)
    return str(file_path)


if __name__ == "__main__":
    main()

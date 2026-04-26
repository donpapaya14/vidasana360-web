#!/usr/bin/env python3
"""
Genera un artículo SEO completo en Markdown con links Amazon Afiliados.
Pipeline: plan_topic → research AI → generate content AI → write markdown
Optimizado para long-tail keywords y monetización.
"""

import json
import logging
import os
import sys
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

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

# Amazon affiliate tag — CAMBIAR cuando tengas tu tag real
AMAZON_TAG = os.getenv("AMAZON_TAG", "vladys-21")
SITE_URL = os.getenv("SITE_URL", "https://vidasana360-web.vercel.app")
BRAND = os.getenv("BRAND", "VidaSana360")


def research_topic(category: str, formula: str, existing_titles: list[str]) -> dict:
    """Paso 1: Investiga tema con enfoque long-tail keyword."""
    existing_str = "\n".join(f"- {t}" for t in existing_titles[:20]) if existing_titles else "Ninguno"

    prompt = f"""Eres un experto SEO y editor de un blog en español sobre {CATEGORY_NAMES.get(category, category)}.

GENERA UN TEMA para un artículo SEO largo (2000-2500 palabras) sobre:
{formula}

ARTÍCULOS YA PUBLICADOS (NO repetir):
{existing_str}

ESTRATEGIA SEO — LONG-TAIL KEYWORDS:
- Elige una keyword LONG-TAIL (3-6 palabras) que sea MUY ESPECÍFICA
- Ejemplo MALO: "ayuno intermitente" (demasiado competitivo)
- Ejemplo BUENO: "ayuno intermitente 16/8 para principiantes mayores de 40"
- La keyword debe ser algo que alguien buscaria en Google palabra por palabra
- Prioriza keywords tipo "cómo", "qué es", "mejores", "guía", "para principiantes"

REGLAS:
- Título SEO: max 65 chars, incluir keyword EXACTA
- Meta description: max 155 chars, incluir keyword, generar curiosidad
- Outline con 6-8 secciones H2 (más secciones = más contenido = mejor SEO)
- CADA sección debe citar al menos 1 fuente real
- Incluir 1-2 productos REALES de Amazon relevantes al tema (nombre exacto del producto)

Responde SOLO JSON:
{{
  "title": "titulo SEO con keyword long-tail exacta",
  "description": "meta description max 155 chars con keyword",
  "keyword": "keyword long-tail principal de 3-6 palabras",
  "secondary_keywords": ["kw2", "kw3", "kw4", "kw5"],
  "outline": [
    {{"h2": "Seccion 1", "points": ["punto", "estudio a citar"]}},
    {{"h2": "Seccion 2", "points": ["punto", "estudio"]}},
    ...
  ],
  "sources_preview": ["Estudio/revista 1", "Estudio/revista 2", "..."],
  "amazon_products": [
    {{"name": "nombre exacto producto Amazon", "why": "por que es relevante en 1 linea"}}
  ]
}}"""

    data = call_ai(prompt, temperature=0.85)
    log.info("Tema: %s | KW: %s", data.get("title", "?"), data.get("keyword", "?"))
    return data


def generate_content(category: str, topic_data: dict) -> dict:
    """Paso 2: Genera artículo completo con Amazon y SEO."""
    outline_str = json.dumps(topic_data["outline"], ensure_ascii=False, indent=2)
    products = topic_data.get("amazon_products", [])
    products_str = json.dumps(products, ensure_ascii=False) if products else "ninguno"

    prompt = f"""Escribe un artículo COMPLETO de blog en español.

TÍTULO: {topic_data['title']}
CATEGORÍA: {CATEGORY_NAMES.get(category, category)}
KEYWORD PRINCIPAL: {topic_data['keyword']}
KEYWORDS SECUNDARIAS: {', '.join(topic_data.get('secondary_keywords', []))}
PRODUCTOS AMAZON RELEVANTES: {products_str}

OUTLINE:
{outline_str}

REGLAS DE CONTENIDO:
1. CADA afirmación DEBE tener fuente real: "(Universidad X, año)" o "(Estudio en Revista Y, año)"
2. CERO afirmaciones sin fuente. Si no hay estudio real, NO lo inventes
3. Tono: informativo, cercano, como explicar a un amigo inteligente
4. Usar TÚ para dirigirte al lector
5. Incluir consejos PRÁCTICOS y APLICABLES
6. 2000-2500 palabras MÍNIMO

REGLAS SEO AVANZADO:
1. Keyword principal en primer párrafo Y en un H2
2. Keywords secundarias en H2 y distribuidas naturalmente
3. Párrafos CORTOS (2-3 líneas máximo para móvil)
4. Listas y bullets frecuentes (Google las ama para featured snippets)
5. Incluir una sección tipo FAQ con 3-4 preguntas (## Preguntas frecuentes)
6. Último H2: "Resumen práctico" con bullets de acción

REGLAS AMAZON AFILIADOS:
1. Si hay productos relevantes, incluir una sección "## Productos recomendados"
2. Para cada producto, escribir: nombre, para qué sirve, por qué lo recomiendas (1-2 líneas)
3. Incluir placeholder: [AMAZON:nombre-producto] que será reemplazado por el link real
4. NO ser agresivo vendiendo. Recomendar de forma natural y honesta
5. Añadir disclaimer: "Este artículo contiene enlaces de afiliado. Si compras a través de ellos, recibimos una pequeña comisión sin coste adicional para ti."

REGLAS FORMATO:
1. ## para H2, ### para H3
2. **negrita** para términos clave
3. Listas con - o números
4. NO incluir título H1
5. Incluir tabla comparativa si el tema lo permite

Responde SOLO JSON:
{{
  "content": "contenido markdown completo (sin H1)",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6"],
  "sources": [
    "Apellido, A. (año). Titulo. Revista, volumen(numero)",
    "..."
  ],
  "amazon_keywords": ["keyword busqueda amazon producto 1", "keyword producto 2"]
}}"""

    data = call_ai(prompt, temperature=0.55, max_retries=2)
    log.info("Artículo generado: %d chars", len(data.get("content", "")))
    return data


def inject_amazon_links(content: str, amazon_keywords: list[str]) -> str:
    """Reemplaza [AMAZON:x] con links reales de Amazon Afiliados."""
    import re

    # Replace [AMAZON:product-name] placeholders
    def replace_amazon(match):
        product = match.group(1)
        search_query = product.replace(" ", "+")
        return f"[{product} en Amazon](https://www.amazon.es/s?k={search_query}&tag={AMAZON_TAG})"

    content = re.sub(r'\[AMAZON:([^\]]+)\]', replace_amazon, content)

    # If no placeholders found but we have amazon_keywords, add a products section
    if amazon_keywords and "[AMAZON:" not in content and "amazon.es" not in content:
        products_section = "\n\n## Productos recomendados\n\n"
        products_section += "*Este artículo contiene enlaces de afiliado. Si compras a través de ellos, recibimos una pequeña comisión sin coste adicional para ti.*\n\n"
        for kw in amazon_keywords[:3]:
            search = kw.replace(" ", "+")
            products_section += f"- [{kw}](https://www.amazon.es/s?k={search}&tag={AMAZON_TAG})\n"
        content += products_section

    return content


def write_markdown(category: str, topic_data: dict, content_data: dict) -> Path:
    """Escribe markdown con frontmatter y links Amazon."""
    title = topic_data["title"]
    slug = generate_slug(title)
    content = clean_markdown(content_data["content"])

    # Inject Amazon affiliate links
    amazon_kws = content_data.get("amazon_keywords", [])
    content = inject_amazon_links(content, amazon_kws)

    reading_time = estimate_reading_time(content)
    sources = content_data.get("sources", topic_data.get("sources_preview", []))
    tags = content_data.get("tags", topic_data.get("secondary_keywords", []))
    today = date.today().isoformat()

    sources_yaml = "\n".join(f'  - "{s}"' for s in sources)
    tags_yaml = json.dumps(tags, ensure_ascii=False)

    frontmatter = f"""---
title: "{title}"
description: "{topic_data['description']}"
pubDate: {today}
category: "{category}"
tags: {tags_yaml}
author: "{BRAND}"
readingTime: {reading_time}
sources:
{sources_yaml}
draft: false
---"""

    BLOG_DIR.mkdir(parents=True, exist_ok=True)
    file_path = BLOG_DIR / f"{slug}.md"

    if file_path.exists():
        slug = f"{slug}-{today}"
        file_path = BLOG_DIR / f"{slug}.md"

    file_path.write_text(f"{frontmatter}\n\n{content}", encoding="utf-8")
    log.info("Artículo escrito: %s", file_path)
    return file_path


def notify_telegram(message: str):
    """Notificación Telegram."""
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
    log.info("=== Generando artículo SEO + Amazon ===")

    plan = plan_topic()
    category = plan["category"]
    formula = plan["formula"]
    log.info("Cat: %s | Fórmula: %s", category, formula[:60])

    topic_data = research_topic(category, formula, plan["existing_titles"])
    content_data = generate_content(category, topic_data)
    file_path = write_markdown(category, topic_data, content_data)

    title = topic_data["title"]
    keyword = topic_data.get("keyword", "")
    msg = (
        f"<b>📝 {BRAND} — Nuevo artículo</b>\n"
        f"<b>Título:</b> {title}\n"
        f"<b>Keyword:</b> {keyword}\n"
        f"<b>Cat:</b> {CATEGORY_NAMES.get(category, category)}\n"
        f"<b>Archivo:</b> {file_path.name}"
    )
    notify_telegram(msg)

    log.info("=== Completado: %s ===", title)
    return str(file_path)


if __name__ == "__main__":
    main()

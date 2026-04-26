#!/usr/bin/env python3
"""
Genera UN artículo SEO de calidad con datos reales y links Amazon.
Prioridad: contenido útil y real > volumen.
"""

import json
import logging
import os
import re
import sys
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from ai_client import call_ai
from topic_planner import plan_topic
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

AMAZON_TAG = os.getenv("AMAZON_TAG", "vladys-21")
SITE_URL = os.getenv("SITE_URL", "https://vidasana360-web.vercel.app")
BRAND = os.getenv("BRAND", "VidaSana360")


def research_topic(category: str, formula: str, existing_titles: list[str]) -> dict:
    """Paso 1: Elige tema con keyword long-tail y plan detallado."""
    existing_str = "\n".join(f"- {t}" for t in existing_titles[:20]) if existing_titles else "Ninguno"

    prompt = f"""Eres editor jefe de un blog profesional en español sobre {CATEGORY_NAMES.get(category, category)}.

Tu trabajo: elegir UN tema para un artículo que sea REALMENTE ÚTIL para el lector.

TIPO DE ARTÍCULO A CREAR: {formula}

ARTÍCULOS QUE YA EXISTEN (elige algo DIFERENTE):
{existing_str}

INSTRUCCIONES:
1. Elige un tema MUY ESPECÍFICO (no genérico). Ejemplo malo: "beneficios del ejercicio". Ejemplo bueno: "rutina de sentadillas búlgaras para fortalecer rodillas después de los 40".
2. El título debe ser lo que alguien escribiría en Google, 3-6 palabras clave.
3. Piensa en 5-6 secciones donde CADA UNA aporte información concreta que el lector no sabía.
4. Para cada sección, escribe QUÉ dato específico o consejo práctico incluirás.

Responde JSON:
{{
  "title": "título max 65 chars, keyword exacta incluida",
  "description": "max 150 chars, genera curiosidad real",
  "keyword": "keyword long-tail de 3-6 palabras",
  "secondary_keywords": ["kw2", "kw3", "kw4"],
  "sections": [
    {{
      "heading": "Título de la sección",
      "what_to_cover": "Qué información CONCRETA y ÚTIL va aquí",
      "source_to_cite": "Nombre real del estudio o institución con año"
    }}
  ],
  "amazon_product": "nombre de UN producto relevante de Amazon (o null si no aplica)"
}}"""

    return call_ai(prompt, temperature=0.8)


def generate_content(category: str, topic_data: dict) -> dict:
    """Paso 2: Genera artículo completo de alta calidad."""
    sections = json.dumps(topic_data.get("sections", []), ensure_ascii=False, indent=2)
    amazon_product = topic_data.get("amazon_product")

    prompt = f"""Escribe un artículo de blog en español que sea REALMENTE ÚTIL para el lector.

TÍTULO: {topic_data['title']}
CATEGORÍA: {CATEGORY_NAMES.get(category, category)}
KEYWORD: {topic_data['keyword']}

PLAN DE SECCIONES:
{sections}

REGLAS DE CALIDAD (LEE ESTO CON ATENCIÓN):

1. PROHIBIDO el relleno. Cada frase debe aportar información nueva o un consejo aplicable.
   - MAL: "La nutrición es muy importante para nuestra salud y bienestar general"
   - BIEN: "Según un ensayo de 2019 en The Lancet con 195 países, una dieta pobre causa 11 millones de muertes al año — más que el tabaco"

2. DATOS REALES obligatorios. Cuando cites un estudio:
   - Nombre de la universidad o revista
   - Año de publicación
   - El dato concreto (cifra, porcentaje, resultado medible)
   - MAL: "Estudios demuestran que es beneficioso"
   - BIEN: "Un ensayo de la Universidad de Sydney (2021, publicado en BMJ) con 4.500 participantes encontró que 30 minutos de caminata diaria reduce el riesgo cardiovascular un 23%"

3. CONSEJOS PRÁCTICOS con pasos concretos.
   - MAL: "Es recomendable hacer ejercicio regularmente"
   - BIEN: "Empieza con 3 sesiones de 20 minutos por semana. Semana 1-2: caminata rápida. Semana 3-4: añade 5 minutos de trote. Mes 2: alterna 3 min trote + 2 min caminata x 6 series"

4. PREGUNTAS FRECUENTES: incluye 3-4 preguntas que la gente realmente busca en Google. Cada respuesta debe ser CONCRETA (mínimo 3-4 líneas con dato o consejo real, no una frase vaga).
   - MAL: "¿Es bueno el ayuno? Sí, tiene muchos beneficios para la salud"
   - BIEN: "¿Cuántas horas de ayuno se necesitan para quemar grasa? El cambio metabólico de glucosa a cetonas ocurre entre las 12-16 horas de ayuno según Mattson (NEJM, 2019). Para principiantes, el protocolo 16:8 es el más estudiado y seguro"

5. FORMATO:
   - Párrafos de 2-3 líneas máximo
   - Usa ## para secciones principales, ### para subsecciones
   - Negrita para conceptos clave
   - Listas cuando enumeres pasos o elementos
   - NO incluir título H1 (se pone automáticamente)
   - Incluir sección "## Preguntas frecuentes" con ### para cada pregunta
   - Terminar con "## Resumen práctico" con 5-6 bullets de acción concreta

6. LONGITUD: 1800-2200 palabras de contenido REAL (no relleno para llegar a un número).

{f'7. PRODUCTO AMAZON: Menciona "{amazon_product}" de forma natural donde sea relevante. Usa el formato [AMAZON:{amazon_product}] que será reemplazado por el link. No fuerces la mención si no encaja.' if amazon_product else ''}

Responde JSON:
{{
  "content": "artículo completo en markdown (sin H1)",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "sources": [
    "Apellido, A. et al. (año). Título del estudio. Revista, volumen",
    "Institución (año). Nombre del informe"
  ],
  "amazon_keywords": ["keyword búsqueda amazon si hay producto relevante"]
}}"""

    return call_ai(prompt, temperature=0.5)


def fetch_pexels_image(query: str) -> tuple[str, str]:
    """Busca imagen relevante en Pexels."""
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        return "", ""
    try:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": api_key},
            params={"query": query, "per_page": 3, "orientation": "landscape", "size": "medium"},
            timeout=10,
        )
        resp.raise_for_status()
        photos = resp.json().get("photos", [])
        if photos:
            return photos[0]["src"]["medium"], photos[0].get("alt", query)[:100]
    except Exception as e:
        log.warning("Pexels: %s", e)
    return "", ""


def inject_amazon_links(content: str, amazon_keywords: list[str]) -> str:
    """Reemplaza [AMAZON:x] con links reales."""
    def replace_amazon(match):
        product = match.group(1)
        search_query = product.replace(" ", "+")
        return f"[{product} en Amazon](https://www.amazon.es/s?k={search_query}&tag={AMAZON_TAG})"

    content = re.sub(r'\[AMAZON:([^\]]+)\]', replace_amazon, content)

    if amazon_keywords and "amazon.es" not in content:
        content += "\n\n---\n\n"
        content += "*Este artículo contiene enlaces de afiliado. Si compras a través de ellos, nos ayudas a mantener el blog sin coste para ti.*\n\n"
        for kw in amazon_keywords[:2]:
            search = kw.replace(" ", "+")
            content += f"- [{kw}](https://www.amazon.es/s?k={search}&tag={AMAZON_TAG})\n"

    return content


def add_internal_links(content: str, current_slug: str) -> str:
    """Añade 2-3 links a artículos existentes."""
    import random
    existing = []
    for md in BLOG_DIR.glob("*.md"):
        if md.stem == current_slug:
            continue
        text = md.read_text(encoding="utf-8")
        match = re.search(r'^title:\s*"?([^"\n]+)"?\s*$', text, re.MULTILINE)
        if match:
            existing.append({"slug": md.stem, "title": match.group(1).strip()})

    if not existing:
        return content

    links = random.sample(existing, min(3, len(existing)))
    section = "\n\n### Te puede interesar\n\n"
    for link in links:
        section += f"- [{link['title']}](/blog/{link['slug']})\n"

    if "## Resumen" in content:
        content = content.replace("## Resumen", section + "\n## Resumen")
    else:
        content += section

    return content


def write_markdown(category: str, topic_data: dict, content_data: dict) -> Path:
    """Escribe markdown final."""
    title = topic_data["title"][:70]
    slug = generate_slug(title)
    content = clean_markdown(content_data["content"])

    content = inject_amazon_links(content, content_data.get("amazon_keywords", []))
    content = add_internal_links(content, slug)

    image_url, image_alt = fetch_pexels_image(topic_data.get("keyword", title))

    reading_time = estimate_reading_time(content)
    sources = content_data.get("sources", [])
    tags = content_data.get("tags", [])
    today = date.today().isoformat()

    sources_yaml = "\n".join(f'  - "{s}"' for s in sources)
    tags_yaml = json.dumps(tags, ensure_ascii=False)

    image_lines = ""
    if image_url:
        image_lines = f'image: "{image_url}"\nimageAlt: "{image_alt}"'

    frontmatter = f"""---
title: "{title}"
description: "{topic_data['description'][:150]}"
pubDate: {today}
category: "{category}"
tags: {tags_yaml}
author: "{BRAND}"
readingTime: {reading_time}
{image_lines}
sources:
{sources_yaml}
draft: false
---"""

    BLOG_DIR.mkdir(parents=True, exist_ok=True)
    file_path = BLOG_DIR / f"{slug}.md"
    if file_path.exists():
        file_path = BLOG_DIR / f"{slug}-{today}.md"

    file_path.write_text(f"{frontmatter}\n\n{content}", encoding="utf-8")
    log.info("Escrito: %s (%d palabras)", file_path.name, len(content.split()))
    return file_path


def notify_telegram(message: str):
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
    except Exception:
        pass


def main():
    log.info("=== %s: Generando artículo de calidad ===", BRAND)

    plan = plan_topic()
    category = plan["category"]
    formula = plan["formula"]
    log.info("Categoría: %s", category)

    topic_data = research_topic(category, formula, plan["existing_titles"])
    log.info("Tema: %s", topic_data.get("title", "?"))

    content_data = generate_content(category, topic_data)
    word_count = len(content_data.get("content", "").split())
    log.info("Generado: %d palabras", word_count)

    file_path = write_markdown(category, topic_data, content_data)

    notify_telegram(
        f"<b>📝 {BRAND}</b>\n"
        f"{topic_data['title']}\n"
        f"{word_count} palabras | {category}"
    )

    log.info("=== Completado ===")
    return str(file_path)


if __name__ == "__main__":
    main()

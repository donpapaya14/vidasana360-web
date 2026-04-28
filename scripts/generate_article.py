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

    prompt = f"""Eres editor jefe de VidaSana360, un blog de SALUD PRÁCTICA en español.
ENFOQUE: pérdida de peso, nutrición diaria, ejercicio en casa, recetas saludables, dietas.
Tu lector quiere BAJAR DE PESO, comer mejor y hacer ejercicio HOY.
NO escribas sobre longevidad, envejecimiento, zonas azules ni biohacking — eso es otro blog.

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

    secondary_kws = ", ".join(topic_data.get("secondary_keywords", []))

    prompt = f"""Escribe un artículo de blog en español PROFESIONAL, COMPLETO y optimizado para SEO y GEO.

TÍTULO: {topic_data['title']}
CATEGORÍA: {CATEGORY_NAMES.get(category, category)}
KEYWORD PRINCIPAL: {topic_data['keyword']}
KEYWORDS SECUNDARIAS: {secondary_kws}

PLAN DE SECCIONES:
{sections}

=== REGLAS DE CALIDAD (OBLIGATORIAS) ===

1. PROHIBIDO el relleno. Cada frase aporta dato nuevo o consejo aplicable.
   - MAL: "La nutrición es muy importante para nuestra salud y bienestar general"
   - BIEN: "Según un ensayo de 2019 en The Lancet con 195 países, una dieta pobre causa 11 millones de muertes al año — más que el tabaco"

2. DATOS REALES con fuente completa. Mínimo 5 datos con fuente en todo el artículo.
   - Nombre de universidad/revista + año + dato concreto (cifra, %)
   - MAL: "Estudios demuestran que es beneficioso"
   - BIEN: "Un ensayo de la Universidad de Sydney (2021, BMJ) con 4.500 participantes encontró que 30 min de caminata diaria reduce riesgo cardiovascular un 23%"

3. CONSEJOS PRÁCTICOS numerados con pasos concretos.
   - Incluye cantidades, tiempos, frecuencias exactas
   - Al menos 2 listas de pasos o tablas comparativas en el artículo

4. ENLACES EXTERNOS de autoridad (mínimo 3):
   - Enlaza a fuentes reales cuando cites datos: OMS, universidades, revistas científicas, instituciones oficiales
   - Formato: [nombre fuente](URL real de la institución)
   - Ejemplo: [Organización Mundial de la Salud](https://www.who.int), [Mayo Clinic](https://www.mayoclinic.org)
   - Solo enlaces a dominios principales de instituciones reales, NO inventes URLs de estudios específicos

5. PREGUNTAS FRECUENTES: sección "## Preguntas frecuentes" con 5-6 preguntas reales de Google.
   - Cada ### pregunta con respuesta de 4-6 líneas con dato o consejo real
   - Empieza cada respuesta con una frase directa que responda la pregunta (optimización GEO)
   - MAL: "¿Es bueno el ayuno? Sí, tiene muchos beneficios"
   - BIEN: "¿Cuántas horas de ayuno para quemar grasa? El cambio metabólico de glucosa a cetonas ocurre entre 12-16 horas según Mattson (NEJM, 2019). Para principiantes, el protocolo 16:8 es el más estudiado..."

6. FORMATO:
   - Párrafos de 2-3 líneas máximo
   - ## para secciones principales, ### para subsecciones
   - **Negrita** para conceptos clave y cifras importantes
   - Listas y tablas markdown cuando compares opciones
   - NO incluir título H1 (se pone automáticamente)
   - Terminar con "## Resumen práctico" con 6-8 bullets de acción concreta

7. OPTIMIZACIÓN SEO/GEO:
   - Usa la keyword principal en el primer párrafo y en al menos 2 headings H2
   - Usa keywords secundarias de forma natural repartidas en el texto
   - Primer párrafo: respuesta directa y concisa a la intención de búsqueda (snippet de Google)
   - Incluye una tabla markdown comparativa o de datos cuando sea relevante
   - Las respuestas FAQ deben empezar respondiendo directamente (para featured snippets y citación por IAs)

8. LONGITUD: 2000-2800 palabras de contenido REAL y útil.

{f'9. PRODUCTOS AMAZON: Menciona "{amazon_product}" y 1-2 productos complementarios de forma natural. Usa [AMAZON:nombre producto] para cada uno. No fuerces si no encaja.' if amazon_product else '9. PRODUCTOS AMAZON: Si hay productos relevantes para el tema, menciona 2-3 de forma natural con [AMAZON:nombre producto]. Solo si encaja orgánicamente.'}

Responde JSON:
{{
  "content": "artículo completo en markdown (sin H1)",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8"],
  "sources": [
    "Apellido, A. et al. (año). Título del estudio. Revista",
    "Institución (año). Nombre del informe"
  ],
  "amazon_keywords": ["producto1", "producto2", "producto3"]
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
    """Añade 4-6 links internos: algunos contextuales + sección dedicada."""
    import random
    existing = []
    for md in BLOG_DIR.glob("*.md"):
        if md.stem == current_slug:
            continue
        text = md.read_text(encoding="utf-8")
        title_match = re.search(r'^title:\s*"?([^"\n]+)"?\s*$', text, re.MULTILINE)
        cat_match = re.search(r'^category:\s*"?(\w+)"?\s*$', text, re.MULTILINE)
        if title_match:
            existing.append({
                "slug": md.stem,
                "title": title_match.group(1).strip(),
                "category": cat_match.group(1) if cat_match else "",
            })

    if not existing:
        return content

    # Insertar 2 links contextuales dentro del texto
    shuffled = existing[:]
    random.shuffle(shuffled)
    contextual_count = 0
    paragraphs = content.split("\n\n")
    for i, para in enumerate(paragraphs):
        if contextual_count >= 2:
            break
        if para.startswith("#") or len(para) < 80 or "[" in para:
            continue
        if i > 2 and i < len(paragraphs) - 3 and shuffled:
            link = shuffled.pop(0)
            paragraphs[i] = para + f"\n\n> Relacionado: [{link['title']}](/blog/{link['slug']})"
            contextual_count += 1
    content = "\n\n".join(paragraphs)

    # Sección dedicada con 3-4 links más
    remaining = shuffled[:4] if shuffled else random.sample(existing, min(4, len(existing)))
    section = "\n\n### También te puede interesar\n\n"
    for link in remaining:
        section += f"- [{link['title']}](/blog/{link['slug']})\n"

    if "## Resumen" in content:
        content = content.replace("## Resumen", section + "\n## Resumen")
    else:
        content += section

    return content


def sanitize(text: str, max_len: int) -> str:
    """Trunca texto al límite, cortando en palabra. Quita comillas dobles internas."""
    text = text.replace('"', "'").strip()
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(" ", 1)[0]


def write_markdown(category: str, topic_data: dict, content_data: dict) -> Path:
    """Escribe markdown final con validación anti-fallos."""
    title = sanitize(topic_data.get("title", "Sin titulo"), 115)
    description = sanitize(topic_data.get("description", ""), 240)
    slug = generate_slug(title)
    content = clean_markdown(content_data.get("content", ""))

    # Validate: skip if content is too short (AI failed)
    if len(content.split()) < 600:
        log.warning("Artículo demasiado corto (%d palabras). Saltando.", len(content.split()))
        raise ValueError(f"Artículo demasiado corto: {len(content.split())} palabras")

    content = inject_amazon_links(content, content_data.get("amazon_keywords", []))
    content = add_internal_links(content, slug)

    image_url, image_alt = fetch_pexels_image(topic_data.get("keyword", title))

    reading_time = estimate_reading_time(content)

    # Validate sources — must have at least 1
    sources = content_data.get("sources", [])
    if not sources:
        sources = [f"{BRAND} (2026). Investigacion interna"]

    # Validate category
    valid_cats = list(CATEGORY_NAMES.keys())
    if category not in valid_cats:
        category = valid_cats[0]

    tags = content_data.get("tags", [])
    if not tags:
        tags = [category]
    today = date.today().isoformat()

    # Sanitize sources (no double quotes)
    sources_yaml = "\n".join(f'  - "{sanitize(s, 200)}"' for s in sources)
    tags_yaml = json.dumps(tags[:8], ensure_ascii=False)

    image_lines = ""
    if image_url:
        image_lines = f'image: "{image_url}"\nimageAlt: "{sanitize(image_alt, 100)}"'

    frontmatter = f"""---
title: "{title}"
description: "{description}"
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

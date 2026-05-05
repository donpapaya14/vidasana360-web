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
    "nutrition": "Nutrition",
    "fitness": "Fitness",
    "weight-loss": "Weight Loss",
    "wellness": "Wellness",
    "mental-health": "Mental Health",
}

AMAZON_TAG = os.getenv("AMAZON_TAG", "vladys-21")
SITE_URL = os.getenv("SITE_URL", "https://vidasana360-web.vercel.app")
BRAND = os.getenv("BRAND", "VidaSana360")


def research_topic(category: str, formula: str, existing_titles: list[str]) -> dict:
    """Paso 1: Elige tema con keyword long-tail y plan detallado."""
    existing_str = "\n".join(f"- {t}" for t in existing_titles[:20]) if existing_titles else "Ninguno"

    prompt = f"""You are editor-in-chief of HealthSpark, an English blog about PRACTICAL HEALTH.
FOCUS: weight loss, daily nutrition, home exercise, healthy recipes, diets.
Your reader wants to LOSE WEIGHT, eat better and exercise TODAY.
Do NOT write about longevity, aging, Blue Zones or biohacking — that is a different blog.

Your job: choose ONE topic for an article that is GENUINELY USEFUL for the reader.

ARTICLE TYPE TO CREATE: {formula}

ARTICLES THAT ALREADY EXIST (choose something DIFFERENT):
{existing_str}

INSTRUCTIONS:
1. Choose a VERY SPECIFIC topic (not generic). Bad: "benefits of exercise". Good: "Bulgarian split squat routine to strengthen knees after 40".
2. The title should be what someone would type in Google, 3-6 keywords.
3. Think of 5-6 sections where EACH ONE adds concrete information the reader did not know.
4. For each section, write WHAT specific data or practical advice you will include.

Respond JSON:
{{
  "title": "title max 65 chars, exact keyword included",
  "description": "max 150 chars, generates real curiosity",
  "keyword": "long-tail keyword of 3-6 words",
  "secondary_keywords": ["kw2", "kw3", "kw4"],
  "sections": [
    {{
      "heading": "Section title",
      "what_to_cover": "What CONCRETE and USEFUL information goes here",
      "source_to_cite": "Real study or institution name with year"
    }}
  ],
  "amazon_product": "name of ONE relevant Amazon product (or null if not applicable)"
}}"""

    return call_ai(prompt, temperature=0.8)


def generate_content(category: str, topic_data: dict) -> dict:
    """Paso 2: Genera artículo completo de alta calidad."""
    sections = json.dumps(topic_data.get("sections", []), ensure_ascii=False, indent=2)
    amazon_product = topic_data.get("amazon_product")

    secondary_kws = ", ".join(topic_data.get("secondary_keywords", []))

    prompt = f"""Write a PROFESSIONAL, COMPLETE English blog article optimized for SEO and GEO.

TITLE: {topic_data['title']}
CATEGORY: {CATEGORY_NAMES.get(category, category)}
MAIN KEYWORD: {topic_data['keyword']}
SECONDARY KEYWORDS: {secondary_kws}

SECTION PLAN:
{sections}

=== QUALITY RULES (MANDATORY) ===

1. NO filler. Every sentence adds new data or actionable advice.
   - BAD: "Nutrition is very important for our health and wellbeing"
   - GOOD: "According to a 2019 Lancet study across 195 countries, poor diet causes 11 million deaths per year — more than smoking"

2. REAL DATA with full source. Minimum 5 data points with source in the entire article.
   - University/journal name + year + specific figure (number, %)
   - BAD: "Studies show it is beneficial"
   - GOOD: "A University of Sydney trial (2021, BMJ) with 4,500 participants found 30 min of daily walking reduces cardiovascular risk by 23%"

3. PRACTICAL ADVICE with numbered steps.
   - Include exact quantities, times, frequencies
   - At least 2 numbered lists or comparison tables in the article

4. EXTERNAL AUTHORITY LINKS (minimum 3):
   - Link to real sources when citing data: WHO, universities, scientific journals, official institutions
   - Format: [source name](real institution URL)
   - Example: [World Health Organization](https://www.who.int), [Mayo Clinic](https://www.mayoclinic.org)
   - Only link to main domains of real institutions, do NOT invent specific study URLs

5. FAQ SECTION: "## Frequently Asked Questions" with 5-6 real Google questions.
   - Each ### question with 4-6 line answer with real data or advice
   - Start each answer with a direct sentence that answers the question (GEO optimization)
   - BAD: "Is fasting good? Yes, it has many benefits"
   - GOOD: "How many hours of fasting to burn fat? The metabolic switch from glucose to ketones occurs between 12-16 hours according to Mattson (NEJM, 2019). For beginners, the 16:8 protocol is the most studied..."

6. FORMAT:
   - Paragraphs of 2-3 lines maximum
   - ## for main sections, ### for subsections
   - **Bold** for key concepts and important figures
   - Markdown lists and tables when comparing options
   - Do NOT include H1 title (added automatically)
   - End with "## Practical Summary" with 6-8 concrete action bullets

7. SEO/GEO OPTIMIZATION:
   - Use main keyword in first paragraph and in at least 2 H2 headings
   - Use secondary keywords naturally throughout the text
   - First paragraph: direct and concise answer to search intent (Google snippet)
   - Include a comparison or data markdown table where relevant
   - FAQ answers should start by directly answering (for featured snippets and AI citation)

8. LENGTH: 2000-2800 words of REAL and useful content.

{f'9. AMAZON PRODUCTS: Mention "{amazon_product}" and 1-2 complementary products naturally. Use [AMAZON:product name] for each. Do not force it if it does not fit.' if amazon_product else '9. AMAZON PRODUCTS: If there are relevant products, mention 2-3 naturally with [AMAZON:product name]. Only if it fits organically.'}

Respond JSON:
{{
  "content": "full article in markdown (no H1)",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8"],
  "sources": [
    "Author, A. et al. (year). Study title. Journal",
    "Institution (year). Report name"
  ],
  "amazon_keywords": ["product1", "product2", "product3"]
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
        return f"[{product} en Amazon](https://www.amazon.com/s?k={search_query}&tag={AMAZON_TAG})"

    content = re.sub(r'\[AMAZON:([^\]]+)\]', replace_amazon, content)

    if amazon_keywords and "amazon.com" not in content:
        content += "\n\n---\n\n"
        content += "*Este artículo contiene enlaces de afiliado. Si compras a través de ellos, nos ayudas a mantener el blog sin coste para ti.*\n\n"
        for kw in amazon_keywords[:2]:
            search = kw.replace(" ", "+")
            content += f"- [{kw}](https://www.amazon.com/s?k={search}&tag={AMAZON_TAG})\n"

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
    section = "\n\n### You might also like\n\n"
    for link in remaining:
        section += f"- [{link['title']}](/blog/{link['slug']})\n"

    if "## Practical Summary" in content:
        content = content.replace("## Practical Summary", section + "\n## Practical Summary")
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
        sources = [f"{BRAND} (2026). Internal research"]

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

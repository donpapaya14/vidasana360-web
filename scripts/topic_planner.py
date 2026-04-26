"""
Planifica temas evitando duplicados y rotando categorías.
Lee artículos existentes en src/content/blog/ para evitar repetir.
"""

import os
import random
import re
from pathlib import Path

BLOG_DIR = Path(__file__).parent.parent / "src" / "content" / "blog"

CATEGORIES = ["nutricion", "ejercicio", "mente", "longevidad", "recetas"]

ARTICLE_FORMULAS = {
    "nutricion": [
        "Análisis completo de un alimento con 3+ beneficios respaldados por estudios reales (nombre universidad, año, revista)",
        "Desmontaje de un mito nutricional común con evidencia científica concreta de al menos 2 estudios",
        "Guía de un patrón alimentario específico (mediterránea, DASH, etc.) con plan semanal y base científica",
        "Comparativa nutricional de 2 alimentos populares con datos reales de composición y estudios",
        "Los X nutrientes más importantes para [objetivo específico] con fuentes alimentarias y cantidades",
        "Alimentos que aceleran/ralentizan el metabolismo con datos metabólicos de estudios reales",
        "Guía de suplementos para [objetivo]: cuáles funcionan y cuáles no, según metaanálisis recientes",
    ],
    "ejercicio": [
        "Rutina completa de X minutos para [objetivo] con progresión semanal y respaldo científico",
        "Comparativa de tipos de ejercicio (HIIT vs cardio, yoga vs pesas) con datos de estudios reales",
        "Errores comunes en el gimnasio/ejercicio que causan lesiones o reducen resultados, con correcciones",
        "Ejercicios específicos para [problema común: dolor espalda, rodillas, etc.] avalados por fisioterapia",
        "Cómo empezar a hacer ejercicio desde cero: guía progresiva de 4 semanas con base científica",
        "Beneficios de caminar X pasos al día con datos de estudios epidemiológicos reales",
    ],
    "mente": [
        "Técnica de gestión del estrés respaldada por estudios de neurociencia con pasos concretos",
        "Hábitos de sueño que mejoran la salud mental: datos de estudios con cifras de mejora medibles",
        "Cómo la meditación afecta al cerebro: estudios de neuroimagen reales con nombres de investigadores",
        "Alimentos que afectan al estado de ánimo: eje intestino-cerebro con estudios recientes",
        "Señales de burnout y estrategias de recuperación basadas en psicología organizacional",
        "Técnicas de productividad con respaldo en neurociencia: Pomodoro, deep work, etc.",
    ],
    "longevidad": [
        "Hábitos de las zonas azules con datos de los estudios de Dan Buettner y National Geographic",
        "Biomarcadores de envejecimiento: qué medir y por qué, según estudios de gerontología",
        "Ayuno intermitente y longevidad: evidencia actual de estudios en humanos",
        "Ejercicio y esperanza de vida: cuántos años añade cada tipo según estudios epidemiológicos",
        "Suplementos anti-envejecimiento: evidencia real vs marketing (NMN, resveratrol, etc.)",
        "Relaciones sociales y longevidad: datos del Harvard Study of Adult Development",
    ],
    "recetas": [
        "Receta antiinflamatoria con lista de ingredientes, pasos y explicación nutricional de cada componente",
        "Desayuno saludable en 10 minutos con macros y beneficios respaldados por nutrición",
        "Meal prep semanal saludable: 5 comidas con lista de compras y valores nutricionales",
        "Receta alta en proteína sin carne con perfil de aminoácidos y alternativas",
        "Snacks saludables para [objetivo: perder peso, ganar músculo, etc.] con valores calóricos reales",
        "Recetas de cena ligera para mejorar el sueño con nutrientes específicos que ayudan",
    ],
}


def get_existing_titles() -> set[str]:
    """Lee títulos de artículos existentes del frontmatter."""
    titles = set()
    if not BLOG_DIR.exists():
        return titles

    for md_file in BLOG_DIR.glob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        match = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', content, re.MULTILINE)
        if match:
            titles.add(match.group(1).lower().strip())
    return titles


def get_category_counts() -> dict[str, int]:
    """Cuenta artículos por categoría."""
    counts = {cat: 0 for cat in CATEGORIES}
    if not BLOG_DIR.exists():
        return counts

    for md_file in BLOG_DIR.glob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        match = re.search(r'^category:\s*["\']?(\w+)["\']?\s*$', content, re.MULTILINE)
        if match and match.group(1) in counts:
            counts[match.group(1)] += 1
    return counts


def pick_category() -> str:
    """Elige categoría con menos artículos (rotación equilibrada)."""
    counts = get_category_counts()
    min_count = min(counts.values())
    least_covered = [cat for cat, count in counts.items() if count == min_count]
    return random.choice(least_covered)


def pick_formula(category: str) -> str:
    """Elige fórmula aleatoria para la categoría."""
    formulas = ARTICLE_FORMULAS.get(category, ARTICLE_FORMULAS["nutricion"])
    return random.choice(formulas)


def plan_topic() -> dict:
    """Devuelve categoría y fórmula para el próximo artículo."""
    category = pick_category()
    formula = pick_formula(category)
    existing = get_existing_titles()

    return {
        "category": category,
        "formula": formula,
        "existing_titles": list(existing)[:20],  # Para contexto al AI
        "existing_count": len(existing),
    }

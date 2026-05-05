"""
Plans topics avoiding duplicates and rotating categories.
Reads existing articles in src/content/blog/ to avoid repetition.
"""

import random
import re
from pathlib import Path

BLOG_DIR = Path(__file__).parent.parent / "src" / "content" / "blog"

CATEGORIES = ["nutrition", "fitness", "weight-loss", "wellness", "mental-health"]

ARTICLE_FORMULAS = {
    "nutrition": [
        "Complete analysis of one food with 3+ benefits backed by real studies (university name, year, journal)",
        "Debunking a common nutrition myth with concrete scientific evidence from at least 2 studies",
        "Guide to a specific dietary pattern (Mediterranean, DASH, etc.) with weekly plan and science",
        "Nutritional comparison of 2 popular foods with real composition data and studies",
        "Most important nutrients for [specific goal] with food sources and amounts",
        "Foods that speed up or slow down metabolism with metabolic data from real studies",
        "Supplements for [goal]: which ones work and which don't according to recent meta-analyses",
    ],
    "fitness": [
        "Complete X-minute routine for [goal] with weekly progression and scientific backing",
        "Comparison of exercise types (HIIT vs cardio, yoga vs weights) with real study data",
        "Common gym/exercise mistakes that cause injury or reduce results with corrections",
        "Exercises for [common problem: back pain, knees, etc.] endorsed by physiotherapy",
        "How to start exercising from zero: 4-week progressive guide with scientific basis",
        "Benefits of walking X steps per day with data from real epidemiological studies",
    ],
    "weight-loss": [
        "Science-backed fat loss method most people ignore: specific mechanism and study result",
        "Common diet mistake that causes 80% of people to fail: specific psychological mechanism",
        "One food that blocks fat absorption according to nutrition research: specific compound and amount",
        "Intermittent fasting variant with best evidence for fat loss: specific protocol and result",
        "Caloric deficit explained with real example: how to calculate and maintain it without hunger",
        "Why the scale doesn't move: specific scientific reasons and what to do instead",
    ],
    "wellness": [
        "Stress management technique backed by neuroscience studies with concrete steps",
        "Sleep habits that improve health: data from studies with measurable improvement figures",
        "Morning habit that boosts energy all day: specific neuroscience explanation and timing",
        "Cold exposure benefits: specific protocol, measurable metabolic effects and evidence",
        "Gut health and overall wellness: specific bacteria, dietary changes and evidence",
    ],
    "mental-health": [
        "How meditation affects the brain: real neuroimaging studies with researcher names",
        "Foods that affect mood: gut-brain axis with recent studies",
        "Burnout signs and recovery strategies based on organizational psychology",
        "Productivity techniques with neuroscience backing: Pomodoro, deep work, etc.",
        "Anxiety reduction techniques with measurable cortisol impact and specific methods",
    ],
}


def get_existing_titles() -> set[str]:
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
    counts = {cat: 0 for cat in CATEGORIES}
    if not BLOG_DIR.exists():
        return counts
    for md_file in BLOG_DIR.glob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        match = re.search(r'^category:\s*["\']?([^"\'\n]+)["\']?\s*$', content, re.MULTILINE)
        if match and match.group(1).strip() in counts:
            counts[match.group(1).strip()] += 1
    return counts


def pick_category() -> str:
    counts = get_category_counts()
    min_count = min(counts.values())
    least_covered = [cat for cat, count in counts.items() if count == min_count]
    return random.choice(least_covered)


def pick_formula(category: str) -> str:
    formulas = ARTICLE_FORMULAS.get(category, list(ARTICLE_FORMULAS.values())[0])
    return random.choice(formulas)


def plan_topic() -> dict:
    category = pick_category()
    formula = pick_formula(category)
    existing = get_existing_titles()
    return {
        "category": category,
        "formula": formula,
        "existing_titles": list(existing)[:20],
        "existing_count": len(existing),
    }

import json
import os

TAXONOMY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "taxonomy", "skills_taxonomy.json"
)

_taxonomy_cache = None
_reverse_cache = None

# Qualifiers a resume may put in front of a skill. "Weak" ones mean the candidate is
# telling us their level is low, so the skill only earns partial credit.
WEAK_QUALIFIERS = (
    "basic", "beginner", "limited", "elementary", "novice", "familiar with",
    "familiarity with", "exposure to", "learning", "fundamentals of",
)
NEUTRAL_QUALIFIERS = (
    "advanced", "expert", "expertise in", "proficient in", "proficient", "strong",
    "intermediate", "working knowledge of", "hands-on",
)


def load_taxonomy() -> dict:
    """
    Loads a local skills taxonomy mapping synonyms/variants to a canonical skill name.
    Example: {"js": "javascript", "reactjs": "react", "postgres": "postgresql"}
    """
    global _taxonomy_cache
    if _taxonomy_cache is not None:
        return _taxonomy_cache

    if not os.path.exists(TAXONOMY_PATH):
        _taxonomy_cache = {}
        return _taxonomy_cache

    with open(TAXONOMY_PATH, "r", encoding="utf-8") as f:
        _taxonomy_cache = json.load(f)

    return _taxonomy_cache


def _reverse_map() -> dict[str, set[str]]:
    global _reverse_cache
    if _reverse_cache is None:
        rev: dict[str, set[str]] = {}
        for alias, canonical in load_taxonomy().items():
            rev.setdefault(canonical, set()).add(alias)
            rev[canonical].add(canonical)
        _reverse_cache = rev
    return _reverse_cache


def split_qualifier(skill: str) -> tuple[str, bool]:
    """
    'Basic Java' -> ('java', True); 'Strong Python' -> ('python', False); 'Docker' -> ('docker', False).
    Returns (skill without qualifier, is_weak).
    """
    cleaned = " ".join(skill.strip().lower().split())
    for q in WEAK_QUALIFIERS:
        if cleaned.startswith(q + " "):
            return cleaned[len(q) + 1:].strip(), True
    for q in NEUTRAL_QUALIFIERS:
        if cleaned.startswith(q + " "):
            return cleaned[len(q) + 1:].strip(), False
    return cleaned, False


def normalize_skill(skill: str) -> str:
    """
    Maps a raw skill string to its canonical form: strips proficiency qualifiers,
    then applies the taxonomy. Falls back to the lowercased text if unknown.
    """
    base, _ = split_qualifier(skill)
    taxonomy = load_taxonomy()
    return taxonomy.get(base, base)


def is_weak_skill(skill: str) -> bool:
    return split_qualifier(skill)[1]


def is_known_skill(canonical: str) -> bool:
    return canonical in _reverse_map()


def aliases_for(canonical: str) -> set[str]:
    """All spellings that count as the same skill (always includes the canonical name)."""
    return set(_reverse_map().get(canonical, set())) | {canonical}


def normalize_skill_list(skills: list[str]) -> list[str]:
    """Normalizes a list of skills and removes duplicates while preserving order."""
    seen = set()
    result = []
    for skill in skills:
        if not isinstance(skill, str) or not skill.strip():
            continue
        normalized = normalize_skill(skill)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result

import re
from functools import lru_cache

# A term only matches when it is not glued to other alphanumerics / skill symbols.
# This stops "java" matching inside "javascript", "c" inside "c++", "r" inside "r&d".
_EDGE = r"A-Za-z0-9+#&"
_LEFT = rf"(?<![{_EDGE}])"
_RIGHT = rf"(?![{_EDGE}])"


@lru_cache(maxsize=2048)
def _pattern(term: str) -> re.Pattern:
    return re.compile(_LEFT + re.escape(term) + _RIGHT, re.IGNORECASE)


@lru_cache(maxsize=256)
def _short_pattern(term: str) -> re.Pattern:
    # Very short alphabetic tokens (C, R, Go, ML) are ambiguous as plain words, so require
    # the capitalised/upper form to appear.
    forms = {term.upper(), term.capitalize()}
    alt = "|".join(re.escape(f) for f in sorted(forms))
    return re.compile(_LEFT + f"(?:{alt})" + _RIGHT)


def _pat(term: str) -> re.Pattern:
    if len(term) <= 2 and term.isalpha():
        return _short_pattern(term)
    return _pattern(term)


def contains_term(text: str, term: str) -> bool:
    term = (term or "").strip()
    if not term or not text:
        return False
    return bool(_pat(term).search(text))


def count_term(text: str, term: str) -> int:
    term = (term or "").strip()
    if not term or not text:
        return 0
    return len(_pat(term).findall(text))


def contains_any(text: str, terms) -> bool:
    return any(contains_term(text, t) for t in terms)


def count_any(text: str, terms) -> int:
    return sum(count_term(text, t) for t in terms)

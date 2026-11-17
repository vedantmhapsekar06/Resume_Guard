"""
Deterministic relevance scoring: how relevant is a piece of resume text to a job?

relevance = blend of (a) share of the JD's required skills that the text actually uses
(exact, word-boundary, taxonomy-aware matching) and (b) embedding similarity to the JD.
No LLM is involved, so the same input always gives the same score.
"""
import logging
import math
from typing import Optional

import numpy as np

from backend.core import embeddings
from backend.core.similarity import rescale_cosine
from backend.core.resume_text import bullet_items, project_texts, role_texts
from backend.core.taxonomy import normalize_skill_list, aliases_for
from backend.core.text_match import contains_any
from backend.models.schemas import JDProfile, ResumeProfile

logger = logging.getLogger(__name__)

# A text that uses >= this share of the required skills gets full skill-overlap credit
# (a single role rarely mentions every required skill).
_FULL_OVERLAP_SHARE = 0.4


def required_canonical(jd: JDProfile) -> list[str]:
    return normalize_skill_list(jd.required_skills)


def jd_query_text(jd: JDProfile) -> str:
    parts = [jd.role_title]
    if jd.responsibilities:
        parts.append("Responsibilities: " + "; ".join(jd.responsibilities[:10]))
    if jd.required_skills:
        parts.append("Skills: " + ", ".join(jd.required_skills[:20]))
    return ". ".join(parts)


def skill_overlap(text: str, required: list[str]) -> Optional[float]:
    """0..1 share of required skills used in `text`, saturating at _FULL_OVERLAP_SHARE. None if no skills."""
    if not required:
        return None
    hits = sum(1 for s in required if contains_any(text, aliases_for(s)))
    return min(1.0, (hits / len(required)) / _FULL_OVERLAP_SHARE)


def _embedding_relevance(texts: list[str], jd: JDProfile) -> Optional[list[float]]:
    try:
        vecs = embeddings.embed_texts([jd_query_text(jd)] + texts)
        sims = vecs[1:] @ vecs[0]
        return [rescale_cosine(float(s)) for s in sims]
    except Exception as exc:   # model missing / not downloaded etc. - degrade, don't crash
        logger.warning("Embedding relevance unavailable, using skill overlap only: %s", exc)
        return None


def batch_relevance(texts: list[str], jd: JDProfile) -> list[float]:
    """Relevance 0-100 for each text against the JD."""
    if not texts:
        return []
    required = required_canonical(jd)
    emb = _embedding_relevance(texts, jd)

    scores = []
    for i, text in enumerate(texts):
        overlap = skill_overlap(text, required)
        e = emb[i] if emb is not None else None
        if overlap is not None and e is not None:
            val = 0.6 * overlap * 100 + 0.4 * e
        elif overlap is not None:
            val = overlap * 100
        elif e is not None:
            val = e
        else:
            val = 0.0
        scores.append(round(val, 1))
    return scores


def jd_resume_similarity(jd: JDProfile, resume: ResumeProfile) -> Optional[float]:
    """
    Real resume<->JD semantic fit (0-100): for every JD requirement (responsibility or required
    skill), find its best-matching resume statement, then average. Returns None if embeddings
    are unavailable so the caller can drop this component instead of faking a number.
    """
    requirements = list(jd.responsibilities[:10]) + [
        f"Experience with {s}" for s in jd.required_skills[:15]
    ]
    requirements = [r for r in requirements if isinstance(r, str) and r.strip()]
    if not requirements:
        requirements = [jd.role_title]

    items = [i["text"] for i in bullet_items(resume)]
    items += project_texts(resume) + role_texts(resume)
    if resume.skills_listed:
        items.append("Skills: " + ", ".join(str(s) for s in resume.skills_listed))
    items = [t for t in items if t.strip()]
    if not items:
        return 0.0

    try:
        vecs = embeddings.embed_texts(requirements + items)
    except Exception as exc:
        logger.warning("Semantic similarity unavailable: %s", exc)
        return None

    req_v, item_v = vecs[: len(requirements)], vecs[len(requirements):]
    best = (req_v @ item_v.T).max(axis=1)
    return round(float(np.mean([rescale_cosine(float(c)) for c in best])), 2)

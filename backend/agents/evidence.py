"""
Evidence agent (fully deterministic - no LLM).

Selects the resume bullets that best support THIS job, straight from the parsed resume, so a
cited bullet can never be invented. Score = how much of the required skill set is demonstrated
(50%) + how relevant the best bullets are (30%) + how many of them are quantified (20%).
"""
import re

from backend.config import EVIDENCE_MIN_RELEVANCE
from backend.core.relevance import batch_relevance, required_canonical
from backend.core.resume_text import bullet_items, evidence_corpus
from backend.core.taxonomy import aliases_for
from backend.core.text_match import contains_any
from backend.models.schemas import JDProfile, ResumeProfile, EvidenceResult

MAX_BULLETS = 6

# A *quantified outcome*, not just any digit: "Python 3", "3 years", "Q3" don't count.
_METRIC = re.compile(
    r"(\d+(?:\.\d+)?\s?%)"                                   # 35%
    r"|([$₹€£]\s?\d)"                                         # $5, ₹2L
    r"|(\b\d+(?:\.\d+)?\s?[xX]\b)"                            # 3x
    r"|(\b\d[\d,]*(?:\.\d+)?\s?[kKmMbB]\+?(?![A-Za-z0-9]))"   # 10k, 2M
    r"|(\b\d[\d,]*\+?\s+(?:users|customers|clients|requests|records|rows|transactions|endpoints|"
    r"apis|services|models|tests|engineers|members|people|students|candidates|ms|seconds|hours)\b)",
    re.IGNORECASE,
)


def has_metric(text: str) -> bool:
    return bool(_METRIC.search(text))


def find_evidence(jd: JDProfile, resume: ResumeProfile) -> EvidenceResult:
    items = bullet_items(resume)
    if not items:
        return EvidenceResult(
            supporting_bullets=[],
            quality_note="No experience or project bullets could be read from this resume.",
            score=0.0,
        )

    texts = [i["text"] for i in items]
    relevance = batch_relevance(texts, jd)

    ranked = sorted(
        range(len(items)),
        key=lambda i: relevance[i] + (10 if has_metric(texts[i]) else 0),
        reverse=True,
    )
    chosen = [i for i in ranked if relevance[i] >= EVIDENCE_MIN_RELEVANCE][:MAX_BULLETS]

    required = required_canonical(jd)
    corpus = evidence_corpus(resume)
    if required:
        coverage = sum(1 for s in required if contains_any(corpus, aliases_for(s))) / len(required)
    else:
        coverage = 0.5   # nothing to cover - neutral

    if chosen:
        strength = sum(relevance[i] for i in chosen) / len(chosen)
        metric_ratio = sum(1 for i in chosen if has_metric(texts[i])) / len(chosen)
    else:
        strength = metric_ratio = 0.0

    score = 0.5 * coverage * 100 + 0.3 * strength + 0.2 * metric_ratio * 100

    if not chosen:
        note = "No bullets were clearly relevant to this job."
    else:
        quantified = sum(1 for i in chosen if has_metric(texts[i]))
        note = (
            f"{len(chosen)} relevant bullet(s), {quantified} with quantified results; "
            f"{round(coverage * 100)}% of required skills demonstrated in experience/projects."
        )

    return EvidenceResult(
        supporting_bullets=[texts[i] for i in chosen],
        quality_note=note,
        score=round(max(0.0, min(100.0, score)), 2),
    )

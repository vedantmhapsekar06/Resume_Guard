"""
Skills Matching agent (fully deterministic).

For every JD skill the resume gets one of four statuses:
  evidenced   - used in a work bullet / project (word-boundary, taxonomy-aware match)   -> full credit
  listed_only - appears only in the Skills list, nothing demonstrates it               -> partial credit
  weak        - the resume itself qualifies it ("Basic Java", "limited ...")            -> partial credit
  missing     - not found anywhere                                                       -> no credit
Listing every keyword with no supporting experience therefore scores poorly.
"""
import logging

from backend.config import (
    FUZZY_SKILL_THRESHOLD,
    LISTED_ONLY_CREDIT,
    WEAK_SKILL_CREDIT,
)
from backend.core import embeddings
from backend.core.resume_text import evidence_corpus
from backend.core.similarity import compute_similarity_matrix
from backend.core.taxonomy import (
    aliases_for,
    is_known_skill,
    is_weak_skill,
    normalize_skill,
    normalize_skill_list,
)
from backend.core.text_match import contains_any, count_any
from backend.models.schemas import JDProfile, ResumeProfile, SkillsMatchResult

logger = logging.getLogger(__name__)

_CREDIT = {
    "evidenced": 1.0,
    "listed_only": LISTED_ONLY_CREDIT,
    "weak": WEAK_SKILL_CREDIT,
    "missing": 0.0,
}


def match_skills(jd: JDProfile, resume: ResumeProfile) -> SkillsMatchResult:
    required = normalize_skill_list(jd.required_skills)
    preferred = [s for s in normalize_skill_list(jd.preferred_skills) if s not in required]

    # canonical listed skill -> True if the resume only ever mentions it with a weak qualifier
    listed: dict[str, bool] = {}
    for raw in resume.skills_listed:
        if not isinstance(raw, str) or not raw.strip():
            continue
        canon = normalize_skill(raw)
        if canon:
            listed[canon] = listed.get(canon, True) and is_weak_skill(raw)

    corpus = evidence_corpus(resume)
    use_raw_fallback = not corpus.strip()   # extraction found no bullets/projects at all

    def evidenced(skill: str) -> bool:
        aliases = aliases_for(skill)
        if contains_any(corpus, aliases):
            return True
        # Fallback when structured extraction failed: a skill mentioned at least twice in the raw
        # text is being used somewhere besides the Skills list.
        return use_raw_fallback and count_any(resume.raw_text, aliases) >= 2

    # Embedding fallback only for JD skills that are neither listed nor demonstrated.
    unresolved = [s for s in required + preferred if s not in listed and not evidenced(s)]
    fuzzy_hits = _fuzzy_matches(unresolved, list(listed))

    def status(skill: str) -> str:
        if evidenced(skill):
            return "evidenced"
        if skill in listed:
            return "weak" if listed[skill] else "listed_only"
        if skill in fuzzy_hits:
            return "weak" if listed[fuzzy_hits[skill]] else "listed_only"
        return "missing"

    req_status = {s: status(s) for s in required}
    pref_status = {s: status(s) for s in preferred}

    def pick(statuses: dict, wanted: set) -> list[str]:
        return [s for s, st in statuses.items() if st in wanted]

    unsupported_all = [c for c in listed if not evidenced(c)]

    return SkillsMatchResult(
        matched_required=pick(req_status, {"evidenced", "listed_only", "weak"}),
        matched_preferred=pick(pref_status, {"evidenced", "listed_only", "weak"}),
        missing_required=pick(req_status, {"missing"}),
        missing_preferred=pick(pref_status, {"missing"}),
        evidenced_required=pick(req_status, {"evidenced"}),
        evidenced_preferred=pick(pref_status, {"evidenced"}),
        unsupported_required=pick(req_status, {"listed_only"}),
        weak_required=pick(req_status, {"weak"}),
        unsupported_skills=unsupported_all,
        score=_compute_skills_score(req_status, pref_status),
    )


def _fuzzy_matches(candidates: list[str], listed: list[str]) -> dict[str, str]:
    """
    Maps a JD skill to a listed skill when their embeddings are nearly identical
    (e.g. 'rest apis' ~ 'restful api'). One batched embedding call. Two DIFFERENT known skills
    (java vs javascript, mysql vs postgresql) never match each other, however close they embed.
    """
    if not candidates or not listed:
        return {}
    try:
        vecs = embeddings.embed_texts(candidates + listed)
    except Exception as exc:
        logger.warning("Fuzzy skill matching unavailable: %s", exc)
        return {}

    sims = compute_similarity_matrix(vecs[: len(candidates)], vecs[len(candidates):])
    out: dict[str, str] = {}
    for i, c in enumerate(candidates):
        best_j, best = None, 0.0
        for j, l in enumerate(listed):
            if c != l and is_known_skill(c) and is_known_skill(l):
                continue
            if sims[i][j] * 100 >= FUZZY_SKILL_THRESHOLD and sims[i][j] > best:
                best_j, best = j, sims[i][j]
        if best_j is not None:
            out[c] = listed[best_j]
    return out


def _credit_pct(statuses: dict[str, str]) -> float:
    if not statuses:
        return 0.0
    return sum(_CREDIT[s] for s in statuses.values()) / len(statuses) * 100


def _compute_skills_score(req_status: dict[str, str], pref_status: dict[str, str]) -> float:
    """
    Required skills carry 90% of the skills score when preferred skills exist (100% otherwise);
    preferred skills carry 10%. Credit per skill comes from _CREDIT, so demonstrated skills
    count fully and keyword-only skills count half.
    """
    if not req_status and not pref_status:
        return 50.0   # JD gave nothing to match on - neutral rather than free points
    if not req_status:
        return round(_credit_pct(pref_status), 2)
    if not pref_status:
        return round(_credit_pct(req_status), 2)
    return round(0.9 * _credit_pct(req_status) + 0.1 * _credit_pct(pref_status), 2)

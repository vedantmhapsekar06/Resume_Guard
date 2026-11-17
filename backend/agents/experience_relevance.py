"""
Experience & Relevance agent (fully deterministic - no LLM).

- total_years      : union of all work periods (overlapping jobs counted once)
- relevant_years   : union of the periods of roles that are relevant to THIS job
- score            : relevant years vs the JD minimum, blended with how relevant the work is
- risk_flags       : date gaps / overlaps only (never model opinions)
"""
from backend.config import ROLE_RELEVANCE_THRESHOLD
from backend.core.date_utils import (
    calculate_duration_years,
    detect_gaps_and_overlaps,
    total_years,
)
from backend.core.relevance import batch_relevance
from backend.core.resume_text import project_texts, role_texts
from backend.models.schemas import JDProfile, ResumeProfile, ExperienceResult

# With no paid experience, relevant projects count, but for less than real work experience.
_PROJECT_DISCOUNT = 0.7
_YEARS_WEIGHT = 0.6
_RELEVANCE_WEIGHT = 0.4


def analyze_experience(jd: JDProfile, resume: ResumeProfile) -> ExperienceResult:
    jobs = resume.work_history
    risk_flags = detect_gaps_and_overlaps(jobs)

    total = total_years(jobs)
    dates_unparseable = bool(jobs) and total == 0.0
    if dates_unparseable and resume.total_experience_years:
        try:   # last resort only: dates unreadable, fall back to the LLM's estimate
            total = round(float(resume.total_experience_years), 1)
        except (TypeError, ValueError):
            pass

    role_rel = batch_relevance(role_texts(resume), jd)
    relevant_jobs = [j for j, r in zip(jobs, role_rel) if r >= ROLE_RELEVANCE_THRESHOLD]

    if dates_unparseable:
        share = len(relevant_jobs) / len(jobs) if jobs else 0.0
        relevant_years = round(total * share, 1)
    else:
        relevant_years = total_years(relevant_jobs)

    # Relevance of the work itself, weighted by how long each role lasted
    notes = []
    if jobs:
        weights = []
        for job, rel in zip(jobs, role_rel):
            years = calculate_duration_years(job.get("start_date", ""), job.get("end_date", ""))
            weights.append(max(years, 0.25))
            tag = "Relevant" if rel >= ROLE_RELEVANCE_THRESHOLD else "Low relevance"
            notes.append(
                f"{tag}: {job.get('title') or 'Role'} @ {job.get('company') or 'Company'} "
                f"({years} yrs, {rel:.0f}/100 match to this job)"
            )
        relevance_score = sum(r * w for r, w in zip(role_rel, weights)) / sum(weights)
    else:
        proj_rel = batch_relevance(project_texts(resume), jd)
        relevance_score = (sum(proj_rel) / len(proj_rel)) * _PROJECT_DISCOUNT if proj_rel else 0.0
        if proj_rel:
            notes.append(f"No work history; {len(proj_rel)} project(s) considered at reduced weight")

    min_years = _to_float(jd.min_experience_years)
    if min_years and min_years > 0:
        years_score = min(1.0, relevant_years / min_years) * 100
        meets_minimum = relevant_years >= min_years - 0.05
        score = _YEARS_WEIGHT * years_score + _RELEVANCE_WEIGHT * relevance_score
    else:
        meets_minimum = True
        score = relevance_score

    penalty = min(len(risk_flags) * 8, 30)
    score = max(0.0, min(100.0, score - penalty))

    return ExperienceResult(
        total_years=total,
        relevant_years=relevant_years,
        meets_minimum=meets_minimum,
        relevance_notes=notes,
        risk_flags=risk_flags,
        score=round(score, 2),
    )


def _to_float(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None

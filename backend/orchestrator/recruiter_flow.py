from backend.agents.jd_analyzer import analyze_jd
from backend.agents.resume_analyzer import analyze_resume
from backend.agents.skills_matching import match_skills
from backend.agents.experience_relevance import analyze_experience
from backend.agents.evidence import find_evidence
from backend.agents.judge import judge_candidate
import logging
import os
import re
from backend.core.document_parser import extract_text
from backend.db.database import get_connection

logger = logging.getLogger(__name__)

_UPLOAD_PREFIX = re.compile(r"^[0-9a-f]{32}_")


def display_name(file_path: str) -> str:
    """File name shown to the user: basename without the random upload prefix."""
    return _UPLOAD_PREFIX.sub("", os.path.basename(file_path.replace("\\", "/")))


def run_recruiter_screening(jd_text: str, resume_file_paths: list[str]) -> dict:
    """
    Runs the full recruiter pipeline:
    JD Analyzer -> for each resume: Resume Analyzer -> Skills Matching ->
    Experience & Relevance -> Evidence -> Judge.
    Persists results to the DB and returns a ranked shortlist.
    """
    jd = analyze_jd(jd_text)

    screening_id = _create_screening_record(jd_text, mode="recruiter")

    candidates = []
    errors = []
    for file_path in resume_file_paths:
        try:
            candidates.append(_screen_single_candidate(jd, file_path, screening_id))
        except Exception as exc:   # one unreadable resume must not discard the whole batch
            logger.exception("Failed to screen %s", file_path)
            # Only our own ValueErrors are safe/meaningful to show; anything else may contain server paths.
            reason = (
                str(exc).splitlines()[0][:200]
                if isinstance(exc, ValueError) and str(exc)
                else "The file could not be read or processed."
            )
            errors.append({"filename": display_name(file_path), "error": reason})
            candidates.append(_error_candidate(file_path, reason))

    # Rank by final_score, descending (failed files sink to the bottom with score 0)
    candidates.sort(key=lambda c: c["final_score"], reverse=True)

    return {
        "screening_id": screening_id,
        "jd_profile": jd.model_dump(),
        "candidates": candidates,
        "errors": errors,
    }


def _error_candidate(file_path: str, reason: str) -> dict:
    """Placeholder row so the UI still lists the file instead of the batch failing."""
    return {
        "filename": display_name(file_path),
        "candidate_name": None,
        "final_score": 0.0,
        "fit_label": "No Fit",
        "priority_label": "Low",
        "summary": f"Could not be processed: {reason}",
        "skills": {"matched_required": [], "missing_required": []},
        "experience": {},
        "evidence": {"supporting_bullets": []},
    }


def _screen_single_candidate(jd, file_path: str, screening_id: int) -> dict:
    resume_text = extract_text(file_path)
    resume = analyze_resume(resume_text)

    skills_result = match_skills(jd, resume)
    experience_result = analyze_experience(jd, resume)
    evidence_result = find_evidence(jd, resume)
    verdict = judge_candidate(jd, resume, skills_result, experience_result, evidence_result)

    _save_candidate_record(
        screening_id, file_path, resume, skills_result, experience_result, evidence_result, verdict
    )

    return {
        "filename": display_name(file_path),
        "candidate_name": resume.candidate_name,
        "final_score": verdict.final_score,
        "fit_label": verdict.fit_label,
        "priority_label": verdict.priority_label,
        "summary": verdict.summary,
        "skills": skills_result.model_dump(),
        "experience": experience_result.model_dump(),
        "evidence": evidence_result.model_dump(),
    }


def _create_screening_record(jd_text: str, mode: str) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO screenings (mode, job_description) VALUES (?, ?)",
            (mode, jd_text),
        )
        conn.commit()
        return cursor.lastrowid


def _save_candidate_record(screening_id, file_path, resume, skills_result, experience_result, evidence_result, verdict):
    filename = display_name(file_path)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO candidates (
                screening_id, filename, resume_text,
                skills_score, experience_score, similarity_score, evidence_score,
                final_score, fit_label, priority_label, judge_summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                screening_id,
                filename,
                resume.raw_text,
                skills_result.score,
                experience_result.score,
                verdict.similarity_score,   # real resume<->JD semantic similarity (NULL if unavailable)
                evidence_result.score,
                verdict.final_score,
                verdict.fit_label,
                verdict.priority_label,
                verdict.summary,
            ),
        )
        conn.commit()
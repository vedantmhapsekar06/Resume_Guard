from backend.agents.base_agent import call_llm_json
from backend.core.relevance import jd_resume_similarity
from backend.core.scoring import compute_final_score, determine_fit_label, determine_priority_label
from backend.models.schemas import (
    JDProfile,
    ResumeProfile,
    SkillsMatchResult,
    ExperienceResult,
    EvidenceResult,
    JudgeVerdict,
)

SYSTEM_PROMPT = """You are the Judge Agent in a resume screening system. You write a brief STRENGTHS-ONLY commentary for a recruiter, based strictly on confirmed matched skills and relevant experience. A separate, already-written sentence (not your job) will cover any gaps - you must NOT mention gaps, missing skills, or anything the candidate lacks.

Return ONLY a valid JSON object with exactly this field, and nothing else (no markdown, no explanation):
{
  "strengths_summary": "1-2 sentences describing the candidate's confirmed strengths and relevant experience, based only on the data below"
}

STRICT RULES:
- Only describe skills/experience that appear in "Matched skills" or "Supporting evidence" below.
- Do NOT use any of these words or their variants: lacks, lacking, missing, gap, gaps, without experience, no experience, limited experience, weak, insufficient.
- Do NOT mention anything the candidate doesn't have - this summary is strengths-only.
- The "Relevance notes" given to you are PER-ROLE observations, not a complete inventory - do not imply a role lacks something just because a note doesn't mention it.
- Do not invent any information not explicitly present in the data below.
- Keep it recruiter-friendly: direct, factual, no fluff.
"""


def judge_candidate(
    jd: JDProfile,
    resume: ResumeProfile,
    skills_result: SkillsMatchResult,
    experience_result: ExperienceResult,
    evidence_result: EvidenceResult,
    similarity_score: float | None = None,
) -> JudgeVerdict:
    """
    Combines all agent outputs into the final verdict:
    - final_score / fit_label / priority_label: fully deterministic (Python)
    - gaps sentence: fully deterministic (Python, built directly from the agents' results)
    - strengths sentence: LLM, but structurally prevented from discussing gaps at all
    """
    if similarity_score is None:
        similarity_score = jd_resume_similarity(jd, resume)   # None if embeddings unavailable

    final_score = compute_final_score(
        skills_score=skills_result.score,
        experience_score=experience_result.score,
        similarity_score=similarity_score,
        evidence_score=evidence_result.score,
    )

    total_required = len(skills_result.matched_required) + len(skills_result.missing_required)
    coverage = (len(skills_result.matched_required) / total_required) if total_required else None

    # Required skills that are only listed (never demonstrated) are something to verify too.
    verify_flags = list(experience_result.risk_flags)
    if skills_result.unsupported_required:
        verify_flags.append("required skills listed but not demonstrated")

    fit_label = determine_fit_label(final_score, coverage)
    priority_label = determine_priority_label(final_score, verify_flags, fit_label)

    strengths_summary = ""
    try:
        user_prompt = _build_user_prompt(jd, resume, skills_result, experience_result, evidence_result)
        llm_result = call_llm_json(SYSTEM_PROMPT, user_prompt, temperature=0.1)
        strengths_summary = str(llm_result.get("strengths_summary", "")).strip()
    except Exception:
        pass   # the narrative is optional; the verdict itself never depends on the LLM

    if not strengths_summary:
        strengths_summary = _fallback_strengths(skills_result)

    gaps_sentence = _build_gaps_sentence(skills_result, experience_result, jd)

    summary = f"{strengths_summary} {gaps_sentence}".strip()

    return JudgeVerdict(
        final_score=final_score,
        fit_label=fit_label,
        priority_label=priority_label,
        summary=summary,
        similarity_score=similarity_score,
    )


def _build_user_prompt(
    jd: JDProfile,
    resume: ResumeProfile,
    skills_result: SkillsMatchResult,
    experience_result: ExperienceResult,
    evidence_result: EvidenceResult,
) -> str:
    matched = ', '.join(skills_result.evidenced_required + skills_result.evidenced_preferred) or "none"
    relevance_notes = '; '.join(
        n for n in experience_result.relevance_notes if n.startswith("Relevant:")
    ) or "none"
    supporting_bullets = '; '.join(evidence_result.supporting_bullets) or "none"

    return f"""
Job Title: {jd.role_title}
Candidate: {resume.candidate_name or "Unknown"}

Matched skills (demonstrated in experience/projects): {matched}
Relevant experience: {experience_result.relevant_years} years

Relevance notes (per-role, not a complete inventory): {relevance_notes}

Supporting evidence: {supporting_bullets}

Write a strengths-only summary using ONLY the information above.
"""


def _build_gaps_sentence(
    skills_result: SkillsMatchResult, experience_result: ExperienceResult, jd: JDProfile
) -> str:
    """
    Fully deterministic - built directly from the agents' results, no LLM involved,
    so this can never hallucinate a gap that doesn't exist.
    """
    parts = []

    if skills_result.missing_required:
        parts.append(f"Missing required skills: {', '.join(skills_result.missing_required)}.")

    if skills_result.weak_required:
        parts.append(
            f"Self-described as basic-level for required skills: {', '.join(skills_result.weak_required)}."
        )

    if skills_result.unsupported_skills:
        parts.append(
            f"Listed but unsupported by evidence (verify in interview): {', '.join(skills_result.unsupported_skills)}."
        )

    if experience_result.risk_flags:
        parts.append(f"Risk flags to verify: {'; '.join(experience_result.risk_flags)}.")

    if not experience_result.meets_minimum:
        parts.append(
            f"Does not meet the minimum experience in the job description "
            f"({experience_result.relevant_years} relevant years vs {jd.min_experience_years}+ required)."
        )

    if not parts:
        return "No missing required skills or risk flags identified."

    return " ".join(parts)


def _fallback_strengths(skills_result: SkillsMatchResult) -> str:
    if skills_result.evidenced_required:
        return f"Candidate has demonstrated experience with: {', '.join(skills_result.evidenced_required)}."
    return "Candidate profile reviewed against job requirements."
from backend.agents.base_agent import call_llm_json
from backend.models.schemas import JDProfile, ResumeProfile, SkillsMatchResult, ExperienceResult, ImprovementFeedback

SYSTEM_PROMPT = """You are a Resume Improvement Agent helping a student/job-seeker understand how their resume compares to a target job description, and how to improve it.

Return ONLY a valid JSON object with exactly these fields, and nothing else (no markdown, no explanation):
{
  "suggestions": ["3-5 concrete, actionable suggestions to improve the resume's fit for this specific job"]
}

STRICT RULES - read carefully:
- Base every suggestion strictly on the data given below (matched skills, missing skills, unsupported skills, experience gap). Do not invent skills, tools, or requirements not present in the data.
- If a skill is in "Missing required", suggest the candidate either add relevant project/coursework evidence for it, or address the gap directly in a cover letter - do NOT tell them to simply add the skill to their list without justification (that would encourage dishonest resume padding).
- If a skill is in "Unsupported skills" (listed but no bullet evidence), suggest adding a concrete example OR removing it - flag this as something applicant-tracking tools may penalize.
- If there's an experience gap (candidate has fewer years than required), suggest highlighting freelance, internship, or project work rather than fabricating experience.
- Never suggest exaggerating, fabricating, or padding the resume with anything not true.
- Keep each suggestion concise and specific - one clear action per suggestion.
"""


def generate_improvement_feedback(
    jd: JDProfile,
    resume: ResumeProfile,
    skills_result: SkillsMatchResult,
    experience_result: ExperienceResult,
) -> ImprovementFeedback:
    """
    Generates student-facing feedback: match percentage (deterministic),
    matched/partial/missing requirements (deterministic, from skills_result),
    and improvement suggestions (LLM, tightly grounded in the same data).
    """
    match_percentage = _compute_match_percentage(skills_result, experience_result)

    # Strengths = demonstrated; "partial" = JD-required skills that are only listed or self-rated basic.
    matched_requirements = list(skills_result.evidenced_required)
    partial_requirements = list(skills_result.unsupported_required) + list(skills_result.weak_required)
    missing_requirements = list(skills_result.missing_required)

    user_prompt = _build_user_prompt(jd, resume, skills_result, experience_result)
    llm_result = call_llm_json(SYSTEM_PROMPT, user_prompt, temperature=0.1)
    suggestions = llm_result.get("suggestions", []) or []

    if not suggestions:
        suggestions = _fallback_suggestions(skills_result, experience_result)

    return ImprovementFeedback(
        match_percentage=match_percentage,
        matched_requirements=matched_requirements,
        partial_requirements=partial_requirements,
        missing_requirements=missing_requirements,
        suggestions=suggestions,
    )


def _compute_match_percentage(skills_result: SkillsMatchResult, experience_result: ExperienceResult) -> float:
    """Skills (credit-based: demonstrated > listed-only > missing) 60% + experience 40%.
    Evidence/similarity are recruiter-side signals and aren't as meaningful for one resume."""
    combined = (skills_result.score * 0.6) + (experience_result.score * 0.4)
    return round(max(0.0, min(100.0, combined)), 2)


def _build_user_prompt(
    jd: JDProfile,
    resume: ResumeProfile,
    skills_result: SkillsMatchResult,
    experience_result: ExperienceResult,
) -> str:
    missing_required = ', '.join(skills_result.missing_required) if skills_result.missing_required else "none - all required skills matched"
    unsupported_list = skills_result.unsupported_required + skills_result.weak_required
    unsupported = ', '.join(unsupported_list) if unsupported_list else "none"

    experience_gap_note = "none - meets or exceeds requirement"
    if not experience_result.meets_minimum and jd.min_experience_years:
        experience_gap_note = f"candidate has {experience_result.relevant_years} relevant years, job requires {jd.min_experience_years}+ years"

    return f"""
Target Job Title: {jd.role_title}

Missing required skills: {missing_required}
Required skills listed but not demonstrated (or self-rated basic): {unsupported}
Experience gap: {experience_gap_note}

Write 3-5 concrete suggestions using ONLY the information above.
"""


def _fallback_suggestions(skills_result: SkillsMatchResult, experience_result: ExperienceResult) -> list[str]:
    """Used only if the LLM call returns empty suggestions after repair."""
    suggestions = []
    if skills_result.missing_required:
        suggestions.append(
            f"Add relevant project or coursework evidence for: {', '.join(skills_result.missing_required)}."
        )
    not_shown = skills_result.unsupported_required + skills_result.weak_required
    if not_shown:
        suggestions.append(
            f"Add a concrete project or bullet that demonstrates: {', '.join(not_shown)}. Skills listed without examples may be flagged as keyword-stuffing."
        )
    if not experience_result.meets_minimum:
        suggestions.append("Highlight any freelance, internship, or project work that adds relevant experience.")
    if not suggestions:
        suggestions.append("Your resume matches this job description well - no major gaps found.")
    return suggestions
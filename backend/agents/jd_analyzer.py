from backend.agents.base_agent import call_llm_json, clip_text
from backend.models.schemas import JDProfile

SYSTEM_PROMPT = """You are a Job Description Analyzer. Extract structured information from the job description text given by the user.

Return ONLY a valid JSON object with exactly these fields, and nothing else (no markdown, no explanation):
{
  "role_title": "string - the job title",
  "required_skills": ["list of must-have skills/technologies mentioned"],
  "preferred_skills": ["list of nice-to-have skills, if any mentioned separately"],
  "min_experience_years": number or null (minimum years of experience required, extract from text like '3+ years'),
  "responsibilities": ["list of key responsibilities/duties mentioned, short phrases"]
}

Rules:
- Only extract what is explicitly stated or clearly implied in the text.
- Do not invent skills or requirements not present in the text.
- Keep skill names concise (e.g. "Python", "REST APIs", "PostgreSQL").
- If min_experience_years is not mentioned, use null.
"""


def _str_list(value) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [v.strip() for v in value if isinstance(v, str) and v.strip()]


def _to_float(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def analyze_jd(jd_text: str) -> JDProfile:
    """
    Runs the JD Analyzer agent on raw job description text and
    returns a validated JDProfile.
    """
    user_prompt = f"Job Description:\n\n{clip_text(jd_text)}"

    result = call_llm_json(SYSTEM_PROMPT, user_prompt, temperature=0.1)

    return JDProfile(
        role_title=str(result.get("role_title") or "Unknown Role"),
        required_skills=_str_list(result.get("required_skills")),
        preferred_skills=_str_list(result.get("preferred_skills")),
        min_experience_years=_to_float(result.get("min_experience_years")),
        responsibilities=_str_list(result.get("responsibilities")),
        raw_text=jd_text,
    )

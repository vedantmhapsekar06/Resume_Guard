from backend.agents.base_agent import call_llm_json, clip_text
from backend.models.schemas import ResumeProfile

SYSTEM_PROMPT = """You are a Resume Analyzer. Extract structured information from the resume text given by the user.

Return ONLY a valid JSON object with exactly these fields, and nothing else (no markdown, no explanation):
{
  "candidate_name": "string or null - the candidate's full name if present",
  "skills_listed": ["list of skills/technologies mentioned anywhere in the resume, especially in a Skills section"],
  "total_experience_years": number or null (rough estimate of professional work experience in years - only a hint),
  "work_history": [
    {
      "title": "job title",
      "company": "company name",
      "start_date": "as written in resume, e.g. 'Jan 2020' or '2020'",
      "end_date": "as written in resume, e.g. 'Mar 2022' or 'Present'",
      "bullets": ["list of bullet points / responsibilities described for this role, kept close to original wording"]
    }
  ],
  "projects": [
    {
      "name": "project name",
      "technologies": ["tools/technologies named for this project"],
      "bullets": ["what was built / achieved, kept close to original wording"]
    }
  ]
}

STRICT RULES:
- Only extract what is explicitly present in the text. Do not invent experience or skills.
- work_history is for jobs and internships only. Personal, academic and hackathon projects go in "projects", NOT in work_history.
- List every distinct job/role and every project found, in the order they appear.
- Keep bullet text close to the original wording (do not summarize away specifics like tools or numbers).
- If total_experience_years cannot be estimated, use null.
- Each skill should appear ONLY ONCE in skills_listed - never list both a plain version and a qualified version of the same skill (e.g. never list both "Java" AND "Basic Java" - pick the one that matches how it is actually described in that specific resume).
- Copy each skill's qualifier exactly as it appears in the SOURCE TEXT for that resume, and only if that resume actually uses a qualifying word for it. Example: if the resume text says "limited experience with Java", write "Basic Java". If the resume text says "Strong expertise in Java" or just lists "Java" plainly, write "Java" with no prefix. Do not add "Basic" to skills the resume does not qualify.
- Do not extract a skill from a sentence that exists only to say the candidate does NOT have it (e.g. "no experience with X" should not produce X in the list at all).
"""


def _str(value) -> str:
    return value.strip() if isinstance(value, str) else ("" if value is None else str(value))


def _str_list(value) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [v.strip() for v in value if isinstance(v, str) and v.strip()]


def _clean_jobs(raw) -> list[dict]:
    jobs = []
    for j in raw if isinstance(raw, list) else []:
        if not isinstance(j, dict):
            continue
        jobs.append({
            "title": _str(j.get("title")),
            "company": _str(j.get("company")),
            "start_date": _str(j.get("start_date")),
            "end_date": _str(j.get("end_date")),
            "bullets": _str_list(j.get("bullets")),
        })
    return jobs


def _clean_projects(raw) -> list[dict]:
    projects = []
    for p in raw if isinstance(raw, list) else []:
        if not isinstance(p, dict):
            continue
        projects.append({
            "name": _str(p.get("name")),
            "technologies": _str_list(p.get("technologies")),
            "bullets": _str_list(p.get("bullets")),
        })
    return projects


def _to_float(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def analyze_resume(resume_text: str) -> ResumeProfile:
    """
    Runs the Resume Analyzer agent on raw resume text and
    returns a validated ResumeProfile.
    """
    user_prompt = f"Resume:\n\n{clip_text(resume_text)}"

    result = call_llm_json(SYSTEM_PROMPT, user_prompt, temperature=0.1)

    name = result.get("candidate_name")
    return ResumeProfile(
        candidate_name=name.strip() if isinstance(name, str) and name.strip() else None,
        skills_listed=_str_list(result.get("skills_listed")),
        total_experience_years=_to_float(result.get("total_experience_years")),
        work_history=_clean_jobs(result.get("work_history")),
        projects=_clean_projects(result.get("projects")),
        raw_text=resume_text,
    )

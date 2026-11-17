from backend.agents.jd_analyzer import analyze_jd
from backend.agents.resume_analyzer import analyze_resume
from backend.agents.skills_matching import match_skills
from backend.agents.experience_relevance import analyze_experience
from backend.agents.evidence import find_evidence
from backend.agents.judge import judge_candidate

sample_jd = """
Backend Developer — 3+ years experience required.
Must have strong skills in Python, Django, REST APIs, and PostgreSQL.
Responsibilities include building scalable APIs and code reviews.
"""

sample_resume = """
Jane Doe
Skills: Python, Django, Flask, REST APIs, PostgreSQL

Experience:
Backend Developer — TechCorp
Jan 2021 - Present
- Built REST APIs using Django and PostgreSQL, serving 2M requests/day
- Led code reviews for a team of 5 engineers
- Reduced API response time by 40% through query optimization

Junior Developer — StartupXYZ
Jun 2019 - Dec 2020
- Assisted in building internal tools with Flask
"""

jd = analyze_jd(sample_jd)
resume = analyze_resume(sample_resume)
skills_result = match_skills(jd, resume)
experience_result = analyze_experience(jd, resume)
evidence_result = find_evidence(jd, resume)

verdict = judge_candidate(jd, resume, skills_result, experience_result, evidence_result)
print(verdict.model_dump_json(indent=2))
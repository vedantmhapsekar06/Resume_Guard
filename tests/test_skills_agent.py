from backend.agents.jd_analyzer import analyze_jd
from backend.agents.resume_analyzer import analyze_resume
from backend.agents.skills_matching import match_skills

sample_jd = """
Backend Developer — 3+ years experience required.
Must have strong skills in Python, Django, REST APIs, and PostgreSQL.
Experience with AWS is a plus.
"""

sample_resume = """
Jane Doe
Skills: Python, Django, Flask, REST APIs, PostgreSQL, Docker, Kubernetes

Experience:
Backend Developer — TechCorp
Jan 2021 - Present
- Built REST APIs using Django and PostgreSQL
- Deployed services using Docker
"""

jd = analyze_jd(sample_jd)
resume = analyze_resume(sample_resume)
result = match_skills(jd, resume)
print(result.model_dump_json(indent=2))
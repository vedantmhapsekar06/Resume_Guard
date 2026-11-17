from backend.agents.jd_analyzer import analyze_jd
from backend.agents.resume_analyzer import analyze_resume
from backend.agents.experience_relevance import analyze_experience

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
- Built REST APIs using Django and PostgreSQL
- Led code reviews for the backend team

Junior Developer — StartupXYZ
Jun 2019 - Dec 2020
- Assisted in building internal tools with Flask
"""

jd = analyze_jd(sample_jd)
resume = analyze_resume(sample_resume)
result = analyze_experience(jd, resume)
print(result.model_dump_json(indent=2))
from backend.agents.jd_analyzer import analyze_jd

sample_jd = """
Backend Developer — 3+ years experience required.
Must have strong skills in Python, Django, REST APIs, and PostgreSQL.
Experience with AWS is a plus.
Responsibilities include building scalable APIs, writing tests, and code reviews.
"""

result = analyze_jd(sample_jd)
print(result.model_dump_json(indent=2))
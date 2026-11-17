from backend.agents.resume_analyzer import analyze_resume

sample_resume = """
Jane Doe
Backend Developer

Skills: Python, Django, Flask, REST APIs, PostgreSQL, Docker, Kubernetes

Experience:

Backend Developer — TechCorp
Jan 2021 - Present
- Built REST APIs using Django and PostgreSQL
- Deployed services using Docker
- Wrote unit tests achieving 90% coverage

Junior Developer — StartupXYZ
Jun 2019 - Dec 2020
- Assisted in building internal tools with Flask
- Worked with PostgreSQL databases
"""

result = analyze_resume(sample_resume)
print(result.model_dump_json(indent=2))
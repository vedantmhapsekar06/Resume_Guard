from backend.agents.jd_analyzer import analyze_jd
from backend.agents.resume_analyzer import analyze_resume
from backend.agents.skills_matching import match_skills
from backend.agents.experience_relevance import analyze_experience
from backend.agents.resume_improvement import generate_improvement_feedback

sample_jd = """
Backend Developer — 3+ years experience required.
Must have strong skills in Python, Django, REST APIs, PostgreSQL, and AWS.
"""

sample_resume = """
Jane Doe
Skills: Python, Django, Flask, REST APIs, PostgreSQL, Kubernetes, GraphQL, Kafka

Experience:
Backend Developer — TechCorp
Jan 2023 - Present
- Built REST APIs using Django and PostgreSQL
"""

jd = analyze_jd(sample_jd)
resume = analyze_resume(sample_resume)
skills_result = match_skills(jd, resume)
experience_result = analyze_experience(jd, resume)

feedback = generate_improvement_feedback(jd, resume, skills_result, experience_result)
print(feedback.model_dump_json(indent=2))
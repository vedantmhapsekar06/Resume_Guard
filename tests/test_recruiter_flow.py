from backend.db.database import init_db
from backend.orchestrator.recruiter_flow import run_recruiter_screening

init_db()

sample_jd = """
Backend Developer — 3+ years experience required.
Must have strong skills in Python, Django, REST APIs, and PostgreSQL.
Experience with AWS is a plus.
Responsibilities include building scalable APIs and code reviews.
"""

resume_files = [
    "test_files/Ananya_Deshmukh_Resume.docx",
    "test_files/Arjun Mehta.pdf",
    "test_files/Sneha Kulkarni.pdf",
]

result = run_recruiter_screening(sample_jd, resume_files)

print(f"\nScreening ID: {result['screening_id']}")
print(f"Job Title: {result['jd_profile']['role_title']}\n")

for i, candidate in enumerate(result["candidates"], start=1):
    print(f"{i}. {candidate['candidate_name'] or candidate['filename']}")
    print(f"   Score: {candidate['final_score']}/100 | {candidate['fit_label']} | Priority: {candidate['priority_label']}")
    print(f"   Summary: {candidate['summary']}\n")
from backend.db.database import init_db
from backend.orchestrator.student_flow import run_student_analysis

init_db()

sample_jd = """
Backend Developer — 3+ years experience required.
Must have strong skills in Python, Django, REST APIs, and PostgreSQL.
Experience with AWS is a plus.
"""

result = run_student_analysis(sample_jd, "test_files/Arjun Mehta.pdf")

print(f"\nScreening ID: {result['screening_id']}")
print(f"Candidate: {result['candidate_name']}")
print(f"Match: {result['feedback']['match_percentage']}%\n")

print("Matched:", result['feedback']['matched_requirements'])
print("Partial:", result['feedback']['partial_requirements'])
print("Missing:", result['feedback']['missing_requirements'])
print("\nSuggestions:")
for s in result['feedback']['suggestions']:
    print(f"- {s}")
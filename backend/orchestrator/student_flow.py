from backend.agents.jd_analyzer import analyze_jd
from backend.agents.resume_analyzer import analyze_resume
from backend.agents.skills_matching import match_skills
from backend.agents.experience_relevance import analyze_experience
from backend.agents.resume_improvement import generate_improvement_feedback
from backend.core.document_parser import extract_text
from backend.db.database import get_connection
from backend.orchestrator.recruiter_flow import display_name


def run_student_analysis(jd_text: str, resume_file_path: str) -> dict:
    """
    Runs the student-facing pipeline:
    JD Analyzer -> Resume Analyzer -> Skills Matching ->
    Experience & Relevance -> Resume Improvement.
    Persists the result to the DB and returns feedback for the UI.
    """
    jd = analyze_jd(jd_text)

    resume_text = extract_text(resume_file_path)
    resume = analyze_resume(resume_text)

    skills_result = match_skills(jd, resume)
    experience_result = analyze_experience(jd, resume)
    feedback = generate_improvement_feedback(jd, resume, skills_result, experience_result)

    screening_id = _create_screening_record(jd_text)
    _save_candidate_record(screening_id, resume_file_path, resume, skills_result, experience_result, feedback)

    return {
        "screening_id": screening_id,
        "jd_profile": jd.model_dump(),
        "candidate_name": resume.candidate_name,
        "feedback": feedback.model_dump(),
    }


def _create_screening_record(jd_text: str) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO screenings (mode, job_description) VALUES (?, ?)",
            ("student", jd_text),
        )
        conn.commit()
        return cursor.lastrowid


def _save_candidate_record(screening_id, file_path, resume, skills_result, experience_result, feedback):
    filename = display_name(file_path)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO candidates (
                screening_id, filename, resume_text,
                skills_score, experience_score, similarity_score, evidence_score,
                final_score, fit_label, priority_label, judge_summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                screening_id,
                filename,
                resume.raw_text,
                skills_result.score,
                experience_result.score,
                None,   # similarity not computed in student mode
                None,   # evidence not computed in student mode
                feedback.match_percentage,
                "N/A",       # fit_label not applicable in student mode
                "N/A",       # priority_label not applicable in student mode
                "; ".join(feedback.suggestions),
            ),
        )
        conn.commit()
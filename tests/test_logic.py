import os
import pytest

from backend.agents.evidence import find_evidence, has_metric
from backend.agents.experience_relevance import analyze_experience
from backend.agents.skills_matching import match_skills
from backend.core.date_utils import detect_gaps_and_overlaps, total_years
from backend.core.sanitize import escape_payload
from backend.core.scoring import compute_final_score, determine_fit_label, determine_priority_label
from backend.core.text_match import contains_term
from backend.models.schemas import JDProfile, ResumeProfile


def jd(required=("Python", "Django", "PostgreSQL"), preferred=("AWS",), min_years=3.0):
    return JDProfile(
        role_title="Backend Developer",
        required_skills=list(required),
        preferred_skills=list(preferred),
        min_experience_years=min_years,
        responsibilities=["build scalable REST APIs", "review code"],
        raw_text="jd",
    )


def resume(skills=(), jobs=(), projects=(), raw="resume text " * 10):
    return ResumeProfile(
        candidate_name="Test",
        skills_listed=list(skills),
        work_history=list(jobs),
        projects=list(projects),
        raw_text=raw,
    )


def job(title, start, end, bullets, company="Acme"):
    return {"title": title, "company": company, "start_date": start, "end_date": end, "bullets": bullets}


# ---------- text matching ----------
def test_word_boundary_matching():
    assert not contains_term("built apps in JavaScript", "java")
    assert not contains_term("wrote C++ services", "c")
    assert not contains_term("R&D team", "r")
    assert contains_term("Used Java and Spring", "java")
    assert contains_term("systems written in C and Go", "c")
    assert contains_term("services in Go", "go")
    assert not contains_term("we go to market fast", "go")   # lower-case 'go' is just a word


# ---------- dates ----------
def test_nested_job_does_not_create_fake_gap():
    flags = detect_gaps_and_overlaps([
        job("A", "Jan 2018", "Jan 2023", []),
        job("B", "Jan 2019", "Jan 2020", []),
        job("C", "Feb 2023", "Present", []),
    ])
    assert not any("gap" in f.lower() for f in flags)


def test_year_only_dates_have_no_fake_gap():
    flags = detect_gaps_and_overlaps([job("A", "2019", "2020", []), job("B", "2021", "2022", [])])
    assert flags == []


def test_total_years_counts_overlap_once():
    same = [job("A", "Jan 2020", "Jan 2022", []), job("B", "Jan 2020", "Jan 2022", [])]
    assert 1.9 <= total_years(same) <= 2.1


def test_real_gap_is_flagged():
    flags = detect_gaps_and_overlaps([job("A", "Jan 2015", "Dec 2016", []), job("B", "Jan 2019", "Dec 2020", [])])
    assert any("gap" in f.lower() for f in flags)


# ---------- skills ----------
def test_keyword_stuffing_is_not_rewarded():
    stuffed = match_skills(jd(), resume(skills=["Python", "Django", "PostgreSQL", "AWS"]))
    honest = match_skills(jd(), resume(
        skills=["Python", "Django", "PostgreSQL", "AWS"],
        jobs=[job("Dev", "2020", "2023", [
            "Built Django REST APIs in Python", "Tuned PostgreSQL queries, cut latency 40%", "Deployed to AWS"])],
    ))
    assert stuffed.score <= 55
    assert honest.score >= 95
    assert set(stuffed.unsupported_required) == {"python", "django", "postgresql"}
    assert honest.evidenced_required == ["python", "django", "postgresql"]


def test_skill_demonstrated_but_not_in_skills_list_counts():
    r = match_skills(jd(), resume(
        skills=["Python"],
        jobs=[job("Dev", "2020", "2023", ["Built APIs with Django and PostgreSQL"])],
    ))
    assert r.missing_required == []


def test_student_projects_count_as_evidence():
    r = match_skills(jd(), resume(
        skills=["Python", "Django"],
        projects=[{"name": "Blog", "technologies": ["Python", "Django"], "bullets": ["Built a blog"]}],
    ))
    assert "python" in r.evidenced_required and "django" in r.evidenced_required


def test_java_does_not_match_javascript():
    r = match_skills(jd(required=["Java"], preferred=[]), resume(skills=["JavaScript"]))
    assert r.missing_required == ["java"]


def test_weak_qualifier_gets_partial_credit():
    r = match_skills(jd(required=["Java", "Python"], preferred=[]), resume(skills=["Basic Java", "Python"]))
    assert r.weak_required == ["java"]
    assert r.score == pytest.approx(50.0)   # java 0.5 (weak) + python 0.5 (listed only) => 50%


def test_unsupported_check_no_substring_false_positive():
    r = match_skills(jd(required=["Java"], preferred=[]), resume(
        skills=["Java"], jobs=[job("Dev", "2020", "2022", ["Built dashboards in JavaScript"])]))
    assert "java" in r.unsupported_skills


# ---------- experience ----------
def test_irrelevant_experience_does_not_satisfy_minimum():
    r = analyze_experience(jd(), resume(
        jobs=[job("Baker", "2010", "2020", ["Baked bread", "Managed ovens"], company="Bakery")]))
    assert r.total_years >= 9
    assert r.relevant_years == 0
    assert not r.meets_minimum
    assert r.score < 30


def test_relevant_experience_meets_minimum():
    r = analyze_experience(jd(), resume(
        jobs=[job("Backend Dev", "2018", "2022", ["Built Django APIs in Python with PostgreSQL"])]))
    assert r.meets_minimum and r.relevant_years >= 3.5 and r.score > 70


def test_no_experience_is_not_a_free_100_when_jd_has_no_minimum():
    r = analyze_experience(jd(min_years=None), resume())
    assert r.score == 0.0


def test_llm_hint_is_ignored_when_dates_parse():
    res = resume(jobs=[job("Backend Dev", "2022", "2023", ["Python"])])
    res.total_experience_years = 15
    assert analyze_experience(jd(), res).total_years < 2.5


# ---------- evidence ----------
def test_metric_detection_ignores_plain_numbers():
    assert has_metric("Reduced latency by 35%")
    assert has_metric("Served 10k users")
    assert not has_metric("Used Python 3 for Q3 reports")
    assert not has_metric("3 years of experience")


def test_evidence_bullets_are_real_and_scored():
    bullets = ["Built Django REST APIs in Python serving 10k users", "Organised team lunches"]
    r = find_evidence(jd(), resume(jobs=[job("Dev", "2020", "2023", bullets)]))
    assert set(r.supporting_bullets) <= set(bullets)
    assert bullets[0] in r.supporting_bullets
    assert find_evidence(jd(), resume()).score == 0.0


# ---------- scoring ----------
def test_similarity_none_renormalises_weights():
    assert compute_final_score(80, 80, None, 80) == pytest.approx(80.0)


def test_required_coverage_knockout_and_priority_consistency():
    assert determine_fit_label(90, 0.3) == "Partial Fit"
    assert determine_fit_label(90, 0.0) == "No Fit"
    assert determine_fit_label(90, 1.0) == "Strong Fit"
    assert determine_priority_label(90, [], "Partial Fit") == "Medium"
    assert determine_priority_label(90, ["x"], "Strong Fit") == "Medium"
    assert determine_priority_label(90, [], "Strong Fit") == "High"


# ---------- judge / pipeline ----------
def test_judge_verdict_is_deterministic_even_if_llm_fails(monkeypatch):
    from backend.agents import judge as judge_mod

    def boom(*a, **k):
        raise RuntimeError("ollama down")

    monkeypatch.setattr(judge_mod, "call_llm_json", boom)
    j = jd()
    r = resume(skills=["Python", "Django", "PostgreSQL"],
               jobs=[job("Backend Dev", "2018", "2022", ["Built Django APIs in Python", "PostgreSQL tuning, 30% faster"])])
    verdict = judge_mod.judge_candidate(
        j, r, match_skills(j, r), analyze_experience(j, r), find_evidence(j, r))
    assert verdict.fit_label == "Strong Fit"
    assert verdict.similarity_score is not None and verdict.similarity_score > 0


def test_one_bad_resume_does_not_fail_the_batch(monkeypatch, tmp_path):
    from backend.db.database import init_db
    from backend.orchestrator import recruiter_flow as rf

    init_db()
    j = jd()
    monkeypatch.setattr(rf, "analyze_jd", lambda t: j)

    def fake_extract(path):
        if os.path.basename(path).startswith("bad"):
            raise ValueError("No readable text found in this file")
        return "text"

    good = resume(skills=["Python"], jobs=[job("Backend Dev", "2018", "2022", ["Built Django APIs in Python"])])
    monkeypatch.setattr(rf, "extract_text", fake_extract)
    monkeypatch.setattr(rf, "analyze_resume", lambda t: good)
    monkeypatch.setattr("backend.agents.judge.call_llm_json", lambda *a, **k: {"strengths_summary": "Solid."})

    out = rf.run_recruiter_screening("jd", [str(tmp_path / ("a" * 32 + "_good.pdf")), str(tmp_path / "bad.pdf")])
    names = [c["filename"] for c in out["candidates"]]
    assert "good.pdf" in names and "bad.pdf" in names      # uuid prefix stripped, bad file listed
    assert len(out["errors"]) == 1
    assert out["candidates"][0]["filename"] == "good.pdf"   # ranked above the failed file


# ---------- LLM plumbing ----------
def test_truncated_llm_json_is_not_silently_repaired(monkeypatch):
    from backend.agents import base_agent

    monkeypatch.setattr(base_agent, "_chat", lambda *a, **k: ('{"work_history": [{"title": "A"', True))
    with pytest.raises(base_agent.LLMOutputError):
        base_agent.call_llm_json("s", "u")


def test_valid_llm_json_passes(monkeypatch):
    from backend.agents import base_agent

    monkeypatch.setattr(base_agent, "_chat", lambda *a, **k: ('{"a": 1}', False))
    assert base_agent.call_llm_json("s", "u") == {"a": 1}


# ---------- security ----------
def test_response_payload_is_html_escaped():
    out = escape_payload({"candidate_name": "<img src=x onerror=alert(1)>", "n": 3, "l": ["<b>"]})
    assert "<" not in out["candidate_name"] and out["n"] == 3 and out["l"] == ["&lt;b&gt;"]

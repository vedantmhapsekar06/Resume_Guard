from pydantic import BaseModel
from typing import List, Optional


# ---------- JD Analyzer output ----------
class JDProfile(BaseModel):
    role_title: str
    required_skills: List[str]
    preferred_skills: List[str] = []
    min_experience_years: Optional[float] = None
    responsibilities: List[str] = []
    raw_text: str


# ---------- Resume Analyzer output ----------
class ResumeProfile(BaseModel):
    candidate_name: Optional[str] = None
    skills_listed: List[str] = []
    total_experience_years: Optional[float] = None   # LLM hint only; never trusted over dates
    work_history: List[dict] = []   # [{title, company, start_date, end_date, bullets: []}]
    projects: List[dict] = []       # [{name, technologies: [], bullets: []}]
    raw_text: str


# ---------- Skills Matching output ----------
class SkillsMatchResult(BaseModel):
    matched_required: List[str] = []      # every required skill found (demonstrated OR merely listed)
    matched_preferred: List[str] = []
    missing_required: List[str] = []
    missing_preferred: List[str] = []
    evidenced_required: List[str] = []    # required skills actually demonstrated in bullets/projects
    evidenced_preferred: List[str] = []
    unsupported_required: List[str] = []  # required skills that are ONLY in the Skills list
    weak_required: List[str] = []         # required skills the resume itself calls basic/limited
    unsupported_skills: List[str] = []    # ANY listed skill with no supporting evidence (for recruiter verification)
    score: float   # 0-100


# ---------- Experience & Relevance output (includes risk/consistency checks) ----------
class ExperienceResult(BaseModel):
    total_years: float                 # union of all work periods (overlaps counted once)
    relevant_years: float = 0.0        # union of periods of roles relevant to this JD
    meets_minimum: bool
    relevance_notes: List[str] = []
    risk_flags: List[str] = []         # deterministic date gaps/overlaps only
    score: float   # 0-100


# ---------- Evidence Agent output ----------
class EvidenceResult(BaseModel):
    supporting_bullets: List[str] = []
    quality_note: str = ""
    score: float   # 0-100


# ---------- Judge Agent output (Recruiter flow) ----------
class JudgeVerdict(BaseModel):
    final_score: float
    fit_label: str        # "Strong Fit" / "Partial Fit" / "No Fit"
    priority_label: str   # "High" / "Medium" / "Low"
    summary: str
    similarity_score: Optional[float] = None   # None when embeddings were unavailable


# ---------- Resume Improvement output (Student flow) ----------
class ImprovementFeedback(BaseModel):
    match_percentage: float
    matched_requirements: List[str] = []
    partial_requirements: List[str] = []
    missing_requirements: List[str] = []
    suggestions: List[str] = []

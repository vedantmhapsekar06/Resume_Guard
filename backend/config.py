import os
from dotenv import load_dotenv

load_dotenv()

# --- LLM Configuration ---
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.2:3b")

# Context window must hold: system prompt + input text + generated JSON.
# 8192 still fits a 3B model in ~4GB VRAM (KV cache is small for llama3.2:3b).
LLM_NUM_CTX = int(os.getenv("LLM_NUM_CTX", "8192"))
LLM_NUM_PREDICT = int(os.getenv("LLM_NUM_PREDICT", "3072"))

# Hard cap on characters of resume / JD text sent to the LLM (~3.5 chars/token).
# Anything longer is clipped explicitly instead of being silently truncated by Ollama.
MAX_INPUT_CHARS = int(os.getenv("MAX_INPUT_CHARS", "12000"))

# --- Embedding Model ---
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

# Raw cosine similarity of BGE embeddings is compressed (unrelated text still scores
# ~0.4-0.5). These bounds stretch the useful range [LOW, HIGH] onto 0-100.
# They are heuristics - re-calibrate on your own labelled resumes if you can.
SIM_COSINE_LOW = float(os.getenv("SIM_COSINE_LOW", "0.45"))
SIM_COSINE_HIGH = float(os.getenv("SIM_COSINE_HIGH", "0.85"))

# --- Database ---
DB_PATH = os.getenv("DB_PATH", "backend/db/resumeguard.db")

# --- Scoring Weights (must sum to 1.0) ---
SCORE_WEIGHTS = {
    "skills_match": 0.40,
    "experience_relevance": 0.30,
    "semantic_similarity": 0.20,
    "evidence_quality": 0.10,
}
assert abs(sum(SCORE_WEIGHTS.values()) - 1.0) < 1e-9, "SCORE_WEIGHTS must sum to 1.0"

# --- Thresholds ---
FIT_THRESHOLDS = {
    "strong_fit": 75,   # score >= this => Strong Fit
    "partial_fit": 50,  # score >= this => Partial Fit
    # below partial_fit => No Fit
}

# A candidate who covers less than this share of required skills can never be a Strong Fit.
MIN_REQUIRED_COVERAGE_FOR_STRONG = 0.5

# --- Skill matching ---
# Credit per required skill: demonstrated in bullets/projects = 1.0.
LISTED_ONLY_CREDIT = 0.5   # appears only in the Skills list (no demonstration)
WEAK_SKILL_CREDIT = 0.5    # resume itself says "basic / limited / familiar with ..."
# Embedding fallback for skill names the taxonomy doesn't know (0-100 scale, strict on purpose)
FUZZY_SKILL_THRESHOLD = float(os.getenv("FUZZY_SKILL_THRESHOLD", "90"))

# --- Experience / relevance ---
ROLE_RELEVANCE_THRESHOLD = 35.0   # a role counts as "relevant experience" at/above this (0-100)
EVIDENCE_MIN_RELEVANCE = 30.0     # a bullet must be at least this relevant to be cited as evidence
GAP_THRESHOLD_DAYS = 180
OVERLAP_THRESHOLD_DAYS = 30

# --- File Upload Limits ---
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_FILE_SIZE_MB = 10

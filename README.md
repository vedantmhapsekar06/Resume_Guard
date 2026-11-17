# ResumeGuard

A multi-agent resume screening system that runs entirely on free, open-source, locally hosted tools — no paid APIs, no cloud LLM costs.

ResumeGuard has two modes:

- **I'm Hiring** (recruiter) — batch-screens multiple resumes against a job description and returns a ranked shortlist with fit/priority labels and evidence-backed reasoning.
- **I'm Applying** (student) — gives one candidate honest, structured feedback on how well their resume matches a target job.

---

## Why this project exists

Most screening tools are black boxes: a score with no explanation, and easy to game by keyword stuffing. ResumeGuard is built on three principles:

1. **Explainability first.** Every score is backed by evidence you can inspect: matched skills, missing skills, and the actual resume bullets that support the verdict.
2. **Facts are deterministic; the LLM only reads and narrates.** All scores, labels, skill classifications, experience calculations and evidence selection are plain Python. The LLM is used only to extract structured data from text and to write short commentary grounded in already-verified facts. A model error can never change a score.
3. **No keyword-stuffing rewards.** A skill that is only listed earns half credit; a skill demonstrated in a work bullet or project earns full credit.

---

## How scoring works

```
Final Score = Skills Match          × 0.40
            + Experience Relevance  × 0.30
            + Semantic Similarity   × 0.20
            + Evidence Quality      × 0.10
```

| Component | How it is computed |
|---|---|
| **Skills Match** | Each JD skill is classified as *demonstrated* (full credit), *listed only* or *self-described as basic* (half credit), or *missing* (none). Required skills carry 90% of the component, preferred skills 10%. |
| **Experience Relevance** | Relevant years (periods of roles that actually match this JD, overlapping jobs counted once) against the JD minimum, blended with how relevant the work is. Date gaps and overlaps reduce the score. |
| **Semantic Similarity** | Embedding similarity between each JD requirement and the best-matching resume statement, averaged. If embeddings are unavailable the component is dropped and the other weights are re-normalised. |
| **Evidence Quality** | Share of required skills demonstrated (50%), relevance of the best bullets (30%), share of bullets with quantified results (20%). |

| Score | Fit label |
|---|---|
| ≥ 75 | Strong Fit |
| 50–74 | Partial Fit |
| < 50 | No Fit |

Two rules sit on top of the score:

- A candidate covering **under half** of the required skills cannot be a Strong Fit, and one covering none is a No Fit.
- **Priority** (High / Medium / Low) is separate from Fit and always consistent with it. A Strong Fit with something to verify (an employment gap, or required skills listed but never demonstrated) is Medium priority, not High.

---

## Architecture

### The agents

| # | Agent | Used by | Method | What it does |
|---|-------|---------|--------|--------------|
| 1 | JD Analyzer | Both | LLM extraction | Role title, required/preferred skills, minimum years, responsibilities |
| 2 | Resume Analyzer | Both | LLM extraction | Name, skills, work history (dates + bullets), projects |
| 3 | Skills Matching | Both | Deterministic | Taxonomy + word-boundary matching; demonstrated / listed-only / basic / missing |
| 4 | Experience & Relevance | Both | Deterministic | Total and relevant years, role relevance, date gap/overlap flags |
| 5 | Evidence | Recruiter | Deterministic | Selects the strongest real bullets for this JD and scores them |
| 6 | Judge | Recruiter | Deterministic score + LLM narrative | Final score, Fit/Priority labels, summary |
| 7 | Resume Improvement | Student | Deterministic match % + LLM suggestions | Match percentage and 3–5 honest suggestions |

### Pipelines

**Recruiter:** JD Analyzer → for each resume: Resume Analyzer → Skills Matching → Experience & Relevance → Evidence → Judge → ranked shortlist. A resume that fails (for example a scanned PDF) is listed as "Could not be processed" instead of failing the batch.

**Student:** JD Analyzer → Resume Analyzer → Skills Matching → Experience & Relevance → Resume Improvement.

### Deterministic vs. LLM

| Deterministic (Python) | LLM (Ollama, local) |
|---|---|
| PDF/DOCX text extraction | Structured extraction from the JD and resume |
| Skill taxonomy and skill matching | Strengths narrative (Judge) |
| Date math, relevant years, gaps/overlaps | Improvement suggestions (Student flow) |
| Role relevance and evidence selection | |
| Semantic similarity (embeddings) | |
| Final score, Fit and Priority labels | |
| Gaps / missing-skills sentence | |

The model is small (3B parameters, to fit in 4 GB of VRAM). Small models are unreliable at open-ended judgment but good at extracting and restating given facts, so the design keeps judgment out of the LLM.

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11 + FastAPI |
| LLM | [Ollama](https://ollama.com) running `llama3.2:3b` |
| Embeddings | `sentence-transformers` (`BAAI/bge-small-en-v1.5`) |
| Similarity | `scikit-learn` cosine similarity |
| Document parsing | `pdfplumber`, `PyMuPDF`, `python-docx` (including tables) |
| Database | SQLite |
| Frontend | Plain HTML/CSS/JS via Jinja2 (no build step) |
| JSON reliability | Ollama JSON mode, with `json-repair` for minor formatting slips only |

---

## Setup

### Prerequisites

- Python 3.11 (newer versions such as 3.13 are not compatible with the ML dependencies)
- [Ollama](https://ollama.com/download) installed
- Windows PowerShell for the provided scripts (on macOS/Linux run the equivalent commands manually)

### Install

```powershell
git clone https://github.com/<your-username>/resumeguard.git
cd resumeguard
.\scripts\setup.ps1
```

This creates a virtual environment, installs dependencies, copies `.env.example` to `.env`, and pulls `llama3.2:3b`. To do it by hand:

```powershell
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
ollama pull llama3.2:3b
```

### Run

Make sure Ollama is running (the Ollama app, or `ollama serve`), then:

```powershell
.\scripts\run_dev.ps1
```

or manually:

```powershell
.\venv\Scripts\Activate.ps1
uvicorn backend.main:app --reload --port 8000
```

Open **http://localhost:8000**:

- `/` — recruiter mode ("I'm Hiring")
- `/apply` — student mode ("I'm Applying")

The first run downloads the embedding model (about 130 MB), so the first request is slow.

### Try it with the sample data

`sample_data/` contains a job description and six fake resumes covering a strong match, a keyword-stuffed resume, an irrelevant career, a student with projects, overlapping jobs, and a scanned (unreadable) PDF. In recruiter mode, paste `Sample_JD_Backend_Developer.txt` and upload all the resumes together.

### Configuration

Defaults live in `backend/config.py`; override them with environment variables or `.env`.

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server |
| `MODEL_NAME` | `llama3.2:3b` | Local LLM |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | Embedding model |
| `DB_PATH` | `backend/db/resumeguard.db` | SQLite file |
| `LLM_NUM_CTX` | `8192` | Context window (prompt + output) |
| `LLM_NUM_PREDICT` | `3072` | Max output tokens |
| `MAX_INPUT_CHARS` | `12000` | Resume/JD text is clipped here, explicitly |
| `SIM_COSINE_LOW` / `SIM_COSINE_HIGH` | `0.45` / `0.85` | Useful range of raw cosine similarity, stretched to 0–100 |
| `FUZZY_SKILL_THRESHOLD` | `90` | Strictness of embedding fallback for unknown skill names |

The score weights, fit thresholds and credit values are constants in `config.py`. The embedding values are heuristics for `bge-small-en-v1.5`; calibrate them on a few labelled resumes.

---

## Project structure

```
resumeguard/
├── .env.example
├── requirements.txt            # runtime dependencies
├── requirements-dev.txt        # + pytest
├── pytest.ini
├── README.md
│
├── backend/
│   ├── main.py                 # FastAPI app and page routes
│   ├── config.py               # settings, weights, thresholds
│   ├── routers/                # /api/recruiter, /api/student
│   ├── agents/                 # the 7 agents + LLM client (base_agent.py)
│   ├── orchestrator/           # recruiter_flow.py, student_flow.py
│   ├── core/
│   │   ├── document_parser.py  # PDF/DOCX text extraction
│   │   ├── embeddings.py       # batched, normalised embeddings
│   │   ├── similarity.py       # cosine + rescaling
│   │   ├── relevance.py        # role/bullet relevance, resume↔JD similarity
│   │   ├── taxonomy.py         # skill normalisation, aliases, qualifiers
│   │   ├── text_match.py       # word-boundary term matching
│   │   ├── resume_text.py      # evidence text helpers
│   │   ├── date_utils.py       # durations, merged periods, gaps/overlaps
│   │   ├── scoring.py          # final score, Fit and Priority labels
│   │   └── sanitize.py         # HTML-escapes API output
│   ├── models/schemas.py       # Pydantic models
│   ├── db/database.py          # SQLite setup
│   └── data/taxonomy/skills_taxonomy.json
│
├── frontend/
│   ├── templates/              # base, recruiter, student
│   └── static/                 # css, js
│
├── tests/
│   ├── conftest.py, test_logic.py   # unit tests (no Ollama needed)
│   └── test_*_agent.py, test_*_flow.py   # manual integration scripts
│
├── scripts/                    # setup.ps1, run_dev.ps1
│
└── sample_data/                # sample job description + fake resumes
```

---

## Testing

Unit tests cover the scoring logic. They need no Ollama and no model download (embeddings are faked):

```powershell
pip install -r requirements-dev.txt
python -m pytest
```

The other files in `tests/` are manual integration scripts that run the real agents and flows against real resumes. Run them from the project root:

```powershell
python -m tests.test_recruiter_flow
python -m tests.test_student_flow
```

---

## Known limitations

- **Extraction quality is the ceiling.** The 3B model extracts the structured data everything else relies on. A missed project or garbled date carries through to the score.
- **Thresholds are heuristic.** Weights, cut-offs and embedding ranges are reasonable defaults, not validated values. Calibrate on labelled resumes before relying on them.
- **Skill coverage.** The taxonomy has about 300 entries. Skills outside it match only by exact wording, so phrasing such as "RESTful services" may not match "REST APIs".
- **The narrative can still be imprecise.** Scores, labels and skill lists are deterministic; only the free-text strengths summary and improvement suggestions come from the LLM. Review them before acting on them.
- **Scanned PDFs are not supported** (no OCR). They are reported as unreadable.
- **Long resumes** over `MAX_INPUT_CHARS` are clipped, and very long model output raises an explicit error instead of silently dropping content.
- **Not an auto-reject tool.** Automated ranking can encode bias (for example, penalising non-linear careers). Use it to prioritise human review, not to replace it.
- **No authentication.** Single-user local tool; do not expose it publicly without adding auth.
- **Resume text is stored in SQLite**, including personal data. Treat the database file as sensitive; it is excluded from version control.
- **Batch processing is sequential** and runs in a worker thread; there is no job queue.

---

## Author

Vedant Mhapsekar

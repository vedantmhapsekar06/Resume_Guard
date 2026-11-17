import os
import re
import uuid
from fastapi.concurrency import run_in_threadpool
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from backend.orchestrator.student_flow import run_student_analysis
from backend.core.sanitize import escape_payload
from backend.config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB

router = APIRouter(prefix="/api/student", tags=["student"])

def _safe_filename(name: str) -> str:
    """Basename only, restricted charset - blocks '../' path traversal in uploaded file names."""
    base = os.path.basename((name or "resume").replace("\\", "/"))
    return re.sub(r"[^A-Za-z0-9._ -]", "_", base)[:100] or "resume"


UPLOAD_DIR = "backend/data/uploads/student"


@router.post("/analyze")
async def analyze_resume(
    job_description: str = Form(...),
    resume: UploadFile = File(...),
):
    """
    Accepts a job description and a single resume file,
    runs the student feedback pipeline, and returns match analysis + suggestions.
    """
    if not job_description.strip():
        raise HTTPException(status_code=400, detail="Job description cannot be empty.")

    ext = os.path.splitext(resume.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {resume.filename}. Only PDF and DOCX are allowed."
        )

    contents = await resume.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {resume.filename} ({size_mb:.1f}MB). Max is {MAX_FILE_SIZE_MB}MB."
        )

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}_{_safe_filename(resume.filename)}"
    save_path = os.path.join(UPLOAD_DIR, safe_name)

    try:
        with open(save_path, "wb") as f:
            f.write(contents)

        result = await run_in_threadpool(run_student_analysis, job_description, save_path)
        return escape_payload(result)
    except ValueError as exc:   # unreadable file, or model output unusable
        raise HTTPException(status_code=422, detail=str(exc).splitlines()[0][:300])
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Analysis failed. Make sure Ollama is running and the model is pulled, then try again.",
        )

    finally:
        if os.path.exists(save_path):
            os.remove(save_path)
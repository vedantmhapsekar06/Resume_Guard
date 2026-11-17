import os
import re
import shutil
import uuid
from fastapi.concurrency import run_in_threadpool
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from backend.orchestrator.recruiter_flow import run_recruiter_screening
from backend.core.sanitize import escape_payload
from backend.config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB

router = APIRouter(prefix="/api/recruiter", tags=["recruiter"])

def _safe_filename(name: str) -> str:
    """Basename only, restricted charset - blocks '../' path traversal in uploaded file names."""
    base = os.path.basename((name or "resume").replace("\\", "/"))
    return re.sub(r"[^A-Za-z0-9._ -]", "_", base)[:100] or "resume"


UPLOAD_DIR = "backend/data/uploads/recruiter"


@router.post("/screen")
async def screen_candidates(
    job_description: str = Form(...),
    resumes: list[UploadFile] = File(...),
):
    """
    Accepts a job description and multiple resume files,
    runs the full recruiter pipeline, and returns a ranked shortlist.
    """
    if not job_description.strip():
        raise HTTPException(status_code=400, detail="Job description cannot be empty.")

    if not resumes:
        raise HTTPException(status_code=400, detail="At least one resume file is required.")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    saved_paths = []

    try:
        for resume in resumes:
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

            safe_name = f"{uuid.uuid4().hex}_{_safe_filename(resume.filename)}"
            save_path = os.path.join(UPLOAD_DIR, safe_name)
            with open(save_path, "wb") as f:
                f.write(contents)
            saved_paths.append(save_path)

        # The pipeline is blocking (LLM + embeddings): run it in a worker thread so the
        # event loop - and every other request - stays responsive.
        result = await run_in_threadpool(run_recruiter_screening, job_description, saved_paths)
        return escape_payload(result)
    except ValueError as exc:   # e.g. the job description could not be analysed
        raise HTTPException(status_code=422, detail=str(exc).splitlines()[0][:300])
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Screening failed. Make sure Ollama is running and the model is pulled, then try again.",
        )

    finally:
        # Clean up uploaded files after processing (resume text is already saved in DB)
        for path in saved_paths:
            if os.path.exists(path):
                os.remove(path)
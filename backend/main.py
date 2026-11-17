from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request

from backend.db.database import init_db
from backend.routers import recruiter, student

app = FastAPI(title="ResumeGuard", description="Multi-Agent Resume Screening System")

# Initialize the database (creates tables if they don't exist)
init_db()

# Register API routers
app.include_router(recruiter.router)
app.include_router(student.router)

# Serve frontend static files (CSS/JS) - folder created in the next step
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

templates = Jinja2Templates(directory="frontend/templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("recruiter.html", {"request": request, "active_mode": "hiring"})


@app.get("/apply", response_class=HTMLResponse)
async def apply_page(request: Request):
    return templates.TemplateResponse("student.html", {"request": request, "active_mode": "applying"})


@app.get("/health")
async def health_check():
    return {"status": "ok"}
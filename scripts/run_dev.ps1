Write-Host "Starting ResumeGuard dev server..." -ForegroundColor Cyan

& .\venv\Scripts\Activate.ps1
uvicorn backend.main:app --reload --port 8000
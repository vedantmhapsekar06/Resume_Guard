Write-Host "Setting up ResumeGuard..." -ForegroundColor Cyan

# Create virtual environment with Python 3.11
Write-Host "Creating virtual environment (Python 3.11)..." -ForegroundColor Yellow
py -3.11 -m venv venv

# Activate it
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

# Copy env file
if (-Not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "Created .env from .env.example" -ForegroundColor Green
}

# Pull the Ollama model
Write-Host "Pulling llama3.2:3b model via Ollama (this may take a few minutes)..." -ForegroundColor Yellow
ollama pull llama3.2:3b

Write-Host "`nSetup complete! Run the app with:" -ForegroundColor Green
Write-Host "  uvicorn backend.main:app --reload --port 8000" -ForegroundColor White
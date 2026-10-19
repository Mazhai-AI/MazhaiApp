
$ErrorActionPreference = "Stop"

# Navigate to the directory containing this script
Set-Location $PSScriptRoot

# Create virtual environment if it doesn't exist
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

# Activate virtual environment
& ".\.venv\Scripts\Activate.ps1"

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
python -m pip install -r backend/requirements.txt

# Create .env if it doesn't exist
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example. Add MISTRAL_API_KEY to enable AI."
}

# Start the application
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8001

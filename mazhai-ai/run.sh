#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m venv .venv 2>/dev/null || true
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
if [[ ! -f .env ]]; then cp .env.example .env; echo "Created .env from .env.example. Add MISTRAL_API_KEY to enable AI." ; fi
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8001

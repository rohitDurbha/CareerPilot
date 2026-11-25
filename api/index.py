"""Vercel entry point for the CareerPilot Flask backend.

vercel.json sends every /api/... request here. The app itself lives in
Project/, and StripPrefix turns /api/latest_jobs into the /latest_jobs route.
"""

import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent / "Project"
sys.path.insert(0, str(PROJECT_DIR))

from backend import app  # noqa: E402
from prefix import StripPrefix  # noqa: E402

app.wsgi_app = StripPrefix(app.wsgi_app, "/api")

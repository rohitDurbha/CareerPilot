"""Record the mock backend's answers for the static GitHub Pages demo.

GitHub Pages only serves files, so it cannot run the Flask backend. This script
starts the backend in mock mode inside the Flask test client, sends it the same
requests the two pages make, and writes every answer to one JSON file. The
static build replays that file in the browser, so the hosted pages show exactly
what the real mock backend returns.

    python scripts/record_demo_api.py demo-api.json

Nothing here touches the network, MongoDB, Activepieces or LiveKit.
"""

from __future__ import annotations

import io
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT / "Project"

SAMPLE_RESUME_TEXT = "Python, SQL and five years of analytics work"


class _SamplePage:
    def extract_text(self):
        return SAMPLE_RESUME_TEXT


class _SampleReader:
    """Stands in for PyPDF2 so the recording needs no real PDF file."""

    def __init__(self, _file):
        self.pages = [_SamplePage()]


def _resume_form(**fields):
    form = dict(fields)
    form["resume"] = (io.BytesIO(b"%PDF sample"), "resume.pdf")
    return form


# (method, path, request keyword arguments) for every call the pages make.
REQUESTS = [
    ("GET", "/", {}),
    ("GET", "/health", {}),
    ("GET", "/latest_jobs", {}),
    ("POST", "/trigger", {"data": lambda: _resume_form(keyword="Data Analyst", location="Remote")}),
    ("POST", "/upload_resume", {"data": lambda: _resume_form(job_id="demo")}),
    ("POST", "/run_agents", {"json": {"job_title": "Data Analyst", "job_description": "Sample"}}),
    ("GET", "/cancel_file1", {}),
]


def load_mock_backend():
    os.environ["CAREERPILOT_MOCK"] = "1"
    for name in ("ACTIVEPIECES_JOB_SEARCH_WEBHOOK", "ACTIVEPIECES_RESUME_MATCH_WEBHOOK", "MONGO_URI"):
        os.environ.pop(name, None)
    if str(PROJECT) not in sys.path:
        sys.path.insert(0, str(PROJECT))
    import config

    # A local Project/.env must never leak real settings into a public file.
    config.ENV_FILE = PROJECT / ".env.does-not-exist"
    sys.modules.pop("backend", None)
    import backend

    backend.PdfReader = _SampleReader
    backend.app.config["TESTING"] = True
    return backend


def record():
    backend = load_mock_backend()
    if not backend.settings.mock_mode:
        raise SystemExit("the backend did not start in mock mode")
    client = backend.app.test_client()
    responses = {}
    for method, path, kwargs in REQUESTS:
        call = {key: (value() if callable(value) else value) for key, value in kwargs.items()}
        reply = client.open(path, method=method, **call)
        body = reply.get_json(silent=True)
        if body is None:
            body = reply.get_data(as_text=True)
        responses[f"{method} {path}"] = {"status": reply.status_code, "body": body}
    return responses


def main(argv):
    if len(argv) != 1:
        raise SystemExit("usage: record_demo_api.py OUTPUT.json")
    responses = record()
    failed = [key for key, value in responses.items() if value["status"] != 200]
    if failed:
        raise SystemExit(f"mock backend calls failed: {', '.join(failed)}")
    Path(argv[0]).write_text(json.dumps(responses, indent=2) + "\n", encoding="utf-8")
    print(f"Recorded {len(responses)} mock backend answers to {argv[0]}")


if __name__ == "__main__":
    main(sys.argv[1:])

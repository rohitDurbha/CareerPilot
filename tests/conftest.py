"""Shared fixtures for the Flask backend tests.

The backend is imported fresh for every test with fake webhook URLs and a
stand-in PDF reader, so no test talks to Activepieces, MongoDB or LiveKit.
"""

import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT / "Project"
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

import config  # noqa: E402

SEARCH_URL = "https://example.test/job-search"
MATCH_URL = "https://example.test/resume-match"


class FakePage:
    def __init__(self, text):
        self._text = text

    def extract_text(self):
        return self._text


class FakeReader:
    def __init__(self, _file, text="Python, SQL and five years of analytics"):
        self.pages = [FakePage(text)]


def _fresh_backend(monkeypatch):
    sys.modules.pop("backend", None)
    module = importlib.import_module("backend")
    module.app.config["TESTING"] = True
    monkeypatch.setattr(module, "PdfReader", FakeReader)
    return module


@pytest.fixture
def backend(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "ENV_FILE", tmp_path / "missing.env")
    monkeypatch.delenv("CAREERPILOT_MOCK", raising=False)
    monkeypatch.setenv("ACTIVEPIECES_JOB_SEARCH_WEBHOOK", SEARCH_URL)
    monkeypatch.setenv("ACTIVEPIECES_RESUME_MATCH_WEBHOOK", MATCH_URL)
    return _fresh_backend(monkeypatch)


@pytest.fixture
def mock_backend(monkeypatch, tmp_path):
    """The backend in mock mode with no webhook URLs configured at all."""
    monkeypatch.setattr(config, "ENV_FILE", tmp_path / "missing.env")
    monkeypatch.setenv("CAREERPILOT_MOCK", "1")
    monkeypatch.delenv("ACTIVEPIECES_JOB_SEARCH_WEBHOOK", raising=False)
    monkeypatch.delenv("ACTIVEPIECES_RESUME_MATCH_WEBHOOK", raising=False)
    return _fresh_backend(monkeypatch)

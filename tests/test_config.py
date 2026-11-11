"""Checks that the Flask backend reads its settings from the environment."""

import importlib
import io
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT / "Project"
sys.path.insert(0, str(PROJECT))

import config  # noqa: E402

SETTING_NAMES = (
    "MONGO_URI",
    "MONGO_DB",
    "MONGO_COLLECTION",
    "ACTIVEPIECES_JOB_SEARCH_WEBHOOK",
    "ACTIVEPIECES_RESUME_MATCH_WEBHOOK",
    "CAREERPILOT_MOCK",
)


@pytest.fixture
def clean_env(monkeypatch):
    for name in SETTING_NAMES:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_no_credentials_or_webhooks_in_the_code():
    for script in PROJECT.glob("*.py"):
        source = script.read_text(encoding="utf-8")
        assert "mongodb+srv://" not in source, f"connection string in {script.name}"
        assert not re.search(r"activepieces\.com/\S+/[A-Za-z0-9]{12,}", source), (
            f"Activepieces URL in {script.name}"
        )


def test_example_env_lists_every_setting():
    example = (PROJECT / ".env.example").read_text(encoding="utf-8")
    for name in SETTING_NAMES:
        assert re.search(rf"^{name}=", example, re.MULTILINE), f"{name} missing"


def test_defaults_when_nothing_is_set(clean_env, tmp_path):
    settings = config.load_settings(env_file=tmp_path / "missing.env")
    assert settings.mongo_uri == config.DEFAULT_MONGO_URI
    assert settings.mongo_db == "scrapped_jobs"
    assert settings.job_search_webhook == ""


def test_environment_wins_over_env_file(clean_env, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "MONGO_DB=from_file\nACTIVEPIECES_JOB_SEARCH_WEBHOOK=https://example.test/file\n"
    )
    clean_env.setenv("MONGO_DB", "from_env")
    settings = config.load_settings(env_file=env_file)
    assert settings.mongo_db == "from_env"
    assert settings.job_search_webhook == "https://example.test/file"


def test_require_names_the_missing_variable(clean_env, tmp_path):
    settings = config.load_settings(env_file=tmp_path / "missing.env")
    with pytest.raises(config.MissingSettingError, match="ACTIVEPIECES_RESUME_MATCH_WEBHOOK"):
        settings.require("resume_match_webhook", "ACTIVEPIECES_RESUME_MATCH_WEBHOOK")


@pytest.fixture
def client(clean_env, tmp_path):
    clean_env.setattr(config, "ENV_FILE", tmp_path / "missing.env")
    sys.modules.pop("backend", None)
    backend = importlib.import_module("backend")
    backend.app.config["TESTING"] = True
    return backend.app.test_client()


@pytest.mark.parametrize("route", ["/trigger", "/upload_resume"])
def test_workflow_routes_explain_missing_webhooks(client, route):
    data = {"keyword": "data analyst", "resume": (io.BytesIO(b"%PDF-1.4"), "resume.pdf")}
    response = client.post(route, data=data, content_type="multipart/form-data")
    assert response.status_code == 503
    assert "ACTIVEPIECES_JOB_SEARCH_WEBHOOK" in response.get_json()["details"]

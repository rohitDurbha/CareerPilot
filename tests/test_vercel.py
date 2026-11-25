"""Checks for the hosted demo: static pages plus the backend function at /api."""

import importlib.util
import json
import re
import shutil
import subprocess
import sys

import pytest

from conftest import PROJECT, ROOT

import config

VERCEL_JSON = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))


def _names(path):
    names = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            names.add(re.split(r"[<>=~!\[ ]", line, maxsplit=1)[0].lower())
    return names


@pytest.fixture
def api_client(monkeypatch, tmp_path):
    """Load api/index.py the way Vercel does, with the backend in mock mode."""
    monkeypatch.setattr(config, "ENV_FILE", tmp_path / "missing.env")
    monkeypatch.setenv("CAREERPILOT_MOCK", "1")
    monkeypatch.delenv("CAREERPILOT_ALLOWED_ORIGINS", raising=False)
    sys.modules.pop("backend", None)
    spec = importlib.util.spec_from_file_location("vercel_entry", ROOT / "api" / "index.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.app.config["TESTING"] = True
    return module.app.test_client()


def test_function_answers_under_api(api_client):
    response = api_client.get("/api/")
    assert response.status_code == 200
    assert b"mock mode" in response.data
    assert api_client.get("/api").status_code == 200


def test_function_serves_the_sample_jobs(api_client):
    response = api_client.get("/api/latest_jobs")
    assert response.status_code == 200
    body = response.get_json()
    assert body["count"] == len(body["jobs"]) > 0


def test_prefix_is_only_stripped_at_the_start(api_client):
    assert api_client.get("/latest_jobs").status_code == 200
    assert api_client.get("/apilatest_jobs").status_code == 404


def test_root_requirements_cover_the_backend():
    hosted = _names(ROOT / "requirements.txt")
    local = _names(PROJECT / "requirements.txt")
    # The function needs every backend package except the local server and
    # the crawler's HTML parser, and nothing the backend does not use.
    assert hosted == local - {"gunicorn", "beautifulsoup4", "requests"}


def test_vercel_routes_api_to_the_function_and_serves_the_pages():
    assert VERCEL_JSON["outputDirectory"] == "site"
    assert "scripts/build-site.mjs" in VERCEL_JSON["buildCommand"]
    rewrites = {r["source"]: r["destination"] for r in VERCEL_JSON["rewrites"]}
    assert rewrites["/api/(.*)"] == "/api/index"
    assert "Project/**" in VERCEL_JSON["functions"]["api/index.py"]["includeFiles"]


def test_secrets_are_never_uploaded():
    ignored = (ROOT / ".vercelignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in ignored and "Project/.env" in ignored


NODE_CHECK = """
const fs = require('fs');
const vm = require('vm');
const sandbox = { window: {} };
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox);
const cp = sandbox.window.CareerPilot;
console.log(JSON.stringify({ jobs: cp.api('/latest_jobs'), room: cp.meet('/rooms/test-room') }));
"""


def _build(tmp_path, env=None):
    out = tmp_path / "site"
    subprocess.run(
        ["node", str(ROOT / "scripts" / "build-site.mjs"), str(out)],
        check=True,
        capture_output=True,
        env={"PATH": "/usr/bin:/bin:/usr/local/bin", **(env or {})},
    )
    return out


def _urls(settings_js):
    output = subprocess.run(
        ["node", "-e", NODE_CHECK, str(settings_js)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return json.loads(output)


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_built_site_calls_the_function_on_the_same_site(tmp_path):
    out = _build(tmp_path)
    assert sorted(p.name for p in out.iterdir()) == [
        "dashboard.html",
        "index.html",
        "settings.js",
    ]
    assert _urls(out / "settings.js") == {
        "jobs": "/api/latest_jobs",
        "room": "http://localhost:3000/rooms/test-room",
    }


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_built_site_takes_the_interview_room_address(tmp_path):
    out = _build(tmp_path, {"CAREERPILOT_MEET_URL": "https://meet.example.test/"})
    assert _urls(out / "settings.js")["room"] == "https://meet.example.test/rooms/test-room"

"""Checks for the static GitHub Pages demo that replays recorded backend answers."""

import importlib.util
import json
import shutil
import subprocess
import sys

import pytest

import config
from conftest import ROOT

NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node is not installed")


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def recorder(monkeypatch):
    for name in ("CAREERPILOT_MOCK", "MONGO_URI", "ACTIVEPIECES_JOB_SEARCH_WEBHOOK"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ACTIVEPIECES_RESUME_MATCH_WEBHOOK", "https://example.test/real-hook")
    # The recorder points config at a missing .env file; put it back afterwards.
    monkeypatch.setattr(config, "ENV_FILE", config.ENV_FILE)
    module = _load(ROOT / "scripts" / "record_demo_api.py", "record_demo_api")
    yield module
    sys.modules.pop("backend", None)


@pytest.fixture
def recorded(recorder, tmp_path):
    out = tmp_path / "demo-api.json"
    recorder.main([str(out)])
    return out


def test_recorder_covers_every_call_the_pages_make(recorded):
    answers = json.loads(recorded.read_text(encoding="utf-8"))
    assert set(answers) == {
        "GET /",
        "GET /health",
        "GET /latest_jobs",
        "POST /trigger",
        "POST /upload_resume",
        "POST /run_agents",
        "GET /cancel_file1",
    }
    assert all(answer["status"] == 200 for answer in answers.values())
    jobs = answers["GET /latest_jobs"]["body"]
    assert jobs["count"] == len(jobs["jobs"]) > 0
    assert answers["GET /health"]["body"]["mode"] == "mock"


def test_recorder_never_writes_a_real_setting(recorded):
    text = recorded.read_text(encoding="utf-8")
    assert "example.test/real-hook" not in text
    assert "mongodb+srv" not in text and "mongodb://" not in text


def _build(tmp_path, recorded):
    out = tmp_path / "pages-site"
    subprocess.run(
        [NODE, str(ROOT / "scripts" / "build-site.mjs"), str(out)],
        check=True,
        capture_output=True,
        env={"PATH": "/usr/bin:/bin:/usr/local/bin", "CAREERPILOT_DEMO_RESPONSES": str(recorded)},
    )
    return out


@needs_node
def test_static_build_carries_the_recordings_and_a_room_notice(tmp_path, recorded):
    out = _build(tmp_path, recorded)
    files = sorted(str(p.relative_to(out)) for p in out.rglob("*") if p.is_file())
    assert files == [
        "dashboard.html",
        "index.html",
        "rooms/test-room/index.html",
        "settings.js",
    ]
    settings = (out / "settings.js").read_text(encoding="utf-8")
    assert '"apiUrl":"demo-api"' in settings
    assert '"meetUrl":"."' in settings
    assert "window.CAREERPILOT_DEMO_RESPONSES = " in settings
    assert "Back to the dashboard" in (out / "rooms/test-room/index.html").read_text(encoding="utf-8")


BROWSER_CHECK = """
const fs = require('fs');
const vm = require('vm');
const calls = [];
const window = {
  fetch: (url) => { calls.push(String(url)); return Promise.resolve('network'); },
};
const sandbox = { window, Response, JSON, Promise, String };
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox);
const cp = window.CareerPilot;
(async () => {
  const jobs = await window.fetch(cp.api('/latest_jobs?limit=5'), { method: 'GET' });
  const trigger = await window.fetch(cp.api('/trigger'), { method: 'POST' });
  const missing = await window.fetch(cp.api('/nothing'), { method: 'DELETE' });
  const other = await window.fetch('https://example.test/other');
  console.log(JSON.stringify({
    jobs: (await jobs.json()).count,
    trigger: trigger.status,
    missing: missing.status,
    other,
    calls,
    room: cp.meet('/rooms/test-room'),
  }));
})();
"""


@needs_node
def test_built_pages_answer_backend_calls_from_the_recordings(tmp_path, recorded):
    out = _build(tmp_path, recorded)
    result = json.loads(
        subprocess.run(
            [NODE, "-e", BROWSER_CHECK, str(out / "settings.js")],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    assert result == {
        "jobs": 3,
        "trigger": 200,
        "missing": 404,
        "other": "network",
        "calls": ["https://example.test/other"],
        "room": "./rooms/test-room",
    }


live_check = _load(ROOT / ".github" / "scripts" / "live_check.py", "live_check_static")
PAGES = "https://rohitdurbha.github.io/CareerPilot"


def _static_answers(settings_body):
    return {
        PAGES + "/": (200, '<script src="settings.js"></script>'),
        PAGES + "/dashboard.html": (200, "CareerPilot.api('/latest_jobs')"),
        PAGES + "/settings.js": (200, settings_body),
        PAGES + "/rooms/test-room/": (200, "<title>CareerPilot interview room</title>"),
    }


def test_static_live_check_passes_for_the_pages_site():
    settings = '{"apiUrl":"demo-api"} "GET /latest_jobs" function createDemoFetch'
    answers = _static_answers(settings)
    assert live_check.run(PAGES + "/", attempts=1, pause=0, fetch=answers.__getitem__, static=True) == []


def test_static_live_check_fails_without_the_recordings():
    answers = _static_answers('{"apiUrl":"/api"}')
    failed = live_check.run(PAGES, attempts=1, pause=0, fetch=answers.__getitem__, static=True)
    assert failed == ["recorded backend"]


def test_pages_workflow_records_builds_and_checks_without_secrets():
    workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
    assert "secrets." not in workflow
    assert "python -m pytest -q" in workflow
    assert "scripts/record_demo_api.py" in workflow
    assert "CAREERPILOT_DEMO_RESPONSES" in workflow
    assert "actions/deploy-pages" in workflow
    assert "live_check.py" in workflow and "--static" in workflow

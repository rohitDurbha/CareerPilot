"""Checks that the HTML pages take their addresses from Project/settings.js."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT / "Project"
SETTINGS_JS = PROJECT / "settings.js"
PAGES = ["index.html", "dashboard.html"]
HARDCODED = re.compile(r"https?://(localhost|127\.0\.0\.1)")


@pytest.mark.parametrize("page", PAGES)
def test_pages_have_no_hardcoded_local_addresses(page):
    html = (PROJECT / page).read_text(encoding="utf-8")
    assert not HARDCODED.search(html)


@pytest.mark.parametrize("page", PAGES)
def test_pages_load_settings_before_their_own_scripts(page):
    html = (PROJECT / page).read_text(encoding="utf-8")
    settings_tag = html.find('<script src="settings.js"></script>')
    first_inline_script = html.find("<script>")
    assert settings_tag != -1
    assert first_inline_script == -1 or settings_tag < first_inline_script


def test_dashboard_uses_both_settings():
    html = (PROJECT / "dashboard.html").read_text(encoding="utf-8")
    assert "CareerPilot.api('/latest_jobs')" in html
    assert "CareerPilot.api('/run_agents')" in html
    assert "CareerPilot.meet('/rooms/test-room')" in html


def test_settings_defaults_point_at_local_servers():
    source = SETTINGS_JS.read_text(encoding="utf-8")
    assert "apiUrl: 'http://localhost:5001'" in source
    assert "meetUrl: 'http://localhost:3000'" in source


NODE_SCRIPT = """
const { buildSettings } = require(process.argv[1]);
const local = buildSettings();
const hosted = buildSettings({ apiUrl: 'https://api.example.test/', meetUrl: 'https://meet.example.test//' });
console.log(JSON.stringify({
  localApi: local.api('/trigger'),
  localMeet: local.meet('/rooms/test-room'),
  hostedApi: hosted.api('latest_jobs'),
  hostedMeet: hosted.meet('/rooms/test-room'),
  hostedBase: hosted.api(''),
}));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_settings_join_addresses_and_paths():
    output = subprocess.run(
        ["node", "-e", NODE_SCRIPT, str(SETTINGS_JS)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    urls = json.loads(output)
    assert urls == {
        "localApi": "http://localhost:5001/trigger",
        "localMeet": "http://localhost:3000/rooms/test-room",
        "hostedApi": "https://api.example.test/latest_jobs",
        "hostedMeet": "https://meet.example.test/rooms/test-room",
        "hostedBase": "https://api.example.test",
    }

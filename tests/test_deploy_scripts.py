"""Checks for the scripts the deploy workflow runs, with the network stubbed out."""

import importlib.util

from conftest import ROOT


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / ".github" / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


production_url = _load("production_url")
live_check = _load("live_check")

SITE = "https://careerpilot-demo.vercel.app"
MEET = "https://careerpilot-meet.vercel.app"


def test_production_url_picks_the_shortest_vercel_alias(capsys):
    deployment = {
        "alias": [
            "careerpilot-demo-git-main-rohit.vercel.app",
            "careerpilot-demo.vercel.app",
            "careers.example.com",
        ]
    }
    seen = []

    def fake_fetch(host, token):
        seen.append((host, token))
        return deployment

    code = production_url.main(
        ["x", "https://careerpilot-demo-abc123.vercel.app/\n"], {"VERCEL_TOKEN": "t"}, fake_fetch
    )
    assert code == 0
    assert seen == [("careerpilot-demo-abc123.vercel.app", "t")]
    assert capsys.readouterr().out.strip() == SITE


def test_production_url_falls_back_to_the_deployment_address(capsys):
    def broken_fetch(host, token):
        raise OSError("network down")

    production_url.main(["x", "https://one-off.vercel.app"], {}, broken_fetch)
    assert capsys.readouterr().out.strip() == "https://one-off.vercel.app"


def _site_answers(meet_url=MEET):
    settings = 'window.CAREERPILOT_SETTINGS = Object.assign({"apiUrl":"/api","meetUrl":"%s"}' % meet_url
    return {
        SITE + "/": (200, '<script src="settings.js"></script>'),
        SITE + "/dashboard.html": (200, "fetch(latest_jobs)"),
        SITE + "/settings.js": (200, settings),
        SITE + "/api/": (200, "Backend is running"),
        SITE + "/api/latest_jobs": (200, '{"count": 1, "jobs": [{}]}'),
        SITE + "/api/health": (200, '{"mode": "mock", "ready": true, "missing": []}'),
        MEET + "/": (200, "<html>"),
        MEET + "/api/health": (200, '{"ok": true, "livekitConfigured": false}'),
        MEET + "/rooms/test-room": (200, "<html>"),
    }


def test_live_check_passes_for_the_site_and_the_room():
    answers = _site_answers()
    assert live_check.run(SITE, MEET, attempts=1, pause=0, fetch=answers.__getitem__) == []


def test_live_check_without_a_room_skips_the_room_checks():
    answers = _site_answers()
    asked = []

    def fetch(url):
        asked.append(url)
        return answers[url]

    assert live_check.run(SITE + "/", attempts=1, pause=0, fetch=fetch) == []
    assert not any(url.startswith(MEET) for url in asked)


def test_live_check_fails_when_the_pages_point_at_another_room():
    answers = _site_answers(meet_url="http://localhost:3000")
    failed = live_check.run(SITE, MEET, attempts=1, pause=0, fetch=answers.__getitem__)
    assert failed == ["room link"]


def test_live_check_fails_when_the_room_health_is_broken():
    answers = _site_answers()
    answers[MEET + "/api/health"] = (500, "Internal Server Error")
    failed = live_check.run(SITE, MEET, attempts=1, pause=0, fetch=answers.__getitem__)
    assert failed == ["room health"]


def test_deploy_publishes_the_interview_room_and_checks_it():
    workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
    assert 'vercel_deploy.sh meet "$MEET_PROJECT"' in workflow
    assert "NEXT_PUBLIC_CAREERPILOT_API_URL=${{ steps.site.outputs.url }}/api" in workflow
    assert '--build-env "CAREERPILOT_MEET_URL=$meet"' in workflow
    assert '--env "CAREERPILOT_ALLOWED_ORIGINS=$meet"' in workflow
    assert '--meet "${{ steps.meet.outputs.url }}"' in workflow
    # The room's LiveKit secret must reach the server only, never the browser build.
    assert "NEXT_PUBLIC_LIVEKIT" not in workflow


def test_interview_room_uploads_no_local_secrets():
    ignored = (ROOT / "meet" / ".vercelignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in ignored and ".env.*" in ignored and "!.env.example" in ignored
    import json

    settings = json.loads((ROOT / "meet" / "vercel.json").read_text(encoding="utf-8"))
    assert settings["framework"] == "nextjs"
    assert settings["installCommand"].startswith("npm ci")


def test_live_check_fails_when_the_backend_is_missing_a_service():
    answers = _site_answers()
    answers[SITE + "/api/health"] = (200, '{"mode": "live", "ready": false, "missing": ["MONGO_URI"]}')
    failed = live_check.run(SITE, MEET, attempts=1, pause=0, fetch=answers.__getitem__)
    assert failed == ["backend health"]

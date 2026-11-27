"""Check that the hosted CareerPilot demo serves its pages and its backend.

Run it with the site address, and optionally the interview room address,
for example

    python .github/scripts/live_check.py https://careerpilot-demo.vercel.app \
        --meet https://careerpilot-meet.vercel.app

For the static GitHub Pages demo, which answers backend calls from recordings
in settings.js, add --static instead

    python .github/scripts/live_check.py https://rohitdurbha.github.io/CareerPilot --static

Every request is read only, so it is safe to run at any time. The script prints
one line per check, retries a few times while a fresh deploy warms up, and
exits with status 1 when any check still fails.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request


def fetch(url, timeout=60):
    request = urllib.request.Request(url, headers={"User-Agent": "careerpilot-live-check"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace")
    except OSError as error:
        return 0, str(error)


def jobs_listed(body):
    try:
        data = json.loads(body)
    except ValueError:
        return False
    return data.get("count", 0) > 0 and len(data.get("jobs") or []) == data["count"]


def backend_ready(body):
    try:
        return json.loads(body).get("ready") is True
    except (ValueError, AttributeError):
        return False


CHECKS = [
    ("search page", "/", lambda s, b: s == 200 and "settings.js" in b),
    ("dashboard page", "/dashboard.html", lambda s, b: s == 200 and "latest_jobs" in b),
    ("hosted settings", "/settings.js", lambda s, b: s == 200 and '"apiUrl":"/api"' in b),
    ("backend", "/api/", lambda s, b: s == 200 and "Backend is running" in b),
    ("sample jobs", "/api/latest_jobs", lambda s, b: s == 200 and jobs_listed(b)),
    ("backend health", "/api/health", lambda s, b: s == 200 and backend_ready(b)),
]


def health_ok(body):
    try:
        return json.loads(body).get("ok") is True
    except (ValueError, AttributeError):
        return False


MEET_CHECKS = [
    ("room home", "/", lambda s, b: s == 200),
    ("room health", "/api/health", lambda s, b: s == 200 and health_ok(b)),
    ("interview room", "/rooms/test-room", lambda s, b: s == 200),
]


STATIC_CHECKS = [
    ("search page", "/", lambda s, b: s == 200 and "settings.js" in b),
    ("dashboard page", "/dashboard.html", lambda s, b: s == 200 and "latest_jobs" in b),
    (
        "recorded backend",
        "/settings.js",
        lambda s, b: s == 200
        and '"apiUrl":"demo-api"' in b
        and '"GET /latest_jobs"' in b
        and "createDemoFetch" in b,
    ),
    ("room notice", "/rooms/test-room/", lambda s, b: s == 200 and "interview room" in b),
]


def plan(site, meet=None, static=False):
    """List (name, url, check) for the site and, when given, the interview room."""
    site = site.rstrip("/")
    if static:
        return [(name, site + path, passes) for name, path, passes in STATIC_CHECKS]
    checks = [(name, site + path, passes) for name, path, passes in CHECKS]
    if meet:
        meet = meet.rstrip("/")
        checks.append(
            ("room link", site + "/settings.js", lambda s, b: s == 200 and meet in b)
        )
        checks += [(name, meet + path, passes) for name, path, passes in MEET_CHECKS]
    return checks


def run(site, meet=None, attempts=5, pause=10, fetch=fetch, static=False):
    failed = []
    for name, url, passes in plan(site, meet, static):
        for attempt in range(1, attempts + 1):
            status, body = fetch(url)
            if passes(status, body):
                print(f"ok    {name:16} {url} answered {status}")
                break
            if attempt == attempts:
                print(f"FAIL  {name:16} {url} answered {status}: {body[:200]!r}")
                failed.append(name)
            else:
                time.sleep(pause)
    return failed


if __name__ == "__main__":
    args = sys.argv[1:]
    meet = None
    static = "--static" in args
    args = [arg for arg in args if arg != "--static"]
    if len(args) == 3 and args[1] == "--meet":
        meet = args[2]
        args = args[:1]
    if len(args) != 1:
        sys.exit(
            "usage: live_check.py https://site.example [--meet https://room.example | --static]"
        )
    sys.exit(1 if run(args[0], meet, static=static) else 0)

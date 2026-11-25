"""Check that the hosted CareerPilot demo serves its pages and its backend.

Run it with the site address, for example

    python .github/scripts/live_check.py https://careerpilot-demo.vercel.app

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


CHECKS = [
    ("search page", "/", lambda s, b: s == 200 and "settings.js" in b),
    ("dashboard page", "/dashboard.html", lambda s, b: s == 200 and "latest_jobs" in b),
    ("hosted settings", "/settings.js", lambda s, b: s == 200 and '"apiUrl":"/api"' in b),
    ("backend", "/api/", lambda s, b: s == 200 and "Backend is running" in b),
    ("sample jobs", "/api/latest_jobs", lambda s, b: s == 200 and jobs_listed(b)),
]


def run(site, attempts=5, pause=10):
    site = site.rstrip("/")
    failed = []
    for name, path, passes in CHECKS:
        for attempt in range(1, attempts + 1):
            status, body = fetch(site + path)
            if passes(status, body):
                print(f"ok    {name:16} {path} answered {status}")
                break
            if attempt == attempts:
                print(f"FAIL  {name:16} {path} answered {status}: {body[:200]!r}")
                failed.append(name)
            else:
                time.sleep(pause)
    return failed


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: live_check.py https://site.example")
    sys.exit(1 if run(sys.argv[1]) else 0)

"""Replays sample Activepieces responses so the backend works without accounts.

Turn it on with ``CAREERPILOT_MOCK=1``. The backend then hands out ``mock://``
addresses instead of real webhook URLs, and any POST to one of them is answered
from the JSON files in ``Project/mock_data`` without touching the network.
"""

import copy
import json
from pathlib import Path

MOCK_DATA_DIR = Path(__file__).resolve().parent / "mock_data"
MOCK_SCHEME = "mock://"

JOB_SEARCH_URL = MOCK_SCHEME + "job-search"
RESUME_MATCH_URL = MOCK_SCHEME + "resume-match"

SAMPLE_FILES = {
    JOB_SEARCH_URL: "job_search.json",
    RESUME_MATCH_URL: "resume_match.json",
}


class UnknownMockWorkflow(LookupError):
    """Raised when a mock:// address has no sample payload behind it."""


def is_mock_url(url):
    return isinstance(url, str) and url.startswith(MOCK_SCHEME)


def load_sample(name):
    with open(MOCK_DATA_DIR / name, encoding="utf-8") as handle:
        return json.load(handle)


def replay(url, payload):
    """Return the sample response for a mock workflow, shaped like a real call.

    The request payload is echoed back under ``received`` (minus any resume
    text, which is reduced to its length) so callers can see what was sent.
    """
    try:
        name = SAMPLE_FILES[url]
    except KeyError:
        raise UnknownMockWorkflow(f"No sample payload for {url}") from None

    data = copy.deepcopy(load_sample(name))
    received = dict(payload or {})
    if "resume_text" in received:
        received["resume_text_length"] = len(received.pop("resume_text") or "")
    data["mock"] = True
    data["received"] = received
    return {"status": 200, "data": data}


def latest_jobs(limit):
    """Return the sample jobs joined with their scores, like ``/latest_jobs``.

    Each job gets its score fields merged in and a ``lastUpdatedTime`` taken
    from ``publishedAt``. Jobs are ordered the way the MongoDB query orders
    them, newest first and then by highest score, and cut to ``limit``.
    """
    jobs = load_sample("job_search.json")["jobs"]
    scores = {
        score["jobId"]: score
        for score in load_sample("resume_match.json")["scores"]
    }

    joined = []
    for job in jobs:
        doc = dict(job)
        doc["_id"] = job["jobId"]
        doc["lastUpdatedTime"] = job.get("publishedAt", "")
        score = scores.get(job["jobId"], {})
        doc.update({key: value for key, value in score.items() if key != "jobId"})
        doc["mock"] = True
        joined.append(doc)

    # Two stable sorts give the same order as sorting on both keys at once.
    joined.sort(key=lambda doc: doc.get("resumeScore", 0), reverse=True)
    joined.sort(key=lambda doc: doc["lastUpdatedTime"], reverse=True)
    return joined[:limit]

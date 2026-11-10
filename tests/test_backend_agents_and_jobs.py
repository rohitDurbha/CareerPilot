"""Covers the interview agent routes and the latest jobs route of the Flask backend."""

import pytest
from bson import ObjectId


class FakeProcess:
    _next_pid = 1000

    def __init__(self, args, running=True, fail_terminate=False):
        FakeProcess._next_pid += 1
        self.pid = FakeProcess._next_pid
        self.args = args
        self.running = running
        self.fail_terminate = fail_terminate
        self.terminated = False

    def poll(self):
        return None if self.running else 0

    def terminate(self):
        if self.fail_terminate:
            raise OSError("permission denied")
        self.terminated = True
        self.running = False

    def wait(self, timeout=None):
        return 0


@pytest.fixture
def launched(monkeypatch, backend):
    started = []

    def fake_popen(args):
        proc = FakeProcess(args)
        started.append(proc)
        return proc

    monkeypatch.setattr(backend.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(backend, "agent_procs", {"agent1": None, "agent2": None})
    return started


def test_run_agents_starts_the_interviewer_and_transcriber(backend, launched):
    response = backend.app.test_client().post(
        "/run_agents", json={"job_title": "Data Analyst", "job_description": "SQL"}
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "started"
    assert body["received"] == {"job_title": "Data Analyst", "job_description": "SQL"}
    assert body["pids"] == {"agent1": launched[0].pid, "agent2": launched[1].pid}
    assert launched[0].args[1] == backend.INTERVIEWER_SCRIPT
    assert launched[1].args[1] == backend.TRANSCRIBER_SCRIPT
    for proc in launched:
        assert proc.args[2:] == ["connect", "--room", "test-room"]


def test_run_agents_reports_a_launch_failure(monkeypatch, backend):
    def failing_popen(args):
        raise FileNotFoundError("python not found")

    monkeypatch.setattr(backend.subprocess, "Popen", failing_popen)
    response = backend.app.test_client().post("/run_agents", json={})

    assert response.status_code == 500
    assert response.get_json() == {"status": "error", "error": "python not found"}


def test_cancel_stops_running_agents_and_clears_them(backend, launched):
    client = backend.app.test_client()
    client.post("/run_agents", json={})
    response = client.get("/cancel_file1")

    assert response.status_code == 200
    assert response.get_json()["details"] == {"agent1": "terminated", "agent2": "terminated"}
    assert all(proc.terminated for proc in launched)
    assert backend.agent_procs == {"agent1": None, "agent2": None}


def test_cancel_reports_agents_that_were_not_running(monkeypatch, backend):
    finished = FakeProcess(["done"], running=False)
    monkeypatch.setattr(backend, "agent_procs", {"agent1": finished, "agent2": None})
    response = backend.app.test_client().get("/cancel_file1")

    assert response.get_json()["details"] == {"agent1": "not running", "agent2": "not running"}
    assert not finished.terminated


def test_cancel_reports_an_agent_that_will_not_stop(monkeypatch, backend):
    stuck = FakeProcess(["stuck"], fail_terminate=True)
    monkeypatch.setattr(backend, "agent_procs", {"agent1": stuck, "agent2": None})
    response = backend.app.test_client().get("/cancel_file1")

    details = response.get_json()["details"]
    assert details["agent1"] == "error terminating: permission denied"
    assert backend.agent_procs["agent1"] is None


class FakeCursor:
    def __init__(self, docs):
        self.docs = docs
        self.sort_keys = None
        self.limit_value = None

    def sort(self, keys):
        self.sort_keys = keys
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def __iter__(self):
        return iter(self.docs[: self.limit_value])


class FakeCollection:
    def __init__(self, docs=None, error=None):
        self.cursor = FakeCursor(docs or [])
        self.error = error

    def find(self):
        if self.error:
            raise self.error
        return self.cursor


def test_latest_jobs_returns_newest_and_best_scored_first(monkeypatch, backend):
    first_id = ObjectId()
    docs = [
        {"_id": first_id, "title": "Data Analyst", "resumeScore": 91},
        {"_id": ObjectId(), "title": "BI Engineer", "resumeScore": 77},
        {"_id": ObjectId(), "title": "ML Intern", "resumeScore": 60},
    ]
    collection = FakeCollection(docs)
    monkeypatch.setattr(backend, "pymongo_collection", collection)
    response = backend.app.test_client().get("/latest_jobs?limit=2")

    assert response.status_code == 200
    body = response.get_json()
    assert body["count"] == 2
    assert body["jobs"][0] == {"_id": str(first_id), "title": "Data Analyst", "resumeScore": 91}
    assert collection.cursor.sort_keys == [("lastUpdatedTime", -1), ("resumeScore", -1)]
    assert collection.cursor.limit_value == 2


def test_latest_jobs_defaults_to_twenty(monkeypatch, backend):
    collection = FakeCollection([])
    monkeypatch.setattr(backend, "pymongo_collection", collection)
    response = backend.app.test_client().get("/latest_jobs")

    assert response.get_json() == {"count": 0, "jobs": []}
    assert collection.cursor.limit_value == 20


@pytest.mark.parametrize("limit", ["abc", "0", "-5"])
def test_latest_jobs_rejects_a_bad_limit(monkeypatch, backend, limit):
    collection = FakeCollection([])
    monkeypatch.setattr(backend, "pymongo_collection", collection)
    response = backend.app.test_client().get(f"/latest_jobs?limit={limit}")

    assert response.status_code == 400
    assert "limit" in response.get_json()["error"]
    assert collection.cursor.limit_value is None


def test_latest_jobs_reports_a_database_failure(monkeypatch, backend):
    monkeypatch.setattr(
        backend, "pymongo_collection", FakeCollection(error=RuntimeError("timed out"))
    )
    response = backend.app.test_client().get("/latest_jobs")

    assert response.status_code == 500
    assert response.get_json()["details"] == "timed out"

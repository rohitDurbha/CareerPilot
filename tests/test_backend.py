"""Checks the single Flask backend that replaced app.py and backend.py."""

import io

from conftest import MATCH_URL, PROJECT, SEARCH_URL, FakeReader


def stub_workflows(monkeypatch, backend, statuses):
    calls = []

    async def fake_trigger(url, payload):
        calls.append((url, payload))
        return {"status": statuses[url], "data": {"ok": statuses[url] == 200}}

    monkeypatch.setattr(backend, "trigger_workflow", fake_trigger)
    return calls


def post_trigger(backend):
    data = {
        "keyword": "data analyst",
        "location": "San Jose",
        "resume": (io.BytesIO(b"%PDF-1.4"), "resume.pdf"),
    }
    return backend.app.test_client().post(
        "/trigger", data=data, content_type="multipart/form-data"
    )


def test_only_one_flask_app_remains():
    assert not (PROJECT / "app.py").exists()
    assert (PROJECT / "backend.py").is_file()


def test_backend_does_not_import_supabase():
    source = (PROJECT / "backend.py").read_text(encoding="utf-8")
    assert "supabase" not in source
    assert "motor" not in source


def test_trigger_runs_both_workflows_in_order(monkeypatch, backend):
    calls = stub_workflows(monkeypatch, backend, {SEARCH_URL: 200, MATCH_URL: 200})
    response = post_trigger(backend)

    assert response.status_code == 200
    body = response.get_json()
    assert body["message"] == "Both workflows succeeded"
    assert [url for url, _ in calls] == [SEARCH_URL, MATCH_URL]
    assert calls[0][1] == {
        "keyword": ["data analyst"],
        "location": "San Jose",
        "publishedAt": "r86400",
    }
    assert "analytics" in calls[1][1]["resume_text"]


def test_failed_job_search_skips_the_match_and_reports_an_error(monkeypatch, backend):
    calls = stub_workflows(monkeypatch, backend, {SEARCH_URL: 500, MATCH_URL: 200})
    response = post_trigger(backend)

    assert response.status_code == 502
    assert response.get_json()["message"] == "Job search workflow failed"
    assert [url for url, _ in calls] == [SEARCH_URL]


def test_failed_resume_match_reports_an_error(monkeypatch, backend):
    stub_workflows(monkeypatch, backend, {SEARCH_URL: 200, MATCH_URL: 404})
    response = post_trigger(backend)

    assert response.status_code == 502
    body = response.get_json()
    assert body["message"] == "Resume match workflow failed"
    assert [r["status"] for r in body["results"]] == [200, 404]


def test_trigger_needs_a_resume(monkeypatch, backend):
    stub_workflows(monkeypatch, backend, {SEARCH_URL: 200, MATCH_URL: 200})
    response = backend.app.test_client().post(
        "/trigger", data={"keyword": "data analyst"}, content_type="multipart/form-data"
    )
    assert response.status_code == 400


def test_unreadable_resume_is_rejected(monkeypatch, backend):
    calls = stub_workflows(monkeypatch, backend, {SEARCH_URL: 200, MATCH_URL: 200})
    monkeypatch.setattr(backend, "PdfReader", lambda f: FakeReader(f, text="   "))
    response = post_trigger(backend)

    assert response.status_code == 400
    assert calls == []

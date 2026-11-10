"""Covers the health check and the resume upload route of the Flask backend."""

import io

from conftest import SEARCH_URL, FakeReader


def stub_activepieces(monkeypatch, backend, status=200, data=None):
    calls = []

    async def fake_send(req, resume_text, url):
        calls.append(
            {
                "url": url,
                "resume_text": resume_text,
                "job_id": req.form.get("job_id", ""),
                "email": req.form.get("email", ""),
            }
        )
        return {"status": status, "data": data if data is not None else {"score": 82}}

    monkeypatch.setattr(backend, "send_resume_to_activepieces", fake_send)
    return calls


def post_resume(backend, **fields):
    data = {"resume": (io.BytesIO(b"%PDF-1.4"), "resume.pdf"), **fields}
    return backend.app.test_client().post(
        "/upload_resume", data=data, content_type="multipart/form-data"
    )


def test_home_reports_that_the_backend_is_running(backend):
    response = backend.app.test_client().get("/")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "Backend is running."


def test_upload_sends_the_resume_text_and_form_fields(monkeypatch, backend):
    calls = stub_activepieces(monkeypatch, backend)
    response = post_resume(backend, job_id="job-42", email="someone@example.test")

    assert response.status_code == 200
    assert response.get_json() == {"status": 200, "data": {"score": 82}}
    assert len(calls) == 1
    assert calls[0]["url"] == SEARCH_URL
    assert "analytics" in calls[0]["resume_text"]
    assert calls[0]["job_id"] == "job-42"
    assert calls[0]["email"] == "someone@example.test"


def test_upload_passes_the_workflow_status_through(monkeypatch, backend):
    stub_activepieces(monkeypatch, backend, status=500, data="flow error")
    response = post_resume(backend)

    assert response.status_code == 200
    assert response.get_json() == {"status": 500, "data": "flow error"}


def test_upload_needs_a_resume_file(monkeypatch, backend):
    calls = stub_activepieces(monkeypatch, backend)
    response = backend.app.test_client().post(
        "/upload_resume", data={"job_id": "job-42"}, content_type="multipart/form-data"
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "No resume uploaded"
    assert calls == []


def test_upload_rejects_a_resume_without_text(monkeypatch, backend):
    calls = stub_activepieces(monkeypatch, backend)
    monkeypatch.setattr(backend, "PdfReader", lambda f: FakeReader(f, text=""))
    response = post_resume(backend)

    assert response.status_code == 400
    assert calls == []


def test_upload_turns_a_broken_pdf_into_a_server_error(monkeypatch, backend):
    calls = stub_activepieces(monkeypatch, backend)

    def broken_reader(_file):
        raise ValueError("not a PDF")

    monkeypatch.setattr(backend, "PdfReader", broken_reader)
    response = post_resume(backend)

    assert response.status_code == 500
    assert response.get_json()["details"] == "not a PDF"
    assert calls == []

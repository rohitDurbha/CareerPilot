"""Checks the mock mode that replays sample Activepieces payloads."""

import asyncio
import io

import pytest

import config
import mock_workflows


def post_with_resume(backend, route, **fields):
    data = {"resume": (io.BytesIO(b"%PDF-1.4"), "resume.pdf"), **fields}
    return backend.app.test_client().post(
        route, data=data, content_type="multipart/form-data"
    )


def refuse_network(monkeypatch, backend):
    class NoSession:
        def __init__(self, *args, **kwargs):
            raise AssertionError("mock mode must not open a network session")

    monkeypatch.setattr(backend.aiohttp, "ClientSession", NoSession)


@pytest.mark.parametrize("value", ["1", "true", "YES", " on "])
def test_mock_flag_accepts_common_true_words(monkeypatch, tmp_path, value):
    monkeypatch.setenv("CAREERPILOT_MOCK", value)
    assert config.load_settings(env_file=tmp_path / "missing.env").mock_mode is True


@pytest.mark.parametrize("value", ["", "0", "false", "off", "maybe"])
def test_mock_flag_is_off_otherwise(monkeypatch, tmp_path, value):
    monkeypatch.setenv("CAREERPILOT_MOCK", value)
    assert config.load_settings(env_file=tmp_path / "missing.env").mock_mode is False


def test_every_mock_url_has_a_sample_file():
    for name in mock_workflows.SAMPLE_FILES.values():
        assert (mock_workflows.MOCK_DATA_DIR / name).is_file()


def test_sample_scores_refer_to_sample_jobs():
    jobs = mock_workflows.load_sample("job_search.json")["jobs"]
    scores = mock_workflows.load_sample("resume_match.json")["scores"]
    job_ids = {job["jobId"] for job in jobs}
    assert job_ids and {score["jobId"] for score in scores} == job_ids
    for score in scores:
        assert 0 <= score["resumeScore"] <= 100


def test_replay_hides_the_resume_text_and_does_not_share_state():
    first = mock_workflows.replay(
        mock_workflows.RESUME_MATCH_URL, {"resume_text": "five words of resume text"}
    )
    assert first["status"] == 200
    assert first["data"]["received"] == {"resume_text_length": 25}
    first["data"]["scores"].clear()

    second = mock_workflows.replay(mock_workflows.RESUME_MATCH_URL, {})
    assert len(second["data"]["scores"]) == 3


def test_replay_rejects_an_unknown_workflow():
    with pytest.raises(mock_workflows.UnknownMockWorkflow):
        mock_workflows.replay("mock://nothing-here", {})


def test_home_says_when_mock_mode_is_on(mock_backend):
    response = mock_backend.app.test_client().get("/")
    assert response.get_data(as_text=True) == "Backend is running in mock mode."


def test_trigger_replays_both_workflows_without_webhooks(monkeypatch, mock_backend):
    refuse_network(monkeypatch, mock_backend)
    response = post_with_resume(
        mock_backend, "/trigger", keyword="data analyst", location="San Jose"
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["message"] == "Both workflows succeeded"
    search, match = body["results"]
    assert search["data"]["mock"] is True
    assert search["data"]["received"]["keyword"] == ["data analyst"]
    assert len(search["data"]["jobs"]) == 3
    assert match["data"]["received"]["resume_text_length"] > 0
    assert "resume_text" not in match["data"]["received"]


def test_upload_resume_replays_the_job_search_sample(monkeypatch, mock_backend):
    refuse_network(monkeypatch, mock_backend)
    response = post_with_resume(mock_backend, "/upload_resume", job_id="mock-1001")

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == 200
    assert body["data"]["received"]["job_id"] == "mock-1001"


def test_real_urls_still_go_over_the_network(monkeypatch, backend):
    calls = []

    class FakeResponse:
        status = 201

        async def json(self):
            return {"ok": True}

    class FakeSession:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        def post(self, url, json):
            calls.append(url)

            class Ctx:
                async def __aenter__(self_inner):
                    return FakeResponse()

                async def __aexit__(self_inner, *exc):
                    return False

            return Ctx()

    monkeypatch.setattr(backend.aiohttp, "ClientSession", FakeSession)
    result = asyncio.run(backend.trigger_workflow("https://example.test/hook", {}))
    assert result == {"status": 201, "data": {"ok": True}}
    assert calls == ["https://example.test/hook"]

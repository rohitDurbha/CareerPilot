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


def refuse_mongo(monkeypatch, backend):
    def no_client(*args, **kwargs):
        raise AssertionError("mock mode must not open a MongoDB connection")

    monkeypatch.setattr(backend, "MongoClient", no_client)


def test_sample_latest_jobs_are_newest_first_with_scores():
    jobs = mock_workflows.latest_jobs(10)
    assert [job["jobId"] for job in jobs] == ["mock-1003", "mock-1002", "mock-1001"]
    times = [job["lastUpdatedTime"] for job in jobs]
    assert times == sorted(times, reverse=True)
    first = jobs[0]
    assert first["resumeScore"] == 64
    assert first["missingSkills"] == ["Airflow", "Snowflake"]
    assert first["_id"] == "mock-1003"
    assert "jobId" in first and first["mock"] is True


def test_sample_latest_jobs_break_time_ties_by_score(monkeypatch):
    jobs = [
        {"jobId": "a", "publishedAt": "2026-11-10T00:00:00Z"},
        {"jobId": "b", "publishedAt": "2026-11-10T00:00:00Z"},
        {"jobId": "c", "publishedAt": "2026-11-09T00:00:00Z"},
    ]
    scores = [
        {"jobId": "a", "resumeScore": 50},
        {"jobId": "b", "resumeScore": 80},
        {"jobId": "c", "resumeScore": 99},
    ]
    samples = {
        "job_search.json": {"jobs": jobs},
        "resume_match.json": {"scores": scores},
    }
    monkeypatch.setattr(mock_workflows, "load_sample", lambda name: samples[name])
    assert [job["jobId"] for job in mock_workflows.latest_jobs(5)] == ["b", "a", "c"]


def test_latest_jobs_route_uses_the_samples_in_mock_mode(monkeypatch, mock_backend):
    refuse_mongo(monkeypatch, mock_backend)
    response = mock_backend.app.test_client().get("/latest_jobs?limit=2")

    assert response.status_code == 200
    body = response.get_json()
    assert body["mock"] is True
    assert body["count"] == 2
    assert [job["jobId"] for job in body["jobs"]] == ["mock-1003", "mock-1002"]


def test_latest_jobs_route_still_checks_the_limit_in_mock_mode(monkeypatch, mock_backend):
    refuse_mongo(monkeypatch, mock_backend)
    response = mock_backend.app.test_client().get("/latest_jobs?limit=0")
    assert response.status_code == 400


def test_backend_import_does_not_create_a_mongo_client(mock_backend):
    assert mock_backend.pymongo_collection is None


def test_real_mode_creates_the_mongo_client_once(monkeypatch, backend):
    created = []

    class FakeClient(dict):
        def __init__(self, uri):
            created.append(uri)
            super().__init__({backend.settings.mongo_db: {backend.settings.mongo_collection: "jobs"}})

    monkeypatch.setattr(backend, "MongoClient", FakeClient)
    assert backend.jobs_collection() == "jobs"
    assert backend.jobs_collection() == "jobs"
    assert created == [backend.settings.mongo_uri]

"""Checks for /health, which says which services the backend can reach."""

import json

import pytest

from conftest import MATCH_URL, SEARCH_URL, _fresh_backend

import config

ATLAS = "mongodb+srv://cs156:hunter2@cluster0.example.mongodb.net/?retryWrites=true"


def _health(backend):
    response = backend.app.test_client().get("/health")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    return response.get_data(as_text=True), response.get_json()


def test_health_in_mock_mode_is_ready_without_any_service(mock_backend, monkeypatch):
    text, body = _health(mock_backend)
    assert body["mode"] == "mock"
    assert body["ready"] is True
    assert body["services"] == {
        "mongodb": {"configured": False, "needed": False},
        "job_search_webhook": {"configured": False, "needed": False},
        "resume_match_webhook": {"configured": False, "needed": False},
    }
    assert body["missing"] == []


def test_health_lists_what_live_mode_still_needs(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "ENV_FILE", tmp_path / "missing.env")
    for name in (
        "CAREERPILOT_MOCK",
        "MONGO_URI",
        "ACTIVEPIECES_JOB_SEARCH_WEBHOOK",
        "ACTIVEPIECES_RESUME_MATCH_WEBHOOK",
    ):
        monkeypatch.delenv(name, raising=False)
    backend = _fresh_backend(monkeypatch)
    _, body = _health(backend)
    assert body["mode"] == "live"
    assert body["ready"] is False
    assert body["missing"] == [
        "MONGO_URI",
        "ACTIVEPIECES_JOB_SEARCH_WEBHOOK",
        "ACTIVEPIECES_RESUME_MATCH_WEBHOOK",
    ]
    assert body["services"]["mongodb"] == {"configured": False, "needed": True}


def test_health_is_ready_when_every_service_is_set(backend, monkeypatch, tmp_path):
    monkeypatch.setenv("MONGO_URI", ATLAS)
    backend = _fresh_backend(monkeypatch)
    text, body = _health(backend)
    assert body["mode"] == "live"
    assert body["ready"] is True
    assert body["missing"] == []
    assert all(s == {"configured": True, "needed": True} for s in body["services"].values())
    # Only yes or no answers leave the server, never a password or webhook address.
    for secret in ("hunter2", "cs156", "mongodb.net", SEARCH_URL, MATCH_URL, "example.test"):
        assert secret not in text


def test_health_never_opens_a_mongodb_connection(backend, monkeypatch):
    monkeypatch.setenv("MONGO_URI", ATLAS)
    backend = _fresh_backend(monkeypatch)

    def refuse(*args, **kwargs):
        raise AssertionError("/health must not connect to MongoDB")

    monkeypatch.setattr(backend, "MongoClient", refuse)
    _health(backend)

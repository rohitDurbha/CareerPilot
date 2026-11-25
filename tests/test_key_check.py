"""Checks for the daily Groq and Gemini key check, with the network stubbed out."""

import importlib.util

import pytest

from conftest import ROOT

spec = importlib.util.spec_from_file_location(
    "key_check", ROOT / ".github" / "scripts" / "key_check.py"
)
key_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(key_check)

GROQ_OK = (200, {"choices": [{"message": {"content": "ok"}}], "usage": {"total_tokens": 40}})
GEMINI_OK = (200, {"candidates": [{}], "usageMetadata": {"totalTokenCount": 9}})
KEYS = {"GROQ_API_KEY": "g", "GEMINI_API_KEY": "m"}


@pytest.fixture
def calls(monkeypatch):
    sent = []
    answers = {}

    def fake_post(url, body, headers, timeout=60):
        sent.append((url, body))
        for fragment, queue in answers.items():
            if fragment in url:
                return queue.pop(0)
        raise AssertionError(f"unexpected request to {url}")

    monkeypatch.setattr(key_check, "post_json", fake_post)
    return sent, answers


def test_both_keys_working(calls, capsys):
    sent, answers = calls
    answers["groq"] = [GROQ_OK]
    answers["gemini-2.5-flash-lite"] = [GEMINI_OK]
    assert key_check.main(KEYS) == 0
    out = capsys.readouterr().out
    assert "Groq openai/gpt-oss-20b ok" in out and "total=40" in out
    assert "Gemini gemini-2.5-flash-lite ok" in out and "total=9" in out
    assert len(sent) == 2


def test_requests_are_small(calls):
    sent, answers = calls
    answers["groq"] = [GROQ_OK]
    answers["gemini-2.5-flash-lite"] = [GEMINI_OK]
    key_check.main(KEYS)
    groq_body, gemini_body = sent[0][1], sent[1][1]
    assert groq_body["max_completion_tokens"] <= 64
    assert groq_body["reasoning_effort"] == "low"
    assert gemini_body["generationConfig"]["maxOutputTokens"] <= 64


def test_retired_groq_models_are_not_used():
    assert not key_check.GROQ_MODEL.startswith("llama-3")


def test_gemini_falls_back_when_the_model_is_refused(calls, capsys):
    _, answers = calls
    answers["groq"] = [GROQ_OK]
    answers["gemini-2.5-flash-lite"] = [(404, {"error": {"message": "not found"}})]
    answers["gemini-3.5-flash-lite"] = [GEMINI_OK]
    assert key_check.main(KEYS) == 0
    assert "Gemini gemini-3.5-flash-lite ok after gemini-2.5-flash-lite" in capsys.readouterr().out


def test_bad_key_fails_the_run(calls, capsys):
    _, answers = calls
    answers["groq"] = [(401, {"error": {"message": "Invalid API Key"}})]
    answers["gemini-2.5-flash-lite"] = [GEMINI_OK]
    assert key_check.main(KEYS) == 1
    assert "::error::Groq openai/gpt-oss-20b the key was rejected (401)" in capsys.readouterr().out


def test_rate_limit_is_reported_without_trying_another_model(calls, capsys):
    sent, answers = calls
    answers["groq"] = [GROQ_OK]
    answers["gemini-2.5-flash-lite"] = [(429, {"error": {"message": "quota"}})]
    assert key_check.main(KEYS) == 1
    assert "rate limited (429)" in capsys.readouterr().out
    assert len(sent) == 2


def test_missing_secret_is_named(calls, capsys):
    _, answers = calls
    answers["groq"] = [GROQ_OK]
    assert key_check.main({"GROQ_API_KEY": "g"}) == 1
    assert "The GEMINI_API_KEY repository secret is missing" in capsys.readouterr().out

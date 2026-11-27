"""Checks that a mock interview stays inside its share of the Groq free tier."""

import ast
import sys
from types import SimpleNamespace

import pytest

from conftest import ROOT

AGENT_DIR = ROOT / "interview_agent"
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

import groq_budget as gb  # noqa: E402


def test_default_share_fits_two_interviews_a_day_under_the_published_limits():
    caps = gb.InterviewBudget.from_env({}).caps
    per_day = gb.DEFAULT_INTERVIEWS_PER_DAY
    tts = gb.PUBLISHED_LIMITS[gb.TTS_MODEL]
    llm = gb.PUBLISHED_LIMITS[gb.LLM_MODEL]
    stt = gb.PUBLISHED_LIMITS[gb.STT_MODEL]
    assert caps.tts_requests * per_day <= tts["rpd"] * gb.SAFETY_SHARE
    # Characters are turned into tokens at a pessimistic three per token.
    assert caps.tts_characters / gb.TTS_CHARS_PER_TOKEN * per_day <= tts["tpd"] * gb.SAFETY_SHARE
    assert caps.llm_tokens * per_day <= llm["tpd"] * gb.SAFETY_SHARE
    assert caps.llm_requests * per_day <= llm["rpd"] * gb.SAFETY_SHARE
    assert caps.stt_audio_seconds <= stt["audio_seconds_per_hour"]
    assert caps.stt_audio_seconds * per_day <= stt["audio_seconds_per_day"]
    assert caps.tts_requests_per_minute < tts["rpm"]


def test_more_interviews_a_day_means_a_smaller_share():
    two = gb.InterviewBudget.from_env({"CAREERPILOT_INTERVIEWS_PER_DAY": "2"}).caps
    four = gb.InterviewBudget.from_env({"CAREERPILOT_INTERVIEWS_PER_DAY": "4"}).caps
    assert four.tts_requests == two.tts_requests // 2
    assert four.llm_tokens == two.llm_tokens // 2


@pytest.mark.parametrize("value", ["0", "-1", "two", "1.5"])
def test_bad_interviews_per_day_is_refused(value):
    with pytest.raises(ValueError):
        gb.interviews_per_day({"CAREERPILOT_INTERVIEWS_PER_DAY": value})


def _llm(prompt, completion):
    return SimpleNamespace(type="llm_metrics", prompt_tokens=prompt, completion_tokens=completion)


def _stt(seconds):
    return SimpleNamespace(type="stt_metrics", audio_duration=seconds)


def _tts(characters):
    return SimpleNamespace(type="tts_metrics", characters_count=characters)


def test_usage_is_counted_per_model_and_reported():
    budget = gb.InterviewBudget.from_env({})
    budget.record(_llm(900, 80))
    budget.record(_stt(4.5))
    budget.record(_tts(150))
    budget.record(SimpleNamespace(type="vad_metrics"))
    usage = budget.usage
    assert (usage.llm_requests, usage.llm_prompt_tokens, usage.llm_completion_tokens) == (1, 900, 80)
    assert (usage.stt_requests, usage.stt_audio_seconds) == (1, 4.5)
    assert (usage.tts_requests, usage.tts_characters) == (1, 150)
    summary = budget.summary()
    assert "openai/gpt-oss-20b 1/400 requests, 900 prompt and 80 completion tokens" in summary
    assert "canopylabs/orpheus-v1-english 1/40 requests, 150/4320 characters" in summary


def test_interview_closes_before_the_speech_budget_runs_out():
    budget = gb.InterviewBudget.from_env({})
    for _ in range(29):
        budget.record(_tts(100))
    assert budget.wrap_up_reason() is None
    budget.record(_tts(100))
    assert budget.wrap_up_reason() == "tts requests"
    assert budget.exhausted_reason() is None
    for _ in range(10):
        budget.record(_tts(10))
    assert budget.exhausted_reason() == "tts requests"


def test_rate_window_waits_for_the_oldest_call_to_leave_the_minute():
    now = [0.0]
    window = gb.RateWindow(limit=2, period=60, clock=lambda: now[0])
    assert window.delay() == 0
    window.mark()
    now[0] = 10
    window.mark()
    now[0] = 15
    assert window.delay() == 45
    now[0] = 60
    assert window.delay() == 0


def test_split_packs_sentences_into_few_chunks_under_the_limit():
    reply = "Thanks for that. " * 30
    chunks = gb.split_for_tts(reply)
    assert all(len(chunk) <= gb.TTS_CHAR_LIMIT for chunk in chunks)
    assert " ".join(chunks) == reply.strip()
    assert len(chunks) == 3


def test_split_breaks_long_sentences_and_words():
    long_sentence = "word " * 70
    huge_word = "x" * 450
    chunks = gb.split_for_tts(f"Hi. {long_sentence}{huge_word}")
    assert all(0 < len(chunk) <= gb.TTS_CHAR_LIMIT for chunk in chunks)
    assert "".join(chunks).replace(" ", "") == f"Hi.{long_sentence}{huge_word}".replace(" ", "")


def test_split_of_nothing_sends_nothing():
    assert gb.split_for_tts("   ") == []


def test_interviewer_uses_only_the_budgeted_groq_models():
    source = (AGENT_DIR / "interviewer.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "livekit.plugins"
        for alias in node.names
    }
    assert imported == {"groq", "silero"}
    for retired in ("openai/gpt-4.1-mini", "cartesia/", "assemblyai/"):
        assert retired not in source
    assert "max_completion_tokens=LLM_MAX_COMPLETION_TOKENS" in source
    assert 'on("metrics_collected")' in source and "budget.summary()" in source


def test_interviewer_models_build_with_the_groq_plugin(monkeypatch):
    pytest.importorskip("livekit.plugins.groq")
    pytest.importorskip("livekit.plugins.silero")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    sys.modules.pop("interviewer", None)
    import interviewer

    models = interviewer.build_models()
    assert models["llm"].model == gb.LLM_MODEL
    assert models["stt"].model == gb.STT_MODEL
    assert type(models["tts"]).__name__ == "StreamAdapter"

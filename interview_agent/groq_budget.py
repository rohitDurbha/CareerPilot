"""Keep each mock interview inside a fixed share of the Groq free tier.

The interviewer listens with Groq Whisper, thinks with GPT-OSS 20B and speaks
with Orpheus, all on one GROQ_API_KEY. Groq only publishes the Developer plan
base limits (https://console.groq.com/docs/rate-limits), and the free tier is
never higher, so those numbers are used as an upper bound here. Each interview
gets an equal share of the daily allowance, after a safety margin, so a day of
CAREERPILOT_INTERVIEWS_PER_DAY interviews stays under it.

Orpheus is the tightest limit by far (100 requests and 3,600 tokens a day, and
at most 200 characters per request), so speech is merged into as few chunks of
up to 200 characters as possible and paced under its per minute limit.

This module has no LiveKit imports, so it can be tested on its own.
"""

from __future__ import annotations

import math
import re
import time
from collections import deque
from dataclasses import dataclass, field

STT_MODEL = "whisper-large-v3-turbo"
LLM_MODEL = "openai/gpt-oss-20b"
TTS_MODEL = "canopylabs/orpheus-v1-english"
TTS_VOICE = "autumn"

# Developer plan base limits from https://console.groq.com/docs/rate-limits,
# read on November 27, 2026. The free tier is at most this.
PUBLISHED_LIMITS = {
    LLM_MODEL: {"rpm": 30, "rpd": 1_000, "tpm": 8_000, "tpd": 200_000},
    STT_MODEL: {"rpm": 20, "rpd": 2_000, "audio_seconds_per_hour": 7_200, "audio_seconds_per_day": 28_800},
    TTS_MODEL: {"rpm": 10, "rpd": 100, "tpm": 1_200, "tpd": 3_600},
}

# Orpheus refuses longer input (https://console.groq.com/docs/text-to-speech/orpheus).
TTS_CHAR_LIMIT = 200
# Orpheus counts tokens, and English text runs about four characters a token.
# Three keeps the character budget on the safe side.
TTS_CHARS_PER_TOKEN = 3

# Use only this much of each published limit, to leave room for the daily key
# check and for limits that are lower on the free tier.
SAFETY_SHARE = 0.8
# Start the closing line once any budget is this full.
WRAP_UP_AT = 0.75
# A completion cap that fits one or two spoken sentences plus low effort reasoning.
LLM_MAX_COMPLETION_TOKENS = 300

DEFAULT_INTERVIEWS_PER_DAY = 2


def interviews_per_day(env) -> int:
    raw = str(env.get("CAREERPILOT_INTERVIEWS_PER_DAY", "") or "").strip()
    if not raw:
        return DEFAULT_INTERVIEWS_PER_DAY
    if not raw.isdigit() or int(raw) < 1:
        raise ValueError("CAREERPILOT_INTERVIEWS_PER_DAY must be a whole number of at least 1")
    return int(raw)


@dataclass(frozen=True)
class Caps:
    llm_requests: int
    llm_tokens: int
    stt_requests: int
    stt_audio_seconds: float
    tts_requests: int
    tts_characters: int
    tts_requests_per_minute: int

    @classmethod
    def for_share(cls, per_day: int) -> "Caps":
        def share(value):
            return math.floor(value * SAFETY_SHARE / per_day)

        llm = PUBLISHED_LIMITS[LLM_MODEL]
        stt = PUBLISHED_LIMITS[STT_MODEL]
        tts = PUBLISHED_LIMITS[TTS_MODEL]
        return cls(
            llm_requests=share(llm["rpd"]),
            llm_tokens=share(llm["tpd"]),
            stt_requests=share(stt["rpd"]),
            stt_audio_seconds=min(share(stt["audio_seconds_per_day"]), stt["audio_seconds_per_hour"] * SAFETY_SHARE),
            tts_requests=share(tts["rpd"]),
            tts_characters=share(tts["tpd"]) * TTS_CHARS_PER_TOKEN,
            tts_requests_per_minute=max(1, math.floor(tts["rpm"] * SAFETY_SHARE)),
        )


@dataclass
class Usage:
    llm_requests: int = 0
    llm_prompt_tokens: int = 0
    llm_completion_tokens: int = 0
    stt_requests: int = 0
    stt_audio_seconds: float = 0.0
    tts_requests: int = 0
    tts_characters: int = 0


@dataclass
class InterviewBudget:
    caps: Caps
    usage: Usage = field(default_factory=Usage)

    @classmethod
    def from_env(cls, env) -> "InterviewBudget":
        return cls(Caps.for_share(interviews_per_day(env)))

    def record(self, metrics) -> None:
        """Add one LiveKit metrics event (LLM, STT or TTS) to the usage."""
        kind = getattr(metrics, "type", "")
        if kind == "llm_metrics":
            self.usage.llm_requests += 1
            self.usage.llm_prompt_tokens += int(getattr(metrics, "prompt_tokens", 0) or 0)
            self.usage.llm_completion_tokens += int(getattr(metrics, "completion_tokens", 0) or 0)
        elif kind == "stt_metrics":
            self.usage.stt_requests += 1
            self.usage.stt_audio_seconds += float(getattr(metrics, "audio_duration", 0) or 0)
        elif kind == "tts_metrics":
            self.usage.tts_requests += 1
            self.usage.tts_characters += int(getattr(metrics, "characters_count", 0) or 0)

    def fractions(self) -> dict[str, float]:
        u, c = self.usage, self.caps
        return {
            "llm requests": u.llm_requests / c.llm_requests,
            "llm tokens": (u.llm_prompt_tokens + u.llm_completion_tokens) / c.llm_tokens,
            "stt requests": u.stt_requests / c.stt_requests,
            "stt audio": u.stt_audio_seconds / c.stt_audio_seconds,
            "tts requests": u.tts_requests / c.tts_requests,
            "tts characters": u.tts_characters / c.tts_characters,
        }

    def _first_over(self, level: float) -> str | None:
        for name, used in self.fractions().items():
            if used >= level:
                return name
        return None

    def wrap_up_reason(self) -> str | None:
        """Name the budget that is nearly used up, so the interview can close."""
        return self._first_over(WRAP_UP_AT)

    def exhausted_reason(self) -> str | None:
        return self._first_over(1.0)

    def summary(self) -> str:
        u, c = self.usage, self.caps
        return (
            f"Groq usage this interview: "
            f"{LLM_MODEL} {u.llm_requests}/{c.llm_requests} requests, "
            f"{u.llm_prompt_tokens} prompt and {u.llm_completion_tokens} completion tokens "
            f"of {c.llm_tokens}; "
            f"{STT_MODEL} {u.stt_requests}/{c.stt_requests} requests, "
            f"{u.stt_audio_seconds:.0f}/{c.stt_audio_seconds:.0f} audio seconds; "
            f"{TTS_MODEL} {u.tts_requests}/{c.tts_requests} requests, "
            f"{u.tts_characters}/{c.tts_characters} characters"
        )


class RateWindow:
    """Say how long to wait so no more than `limit` calls start in any minute."""

    def __init__(self, limit: int, period: float = 60.0, clock=time.monotonic):
        self.limit = limit
        self.period = period
        self.clock = clock
        self.starts: deque[float] = deque()

    def delay(self) -> float:
        now = self.clock()
        while self.starts and now - self.starts[0] >= self.period:
            self.starts.popleft()
        if len(self.starts) < self.limit:
            return 0.0
        return self.period - (now - self.starts[0])

    def mark(self) -> None:
        self.starts.append(self.clock())


_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def split_for_tts(text: str, limit: int = TTS_CHAR_LIMIT) -> list[str]:
    """Split a reply into as few chunks of at most `limit` characters as possible.

    Whole sentences are packed together while they fit. A sentence longer than
    the limit is broken between words, and a single word longer than the limit
    is cut, so no chunk is ever refused by Orpheus.
    """
    words_text = " ".join(str(text or "").split())
    if not words_text:
        return []
    pieces = []
    for sentence in _SENTENCE_END.split(words_text):
        if len(sentence) <= limit:
            pieces.append(sentence)
            continue
        line = ""
        for word in sentence.split(" "):
            while len(word) > limit:
                if line:
                    pieces.append(line)
                    line = ""
                pieces.append(word[:limit])
                word = word[limit:]
            candidate = f"{line} {word}" if line else word
            if len(candidate) <= limit:
                line = candidate
            else:
                pieces.append(line)
                line = word
        if line:
            pieces.append(line)

    chunks = []
    for piece in pieces:
        if chunks and len(chunks[-1]) + 1 + len(piece) <= limit:
            chunks[-1] = f"{chunks[-1]} {piece}"
        else:
            chunks.append(piece)
    return chunks

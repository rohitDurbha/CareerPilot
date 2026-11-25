"""Send one tiny prompt to each LLM provider so a dead key shows up as a failed run.

Reads GROQ_API_KEY and GEMINI_API_KEY from the environment. Each provider gets
one short request with a capped answer, so a daily run uses a negligible share
of the free tier. The script prints the model used and the tokens each
provider counted, and exits with status 1 when any key fails.

Free tier limits checked on November 25, 2026
  Groq openai/gpt-oss-20b   30 requests and 8K tokens a minute,
                            1K requests and 200K tokens a day
                            (console.groq.com/docs/rate-limits)
  Gemini                    published only in the Google AI Studio dashboard,
                            so this check stays at one request a day

The Llama 3.1 and 3.3 models on Groq were shut down on August 16, 2026, which
is why the check uses gpt-oss-20b. Gemini 2.5 Flash-Lite is still served but
only to keys that used it before, so the check falls back to the stable
Gemini 3.5 Flash-Lite when the older model is refused.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

PROMPT = "Reply with the single word ok."

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.environ.get("GROQ_MODEL", "").strip() or "openai/gpt-oss-20b"

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GEMINI_MODELS = [
    m.strip()
    for m in (os.environ.get("GEMINI_MODELS", "") or "gemini-2.5-flash-lite,gemini-3.5-flash-lite").split(",")
    if m.strip()
]

# Statuses that mean this model is not offered to the key, so the next model
# is worth trying. Anything else is reported as it is.
MODEL_REFUSED = {403, 404}


class CheckFailed(Exception):
    pass


def post_json(url, body, headers, timeout=60):
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        text = error.read().decode("utf-8", "replace")
        try:
            return error.code, json.loads(text)
        except ValueError:
            return error.code, {"error": text[:300]}
    except OSError as error:
        return 0, {"error": str(error)}


def explain(status, body):
    if status == 401:
        return "the key was rejected (401), so it is wrong or revoked"
    if status == 429:
        return "rate limited (429), so the free tier allowance is used up for now"
    detail = body.get("error") if isinstance(body, dict) else body
    if isinstance(detail, dict):
        detail = detail.get("message") or detail
    return f"answered {status}: {str(detail)[:300]}"


def check_groq(key):
    status, body = post_json(
        GROQ_URL,
        {
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": PROMPT}],
            "max_completion_tokens": 64,
            "reasoning_effort": "low",
        },
        {"Authorization": f"Bearer {key}"},
    )
    if status != 200 or not body.get("choices"):
        raise CheckFailed(f"Groq {GROQ_MODEL} {explain(status, body)}")
    usage = body.get("usage") or {}
    return (
        f"Groq {GROQ_MODEL} ok, tokens prompt={usage.get('prompt_tokens')} "
        f"completion={usage.get('completion_tokens')} total={usage.get('total_tokens')}"
    )


def check_gemini(key):
    refused = []
    for model in GEMINI_MODELS:
        status, body = post_json(
            GEMINI_URL.format(model=model),
            {
                "contents": [{"parts": [{"text": PROMPT}]}],
                "generationConfig": {"maxOutputTokens": 64},
            },
            {"x-goog-api-key": key},
        )
        if status == 200 and body.get("candidates"):
            usage = body.get("usageMetadata") or {}
            note = f" after {', '.join(refused)} was refused" if refused else ""
            return (
                f"Gemini {model} ok{note}, tokens prompt={usage.get('promptTokenCount')} "
                f"output={usage.get('candidatesTokenCount')} total={usage.get('totalTokenCount')}"
            )
        if status in MODEL_REFUSED:
            print(f"Gemini {model} {explain(status, body)}, trying the next model")
            refused.append(model)
            continue
        raise CheckFailed(f"Gemini {model} {explain(status, body)}")
    raise CheckFailed(f"Gemini refused every model it was offered: {', '.join(refused)}")


CHECKS = (("GROQ_API_KEY", check_groq), ("GEMINI_API_KEY", check_gemini))


def main(env=os.environ):
    failures = []
    for name, check in CHECKS:
        key = env.get(name, "").strip()
        if not key:
            failures.append(f"The {name} repository secret is missing")
            continue
        try:
            print(check(key))
        except CheckFailed as error:
            failures.append(str(error))
    for failure in failures:
        print(f"::error::{failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

"""Guards against the LiveKit key or secret reaching the browser bundle again."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEET = ROOT / "meet"
SOURCE_DIRS = ["app", "lib"]
PUBLIC_SECRET_NAMES = ["NEXT_PUBLIC_LIVEKIT_API_KEY", "NEXT_PUBLIC_LIVEKIT_API_SECRET"]


def _source_files():
    for folder in SOURCE_DIRS:
        for path in (MEET / folder).rglob("*"):
            if path.suffix in {".ts", ".tsx", ".js", ".jsx"} and ".test." not in path.name:
                yield path


def test_interview_room_never_reads_public_livekit_secrets():
    offenders = []
    for path in _source_files():
        text = path.read_text(encoding="utf-8")
        for name in PUBLIC_SECRET_NAMES:
            if name in text:
                offenders.append(f"{path.relative_to(ROOT)} uses {name}")
    assert offenders == []


def test_meet_env_example_lists_server_only_livekit_settings():
    example = (MEET / ".env.example").read_text(encoding="utf-8")
    for name in ["LIVEKIT_URL=", "LIVEKIT_API_KEY=", "LIVEKIT_API_SECRET="]:
        assert name in example
    for name in PUBLIC_SECRET_NAMES:
        assert name not in example

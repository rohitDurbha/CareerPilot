"""Settings for the CareerPilot Flask backend, read from environment variables.

Values can come from the real environment or from a ``Project/.env`` file.
Copy ``Project/.env.example`` to ``Project/.env`` and fill it in for local work.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ENV_FILE = Path(__file__).resolve().parent / ".env"

DEFAULT_MONGO_URI = "mongodb://localhost:27017"
DEFAULT_MONGO_DB = "scrapped_jobs"
DEFAULT_MONGO_COLLECTION = "Careerpilot"
DEFAULT_PORT = 5001

# Origins allowed to call the backend when CAREERPILOT_ALLOWED_ORIGINS is not
# set. Only pages served from this machine, or opened straight from disk (the
# browser sends the origin "null" for those), may call it.
LOCAL_ORIGINS = (
    r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    "null",
)


class MissingSettingError(RuntimeError):
    """Raised when a feature needs a setting that has not been provided."""


TRUE_WORDS = {"1", "true", "yes", "on"}


def _read(name, default=""):
    value = os.environ.get(name, "").strip()
    return value or default


def _read_flag(name):
    return _read(name).lower() in TRUE_WORDS


@dataclass(frozen=True)
class Settings:
    mongo_uri: str
    mongo_db: str
    mongo_collection: str
    job_search_webhook: str
    resume_match_webhook: str
    mock_mode: bool = False
    allowed_origins: tuple = LOCAL_ORIGINS
    port: int = DEFAULT_PORT

    def require(self, field, env_name):
        """Return a setting or raise a clear error naming the variable to set."""
        value = getattr(self, field)
        if not value:
            raise MissingSettingError(
                f"{env_name} is not set. Add it to Project/.env or the environment."
            )
        return value


def _read_origins(name):
    """Split a comma separated origin list, dropping blanks and trailing slashes."""
    origins = tuple(
        part.strip().rstrip("/") for part in _read(name).split(",") if part.strip()
    )
    return origins or LOCAL_ORIGINS


def _read_port(name):
    value = _read(name)
    if not value:
        return DEFAULT_PORT
    try:
        port = int(value)
    except ValueError:
        raise MissingSettingError(f"{name} must be a port number, not {value!r}.")
    if not 0 < port < 65536:
        raise MissingSettingError(f"{name} must be between 1 and 65535, not {port}.")
    return port


def load_settings(env_file=None):
    """Load settings, letting real environment variables win over the .env file."""
    env_file = ENV_FILE if env_file is None else env_file
    if Path(env_file).is_file():
        load_dotenv(env_file, override=False)
    return Settings(
        mongo_uri=_read("MONGO_URI", DEFAULT_MONGO_URI),
        mongo_db=_read("MONGO_DB", DEFAULT_MONGO_DB),
        mongo_collection=_read("MONGO_COLLECTION", DEFAULT_MONGO_COLLECTION),
        job_search_webhook=_read("ACTIVEPIECES_JOB_SEARCH_WEBHOOK"),
        resume_match_webhook=_read("ACTIVEPIECES_RESUME_MATCH_WEBHOOK"),
        mock_mode=_read_flag("CAREERPILOT_MOCK"),
        allowed_origins=_read_origins("CAREERPILOT_ALLOWED_ORIGINS"),
        port=_read_port("PORT"),
    )

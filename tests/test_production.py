"""Checks that the backend is ready to host: gunicorn on PORT and locked CORS."""

import importlib
import runpy
import subprocess
import sys
import time
import urllib.request

import pytest

from conftest import PROJECT

import config

ORIGIN_NAMES = ("CAREERPILOT_ALLOWED_ORIGINS", "PORT", "CAREERPILOT_MOCK")


@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "ENV_FILE", tmp_path / "missing.env")
    for name in ORIGIN_NAMES:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def _client():
    sys.modules.pop("backend", None)
    backend = importlib.import_module("backend")
    backend.app.config["TESTING"] = True
    return backend.app.test_client()


def _allowed_origin(client, origin):
    response = client.get("/", headers={"Origin": origin})
    return response.headers.get("Access-Control-Allow-Origin")


def test_port_defaults_to_5001(clean_env, tmp_path):
    assert config.load_settings(env_file=tmp_path / "missing.env").port == 5001


def test_port_comes_from_the_environment(clean_env, tmp_path):
    clean_env.setenv("PORT", "7860")
    assert config.load_settings(env_file=tmp_path / "missing.env").port == 7860


@pytest.mark.parametrize("value", ["web", "0", "70000"])
def test_bad_port_names_the_variable(clean_env, tmp_path, value):
    clean_env.setenv("PORT", value)
    with pytest.raises(config.MissingSettingError, match="PORT"):
        config.load_settings(env_file=tmp_path / "missing.env")


def test_origins_are_split_and_trimmed(clean_env, tmp_path):
    clean_env.setenv(
        "CAREERPILOT_ALLOWED_ORIGINS",
        " https://careerpilot.vercel.app/ , ,https://preview.example.com",
    )
    settings = config.load_settings(env_file=tmp_path / "missing.env")
    assert settings.allowed_origins == (
        "https://careerpilot.vercel.app",
        "https://preview.example.com",
    )


def test_local_pages_are_allowed_by_default(clean_env):
    client = _client()
    for origin in ("http://localhost:3000", "http://127.0.0.1:5500", "null"):
        assert _allowed_origin(client, origin) == origin


def test_other_sites_are_refused_by_default(clean_env):
    client = _client()
    assert _allowed_origin(client, "https://evil.example.com") is None
    assert _allowed_origin(client, "http://localhost.evil.example.com") is None


def test_configured_origin_is_the_only_one_allowed(clean_env):
    clean_env.setenv("CAREERPILOT_ALLOWED_ORIGINS", "https://careerpilot.vercel.app")
    client = _client()
    assert _allowed_origin(client, "https://careerpilot.vercel.app") == (
        "https://careerpilot.vercel.app"
    )
    assert _allowed_origin(client, "http://localhost:3000") is None
    assert _allowed_origin(client, "https://evil.example.com") is None


def test_preflight_for_configured_origin(clean_env):
    clean_env.setenv("CAREERPILOT_ALLOWED_ORIGINS", "https://careerpilot.vercel.app")
    client = _client()
    response = client.options(
        "/trigger",
        headers={
            "Origin": "https://careerpilot.vercel.app",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.headers["Access-Control-Allow-Origin"] == (
        "https://careerpilot.vercel.app"
    )
    assert "POST" in response.headers["Access-Control-Allow-Methods"]


def _gunicorn_conf(monkeypatch, port=None):
    if port is None:
        monkeypatch.delenv("PORT", raising=False)
    else:
        monkeypatch.setenv("PORT", port)
    return runpy.run_path(str(PROJECT / "gunicorn.conf.py"))


def test_gunicorn_binds_to_port(monkeypatch):
    assert _gunicorn_conf(monkeypatch, "7860")["bind"] == "0.0.0.0:7860"
    assert _gunicorn_conf(monkeypatch)["bind"] == "0.0.0.0:5001"


def test_gunicorn_keeps_one_worker(monkeypatch):
    assert _gunicorn_conf(monkeypatch)["workers"] == 1


def test_gunicorn_is_a_requirement():
    text = (PROJECT / "requirements.txt").read_text(encoding="utf-8")
    assert "gunicorn" in text


@pytest.mark.skipif(
    sys.platform.startswith("win"), reason="gunicorn does not run on Windows"
)
def test_gunicorn_serves_the_app(tmp_path):
    pytest.importorskip("gunicorn")
    port = "5987"
    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "PORT": port,
        "CAREERPILOT_MOCK": "1",
        "CAREERPILOT_ALLOWED_ORIGINS": "https://careerpilot.vercel.app",
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "gunicorn", "backend:app"],
        cwd=PROJECT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        body = None
        for _ in range(50):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1) as r:
                    body = r.read().decode()
                    break
            except OSError:
                time.sleep(0.2)
        assert body is not None, "gunicorn never answered"
    finally:
        proc.terminate()
        proc.wait(timeout=10)

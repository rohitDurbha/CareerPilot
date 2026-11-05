"""Checks that the interview agents the backend launches are present and valid."""

import ast
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENT_DIR = ROOT / "interview_agent"
BACKEND = ROOT / "Project" / "backend.py"


def test_agent_scripts_exist_and_compile():
    for name in ("interviewer.py", "transcriber.py"):
        script = AGENT_DIR / name
        assert script.is_file(), f"missing {script}"
        py_compile.compile(str(script), doraise=True)


def test_agents_define_an_entrypoint():
    for name in ("interviewer.py", "transcriber.py"):
        tree = ast.parse((AGENT_DIR / name).read_text(encoding="utf-8"))
        names = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        assert "entrypoint" in names, f"{name} has no entrypoint"


def test_backend_uses_repository_relative_agent_paths():
    source = BACKEND.read_text(encoding="utf-8")
    assert "/Users/" not in source
    assert "python-agents-examples" not in source
    assert '"interview_agent"' in source

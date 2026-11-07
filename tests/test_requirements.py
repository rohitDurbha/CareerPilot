"""Checks that Project/requirements.txt matches what the Flask code imports."""

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT / "Project"

# Import names that differ from the name used on PyPI.
IMPORT_TO_PACKAGE = {
    "bs4": "beautifulsoup4",
    "flask_cors": "flask-cors",
    "dotenv": "python-dotenv",
}

HEAVY_PACKAGES = {"torch", "transformers", "sentence-transformers", "llama-index"}


def _requirements():
    names = set()
    for line in (PROJECT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            names.add(re.split(r"[<>=~!\[ ]", line, maxsplit=1)[0].lower())
    return names


def _third_party_imports():
    found = set()
    for script in PROJECT.glob("*.py"):
        tree = ast.parse(script.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                found.add(node.module.split(".")[0])
    local = {script.stem for script in PROJECT.glob("*.py")}
    return {name for name in found if name not in sys.stdlib_module_names | local}


def test_every_import_is_listed():
    listed = _requirements()
    missing = {
        IMPORT_TO_PACKAGE.get(name, name).lower()
        for name in _third_party_imports()
    } - listed
    assert not missing, f"add these to Project/requirements.txt: {sorted(missing)}"


def test_heavy_ml_packages_are_not_required():
    assert not (_requirements() & HEAVY_PACKAGES)


def test_saved_linkedin_page_is_gone():
    assert not (PROJECT / "test.html").exists()

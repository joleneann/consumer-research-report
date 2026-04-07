"""Smoke tests for script entrypoints.

These tests verify that every script in scripts/ and examples/ can be
imported without crashing. This catches the class of bugs where RUNS_DIR
or other symbols are used before being imported, or where removed config
fields cause TypeError at import time.

These are NOT functional tests - they do not run the scripts' logic.
They only verify that the import-time code path succeeds.
"""
import importlib
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
EXAMPLES_DIR = REPO_ROOT / "examples" / "studies" / "weight_loss"


def _check_script_syntax(script_path: Path):
    """Run Python's compile check on a script file."""
    source = script_path.read_text(encoding="utf-8")
    compile(source, str(script_path), "exec")


def _check_script_runs(script_path: Path):
    """Run the script in a subprocess and verify it doesn't crash on import.

    Scripts that need CLI args or missing data will exit with a clean error
    message. We just verify they don't crash with NameError/ImportError/TypeError.
    """
    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        timeout=15,
        cwd=str(REPO_ROOT),
    )
    stderr = result.stderr
    # These are fatal import/wiring bugs - the script is broken
    for error_type in ["NameError", "ImportError", "TypeError", "AttributeError"]:
        if error_type in stderr:
            pytest.fail(
                f"{script_path.name} crashed with {error_type}:\n{stderr[-500:]}"
            )


class TestScriptSyntax:
    """Verify all scripts have valid Python syntax."""

    @pytest.mark.parametrize("script", sorted(SCRIPTS_DIR.glob("*.py")))
    def test_script_compiles(self, script):
        _check_script_syntax(script)

    @pytest.mark.parametrize("script", sorted(EXAMPLES_DIR.glob("*.py")))
    def test_example_compiles(self, script):
        _check_script_syntax(script)


class TestScriptEntrypoints:
    """Verify scripts don't crash at import time.

    Each script is run in a subprocess with no arguments. We expect them
    to exit with a usage error or missing-data error, NOT with NameError
    or ImportError.
    """

    @pytest.mark.parametrize("script_name", [
        "stage6_7_score_report.py",
        "regenerate_report.py",
        "rescore.py",
        "export_to_excel.py",
        "fix_quotes.py",
        "add_narrative_themes.py",
    ])
    def test_script_entrypoint(self, script_name):
        script = SCRIPTS_DIR / script_name
        if script.exists():
            _check_script_runs(script)

    @pytest.mark.parametrize("script_name", [
        "resume_stage3.py",
        "resume_stage4.py",
    ])
    def test_resume_script_entrypoint(self, script_name):
        """Resume scripts require a run_id arg. Pass a dummy to verify import wiring."""
        script = SCRIPTS_DIR / script_name
        if not script.exists():
            pytest.skip(f"{script_name} not found")
        result = subprocess.run(
            [sys.executable, str(script), "nonexistent_run_id"],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(REPO_ROOT),
            env={**__import__("os").environ, "ANTHROPIC_API_KEY": "sk-ant-test-dummy"},
        )
        stderr = result.stderr
        for error_type in ["NameError", "ImportError", "TypeError", "AttributeError"]:
            if error_type in stderr:
                pytest.fail(
                    f"{script_name} crashed with {error_type}:\n{stderr[-500:]}"
                )


class TestCLIEntrypoint:
    """Verify the CLI doesn't crash and shows correct subcommands."""

    def test_help_works(self):
        result = subprocess.run(
            [sys.executable, "-m", "consumer_research.run", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "ingest" in result.stdout
        assert "run" in result.stdout
        assert "score-report" in result.stdout
        assert "regenerate" in result.stdout

    def test_no_resume_subcommand(self):
        result = subprocess.run(
            [sys.executable, "-m", "consumer_research.run", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert "resume" not in result.stdout

    def test_run_subcommand_no_dead_flags(self):
        result = subprocess.run(
            [sys.executable, "-m", "consumer_research.run", "run", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "--interactive" not in result.stdout
        assert "--max-corpus" not in result.stdout

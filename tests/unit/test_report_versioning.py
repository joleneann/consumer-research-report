"""Unit tests for report serial versioning logic.

The DOCX generator assigns report_v001.docx, report_v002.docx, etc.
These tests verify the numeric-max logic, lock-file filtering, and
zero-padding behaviour without running the full report generator.
"""
import re
from pathlib import Path

import pytest


# ── Standalone version picker (mirrors docx_generator._next_report_version) ──

def _next_version(report_dir: Path) -> int:
    """Extract the next serial version number from existing report files.

    Mirrors the logic in report/docx_generator.py. Any changes to the
    production implementation should be reflected here.

    Rules:
    - Glob for report_v*.docx
    - Filter out lock files (~$...)
    - Parse version numbers numerically (not lexicographically)
    - Return max(existing) + 1, or 1 if none exist
    """
    existing = [
        f for f in report_dir.glob("report_v*.docx")
        if not f.name.startswith("~$")
    ]
    if not existing:
        return 1

    nums = []
    for f in existing:
        m = re.search(r"report_v(\d+)\.docx$", f.name)
        if m:
            nums.append(int(m.group(1)))

    return max(nums) + 1 if nums else 1


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestReportVersioning:
    def test_first_version_is_001(self, tmp_path):
        assert _next_version(tmp_path) == 1

    def test_increments_from_existing(self, tmp_path):
        (tmp_path / "report_v001.docx").touch()
        assert _next_version(tmp_path) == 2

    def test_numeric_max_not_alphabetical(self, tmp_path):
        """report_v2.docx and report_v10.docx — alphabetically '2' > '10', but numerically 10 > 2."""
        (tmp_path / "report_v2.docx").touch()
        (tmp_path / "report_v10.docx").touch()
        assert _next_version(tmp_path) == 11

    def test_mixed_padding_numeric_max(self, tmp_path):
        """Mix of zero-padded and non-padded filenames."""
        (tmp_path / "report_v001.docx").touch()
        (tmp_path / "report_v010.docx").touch()
        (tmp_path / "report_v5.docx").touch()
        assert _next_version(tmp_path) == 11

    def test_lock_files_ignored(self, tmp_path):
        """Windows lock files (~$report_v...) must not influence version selection."""
        (tmp_path / "report_v003.docx").touch()
        (tmp_path / "~$report_v003.docx").touch()  # Word lock file
        assert _next_version(tmp_path) == 4

    def test_unrelated_docx_ignored(self, tmp_path):
        """Only report_v*.docx files should count."""
        (tmp_path / "final_report.docx").touch()
        (tmp_path / "report_draft.docx").touch()
        assert _next_version(tmp_path) == 1

    def test_sequence_stays_monotonic(self, tmp_path):
        """Simulate 3 consecutive regenerations."""
        versions = []
        for _ in range(3):
            v = _next_version(tmp_path)
            versions.append(v)
            (tmp_path / f"report_v{v:03d}.docx").touch()

        assert versions == [1, 2, 3]

    def test_gap_in_sequence_jumps_correctly(self, tmp_path):
        """If v001 and v003 exist (v002 deleted), next should be v004."""
        (tmp_path / "report_v001.docx").touch()
        (tmp_path / "report_v003.docx").touch()
        assert _next_version(tmp_path) == 4

    def test_large_version_number(self, tmp_path):
        (tmp_path / "report_v099.docx").touch()
        assert _next_version(tmp_path) == 100

    def test_empty_directory_returns_1(self, tmp_path):
        empty_dir = tmp_path / "report"
        empty_dir.mkdir()
        assert _next_version(empty_dir) == 1

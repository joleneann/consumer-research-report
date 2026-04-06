"""Unit tests for report serial versioning logic.

Tests the actual production function from docx_generator.py, not a mirror copy.
"""
from pathlib import Path

import pytest

from consumer_research.report.docx_generator import _next_report_version


class TestReportVersioning:
    def test_first_version_is_001(self, tmp_path):
        assert _next_report_version(tmp_path) == 1

    def test_increments_from_existing(self, tmp_path):
        (tmp_path / "report_v001.docx").touch()
        assert _next_report_version(tmp_path) == 2

    def test_numeric_max_not_alphabetical(self, tmp_path):
        """report_v2.docx and report_v10.docx - alphabetically '2' > '10', but numerically 10 > 2."""
        (tmp_path / "report_v2.docx").touch()
        (tmp_path / "report_v10.docx").touch()
        assert _next_report_version(tmp_path) == 11

    def test_mixed_padding_numeric_max(self, tmp_path):
        """Mix of zero-padded and non-padded filenames."""
        (tmp_path / "report_v001.docx").touch()
        (tmp_path / "report_v010.docx").touch()
        (tmp_path / "report_v5.docx").touch()
        assert _next_report_version(tmp_path) == 11

    def test_lock_files_ignored(self, tmp_path):
        """Windows lock files (~$report_v...) must not influence version selection."""
        (tmp_path / "report_v003.docx").touch()
        (tmp_path / "~$report_v003.docx").touch()
        assert _next_report_version(tmp_path) == 4

    def test_unrelated_docx_ignored(self, tmp_path):
        """Only report_v*.docx files should count."""
        (tmp_path / "final_report.docx").touch()
        (tmp_path / "report_draft.docx").touch()
        assert _next_report_version(tmp_path) == 1

    def test_sequence_stays_monotonic(self, tmp_path):
        """Simulate 3 consecutive regenerations."""
        versions = []
        for _ in range(3):
            v = _next_report_version(tmp_path)
            versions.append(v)
            (tmp_path / f"report_v{v:03d}.docx").touch()

        assert versions == [1, 2, 3]

    def test_gap_in_sequence_jumps_correctly(self, tmp_path):
        """If v001 and v003 exist (v002 deleted), next should be v004."""
        (tmp_path / "report_v001.docx").touch()
        (tmp_path / "report_v003.docx").touch()
        assert _next_report_version(tmp_path) == 4

    def test_large_version_number(self, tmp_path):
        (tmp_path / "report_v099.docx").touch()
        assert _next_report_version(tmp_path) == 100

    def test_empty_directory_returns_1(self, tmp_path):
        empty_dir = tmp_path / "report"
        empty_dir.mkdir()
        assert _next_report_version(empty_dir) == 1

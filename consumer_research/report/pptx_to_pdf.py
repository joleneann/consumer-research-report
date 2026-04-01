"""Convert a .pptx file to PDF using PowerPoint COM automation (Windows only).

This is the reliable PDF path on Windows. WeasyPrint requires GTK/GLib
native libraries that are not pre-installed on Windows. PowerPoint is
always available when you're using the deck.

Usage (standalone):
    python -m consumer_research.report.pptx_to_pdf runs/RUN_ID/report/report.pptx

Usage (from code):
    from consumer_research.report.pptx_to_pdf import pptx_to_pdf
    pdf_path = pptx_to_pdf(pptx_path)
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def pptx_to_pdf(pptx_path: str | Path, pdf_path: str | Path | None = None) -> Path:
    """Export a PPTX to PDF via PowerPoint COM automation.

    Args:
        pptx_path: Path to the source .pptx file.
        pdf_path:  Destination .pdf path. Defaults to same directory,
                   same stem, .pdf extension.

    Returns:
        Path to the generated PDF.

    Raises:
        RuntimeError: If PowerPoint COM automation fails or is unavailable.
        OSError:      If the source file does not exist.
    """
    pptx_path = Path(pptx_path).resolve()
    if not pptx_path.exists():
        raise OSError(f"Source PPTX not found: {pptx_path}")

    if pdf_path is None:
        pdf_path = pptx_path.with_suffix(".pdf")
    pdf_path = Path(pdf_path).resolve()

    if sys.platform != "win32":
        raise RuntimeError(
            "pptx_to_pdf via COM automation is Windows-only. "
            "On Linux/Mac use LibreOffice: libreoffice --headless --convert-to pdf <file>"
        )

    try:
        import win32com.client  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "pywin32 is required for COM automation. "
            "Install with: python -m pip install pywin32"
        ) from exc

    pp_app = None
    presentation = None
    try:
        logger.info(f"Opening PowerPoint COM server...")
        pp_app = win32com.client.Dispatch("PowerPoint.Application")
        # Some PowerPoint versions reject Visible=False when launched from
        # a non-interactive session; leave visibility as default.

        logger.info(f"Opening: {pptx_path}")
        presentation = pp_app.Presentations.Open(  # type: ignore[attr-defined]
            str(pptx_path),
            ReadOnly=True,
            Untitled=False,
            WithWindow=False,
        )

        # ppSaveAsPDF = 32
        PDF_FORMAT = 32
        logger.info(f"Exporting PDF → {pdf_path}")
        presentation.SaveAs(str(pdf_path), PDF_FORMAT)  # type: ignore[attr-defined]
        logger.info(f"PDF saved: {pdf_path} ({pdf_path.stat().st_size:,} bytes)")
        return pdf_path

    except Exception as exc:
        raise RuntimeError(f"PowerPoint COM export failed: {exc}") from exc

    finally:
        try:
            if presentation is not None:
                presentation.Close()
        except Exception:
            pass
        try:
            if pp_app is not None:
                pp_app.Quit()
        except Exception:
            pass


# ── CLI entry point ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    parser = argparse.ArgumentParser(description="Convert PPTX → PDF via PowerPoint COM")
    parser.add_argument("pptx", help="Path to source .pptx file")
    parser.add_argument("--out", default=None, help="Destination .pdf path (optional)")
    args = parser.parse_args()

    out = pptx_to_pdf(args.pptx, args.out)
    print(f"PDF written: {out}")

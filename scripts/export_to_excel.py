"""Export filtered corpus to Excel — one tab per platform.

Columns per item: Date, Geo/Region, URL, Author, Content,
plus platform-specific engagement columns.
Sentiment (where classified) appended as extra columns.

Usage:
    python export_to_excel.py [RUN_ID]

If RUN_ID is omitted, uses the most recent run in runs/.
"""

from __future__ import annotations

import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent  # scripts/ -> repo root
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from consumer_research.config import RUNS_DIR

# ── Resolve run dir ──────────────────────────────────────────────────────────
runs_dir = RUNS_DIR
if len(sys.argv) > 1:
    run_id = sys.argv[1]
    run_dir = runs_dir / run_id
else:
    run_dirs = sorted(runs_dir.iterdir(), key=lambda p: p.name, reverse=True)
    run_dir = next((p for p in run_dirs if p.is_dir()), None)
    if run_dir is None:
        print("No runs found.", file=sys.stderr)
        sys.exit(1)
    run_id = run_dir.name

print(f"Exporting run: {run_id}")

# ── Load data ────────────────────────────────────────────────────────────────
corpus_path = run_dir / "filtered" / "corpus.json"
if not corpus_path.exists():
    print(f"No filtered corpus found at {corpus_path}", file=sys.stderr)
    sys.exit(1)

corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
print(f"  Corpus: {len(corpus)} items")

analysis_path = run_dir / "analysis" / "results.json"
sentiment_map: dict[str, dict] = {}
if analysis_path.exists():
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    for sr in analysis.get("sentiment_results", []):
        sentiment_map[sr["item_id"]] = sr
    print(f"  Sentiment: {len(sentiment_map)} classified items")

# ── Group by platform ────────────────────────────────────────────────────────
by_platform: dict[str, list[dict]] = {}
for item in corpus:
    p = item.get("source_platform", "unknown")
    by_platform.setdefault(p, []).append(item)

print(f"  Platforms: {list(by_platform.keys())}")

# ── Row builders ─────────────────────────────────────────────────────────────
def fmt_date(ts: str | None) -> str:
    if not ts:
        return ""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return str(ts)


def common_cols(item: dict) -> dict:
    meta = item.get("platform_metadata") or {}
    s = sentiment_map.get(item.get("item_id", ""), {})
    return {
        "Item ID":           item.get("item_id", ""),
        "Date":              fmt_date(item.get("source_timestamp")),
        "Geo / Region":      meta.get("region") or "",
        "URL":               item.get("source_url") or "",
        "Author":            item.get("source_author") or "",
        "Content":           item.get("content_text") or "",
        "Content Type":      item.get("content_type") or "",
        "Collection Query":  item.get("collection_query") or "",
        "Sentiment":         s.get("sentiment") or "",
        "Sentiment Score":   s.get("sentiment_score") or "",
        "Key Phrases":       "; ".join(s.get("key_phrases") or []),
        "Aspects Mentioned": "; ".join(s.get("aspects_mentioned") or []),
    }


def platform_specific(item: dict, platform: str) -> dict:
    meta = item.get("platform_metadata") or {}
    if platform == "reddit":
        return {
            "Subreddit":       meta.get("subreddit") or "",
            "Score (Upvotes)": meta.get("score") or 0,
            "Num Comments":    meta.get("num_comments") or 0,
            "Thread ID":       meta.get("thread_id") or "",
            "Comment Depth":   meta.get("comment_depth") or 0,
        }
    elif platform == "youtube":
        return {
            "Video ID":    meta.get("video_id") or "",
            "Video Title": meta.get("video_title") or "",
            "Like Count":  meta.get("like_count") or 0,
            "View Count":  meta.get("view_count") or 0,
        }
    elif platform == "academic":
        return {
            "DOI":            meta.get("doi") or "",
            "Journal":        meta.get("journal") or "",
            "Citation Count": meta.get("citation_count") or 0,
        }
    return {}


# ── Write Excel ──────────────────────────────────────────────────────────────
try:
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.table import Table, TableStyleInfo
except ImportError:
    print("openpyxl not installed. Run: python -m pip install openpyxl", file=sys.stderr)
    sys.exit(1)

# ── Style constants ───────────────────────────────────────────────────────────
# Use fill_type= (not patternType=) — more reliable across openpyxl versions.
# Use 6-char hex (no ARGB prefix) — openpyxl adds FF internally.
# Header: dark navy text on light steel-blue background (always visible).
HDR_FILL  = PatternFill(fill_type="solid", fgColor="DCE8F5")   # light blue
HDR_FONT  = Font(name="Calibri", bold=True, color="1E3A5F", size=10)  # navy text
HDR_ALIGN = Alignment(horizontal="left", vertical="center", wrap_text=False)

BODY_FONT = Font(name="Calibri", size=10)
ALT_FILL  = PatternFill(fill_type="solid", fgColor="F3F6FA")   # very light grey
THIN_BORD = Border(
    bottom=Side(style="thin", color="D1D5DB"),
    right=Side(style="thin", color="E5E7EB"),
)


def write_sheet(wb, title: str, rows: list[dict]) -> None:
    if not rows:
        return
    ws = wb.create_sheet(title=title)
    headers = list(rows[0].keys())
    num_cols = len(headers)
    num_rows = len(rows)

    # ── Row 1: headers ──────────────────────────────────────────────────────
    for col_idx, hdr in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=hdr)
        cell.font = HDR_FONT
        cell.fill = HDR_FILL
        cell.alignment = HDR_ALIGN
        cell.border = THIN_BORD
    ws.row_dimensions[1].height = 22

    # ── Rows 2+: data ───────────────────────────────────────────────────────
    is_content_sheet = "Content" in headers
    for row_idx, row_data in enumerate(rows, 2):
        is_alt = (row_idx % 2 == 0)
        for col_idx, hdr in enumerate(headers, 1):
            val = row_data.get(hdr, "")
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font = BODY_FONT
            cell.alignment = Alignment(
                horizontal="left",
                vertical="top",
                wrap_text=(hdr == "Content"),
            )
            if is_alt:
                cell.fill = ALT_FILL
            cell.border = THIN_BORD
        row_h = 60 if is_content_sheet else 18
        ws.row_dimensions[row_idx].height = row_h

    # ── Auto-filter (adds dropdown arrows to every header cell) ─────────────
    ws.auto_filter.ref = f"A1:{get_column_letter(num_cols)}{num_rows + 1}"

    # ── Freeze header row ───────────────────────────────────────────────────
    ws.freeze_panes = "A2"

    # ── Column widths ───────────────────────────────────────────────────────
    MAX_W = {
        "Content": 80, "URL": 55, "Video Title": 50,
        "Key Phrases": 45, "Aspects Mentioned": 45, "Collection Query": 35,
    }
    for col_idx, hdr in enumerate(headers, 1):
        col_letter = get_column_letter(col_idx)
        # measure max content length in column
        max_len = max(
            (len(str(ws.cell(row=r, column=col_idx).value or "")) for r in range(1, num_rows + 2)),
            default=10,
        )
        cap = MAX_W.get(hdr, 28)
        ws.column_dimensions[col_letter].width = min(max_len + 2, cap)

    print(f"  Sheet '{title}': {num_rows} rows × {num_cols} columns")


# ── Build workbook ────────────────────────────────────────────────────────────
wb = openpyxl.Workbook()
wb.remove(wb.active)  # remove default empty sheet

for platform, items in by_platform.items():
    rows = [{**common_cols(item), **platform_specific(item, platform)} for item in items]
    write_sheet(wb, platform.capitalize(), rows)

# ── Summary sheet ─────────────────────────────────────────────────────────────
ws_sum = wb.create_sheet(title="Summary", index=0)
ws_sum.column_dimensions["A"].width = 32
ws_sum.column_dimensions["B"].width = 24

summary_data = [
    ("Run ID",             run_id),
    ("Export Date",        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")),
    ("Total Items",        len(corpus)),
    ("Sentiment Classified", len(sentiment_map)),
    ("", ""),
    ("Platform",           "Item Count"),
] + [(p.capitalize(), len(items)) for p, items in by_platform.items()]

for r_idx, (label, value) in enumerate(summary_data, 1):
    is_header_row = label in ("Run ID", "Platform")
    a = ws_sum.cell(row=r_idx, column=1, value=label)
    b = ws_sum.cell(row=r_idx, column=2, value=value)
    for cell in (a, b):
        if is_header_row:
            cell.font = Font(name="Calibri", bold=True, size=11, color="1E3A5F")
            cell.fill = PatternFill(fill_type="solid", fgColor="DCE8F5")
        else:
            cell.font = Font(name="Calibri", size=10)
        cell.alignment = Alignment(horizontal="left", vertical="center")
        cell.border = THIN_BORD
    ws_sum.row_dimensions[r_idx].height = 18

# ── Save ──────────────────────────────────────────────────────────────────────
out_path = run_dir / "report" / f"thums_up_data_{run_id[:8]}.xlsx"
wb.save(str(out_path))
print(f"\nExcel saved: {out_path} ({out_path.stat().st_size:,} bytes)")

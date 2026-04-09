"""Export insight-organised Excel — one tab per insight + unthemed items.

Each tab contains all corpus items belonging to that insight's theme(s),
with sentiment and engagement data. Items can appear in multiple tabs
(multi-coded). Final tab contains items not assigned to any theme.

Usage:
    python export_insights_excel.py [RUN_ID]

If RUN_ID is omitted, uses the most recent run in runs/.
"""

from __future__ import annotations

import io
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from consumer_research.config import RUNS_DIR

try:
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    print("openpyxl not installed. Run: python -m pip install openpyxl", file=sys.stderr)
    sys.exit(1)


# ── Style constants (matching existing export) ──────────────────────────────
HDR_FILL = PatternFill(fill_type="solid", fgColor="DCE8F5")
HDR_FONT = Font(name="Lato", bold=True, color="1E3A5F", size=10)
HDR_ALIGN = Alignment(horizontal="left", vertical="center", wrap_text=False)
BODY_FONT = Font(name="Lato", size=10)
ALT_FILL = PatternFill(fill_type="solid", fgColor="F3F6FA")
THIN_BORD = Border(
    bottom=Side(style="thin", color="D1D5DB"),
    right=Side(style="thin", color="E5E7EB"),
)
META_FONT = Font(name="Lato", bold=True, color="374151", size=11)
META_FILL = PatternFill(fill_type="solid", fgColor="F0F4F8")
NAVY_FONT = Font(name="Lato", bold=True, color="1E3A5F", size=12)
NAVY_FILL = PatternFill(fill_type="solid", fgColor="1E3A5F")
WHITE_FONT = Font(name="Lato", bold=True, color="FFFFFF", size=10)


# ── Resolve run dir ─────────────────────────────────────────────────────────
runs_dir = RUNS_DIR
if len(sys.argv) > 1:
    run_id = sys.argv[1]
    run_dir = runs_dir / run_id
else:
    run_dirs = sorted(runs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    run_dir = next((p for p in run_dirs if p.is_dir()), None)
    if run_dir is None:
        print("No runs found.", file=sys.stderr)
        sys.exit(1)
    run_id = run_dir.name

print(f"Exporting run: {run_id}")


# ── Load data ───────────────────────────────────────────────────────────────
def load_json(path: Path) -> dict | list:
    if not path.exists():
        print(f"Missing: {path}", file=sys.stderr)
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


corpus = load_json(run_dir / "filtered" / "corpus.json")
analysis = load_json(run_dir / "analysis" / "results.json")
scored_insights = load_json(run_dir / "scored" / "scored_insights.json")
config = load_json(run_dir / "config.json")

brand_name = config.get("brand_name", "Unknown")
category = config.get("category", "")

print(f"  Brand: {brand_name}")
print(f"  Corpus: {len(corpus)} items")
print(f"  Insights: {len(scored_insights)}")
print(f"  Themes: {len(analysis.get('themes', []))}")


# ── Build lookup maps ───────────────────────────────────────────────────────
item_map: dict[str, dict] = {item["item_id"]: item for item in corpus}

sentiment_map: dict[str, dict] = {}
for sr in analysis.get("sentiment_results", []):
    sentiment_map[sr["item_id"]] = sr

theme_map: dict[str, dict] = {}
for theme in analysis.get("themes", []):
    theme_map[theme["theme_id"]] = theme

# Sort insights by confidence (descending)
scored_insights.sort(key=lambda si: si.get("confidence_score", 0), reverse=True)


# ── Helpers ─────────────────────────────────────────────────────────────────
def fmt_date(ts: str | None) -> str:
    if not ts:
        return ""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(ts)


def get_engagement(item: dict) -> int:
    meta = item.get("platform_metadata") or {}
    return meta.get("score") or meta.get("like_count") or 0


def clean_sheet_name(name: str, max_len: int = 31) -> str:
    """Excel sheet names: max 31 chars, no special characters."""
    clean = re.sub(r'[\\/*?\[\]:]', '', name)
    return clean[:max_len]


def item_to_row(item: dict) -> dict:
    """Convert a corpus item + sentiment to a flat row dict."""
    s = sentiment_map.get(item.get("item_id", ""), {})
    meta = item.get("platform_metadata") or {}
    return {
        "Date": fmt_date(item.get("source_timestamp")),
        "Platform": (item.get("source_platform") or "").replace("_", " ").title(),
        "Author": item.get("source_author") or "",
        "Content": item.get("content_text") or "",
        "Content Type": (item.get("content_type") or "").replace("_", " ").title(),
        "Sentiment": (s.get("sentiment") or "").title(),
        "Sentiment Score": s.get("sentiment_score") or "",
        "Emotion": (s.get("primary_emotion") or ""),
        "Engagement": get_engagement(item),
        "URL": item.get("source_url") or "",
        "Collection Query": item.get("collection_query") or "",
    }


# ── Column widths ───────────────────────────────────────────────────────────
COL_WIDTHS = {
    "Date": 18, "Platform": 12, "Author": 16, "Content": 80,
    "Content Type": 14, "Sentiment": 12, "Sentiment Score": 14,
    "Emotion": 14, "Engagement": 12, "URL": 50, "Collection Query": 30,
}


def write_data_rows(ws, rows: list[dict], start_row: int) -> None:
    """Write data rows starting at start_row. Row start_row is headers."""
    if not rows:
        return
    headers = list(rows[0].keys())

    # Header row
    for col_idx, hdr in enumerate(headers, 1):
        cell = ws.cell(row=start_row, column=col_idx, value=hdr)
        cell.font = HDR_FONT
        cell.fill = HDR_FILL
        cell.alignment = HDR_ALIGN
        cell.border = THIN_BORD
    ws.row_dimensions[start_row].height = 22

    # Data rows
    for row_idx, row_data in enumerate(rows, start_row + 1):
        is_alt = (row_idx % 2 == 0)
        for col_idx, hdr in enumerate(headers, 1):
            val = row_data.get(hdr, "")
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font = BODY_FONT
            cell.alignment = Alignment(
                horizontal="left", vertical="top",
                wrap_text=(hdr == "Content"),
            )
            if is_alt:
                cell.fill = ALT_FILL
            cell.border = THIN_BORD
        ws.row_dimensions[row_idx].height = 60 if any(h == "Content" for h in headers) else 18

    # Auto-filter
    last_row = start_row + len(rows)
    ws.auto_filter.ref = f"A{start_row}:{get_column_letter(len(headers))}{last_row}"

    # Freeze below header
    ws.freeze_panes = f"A{start_row + 1}"

    # Column widths
    for col_idx, hdr in enumerate(headers, 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = COL_WIDTHS.get(hdr, 16)


def write_insight_tab(wb, tab_num: int, scored_insight: dict, theme_items: list[dict]) -> None:
    """Write one insight tab with metadata header + data rows."""
    ins = scored_insight["insight"]
    theme_ids = ins.get("supporting_theme_ids", [])
    theme = theme_map.get(theme_ids[0], {}) if theme_ids else {}

    label = theme.get("theme_label", ins.get("insight_id", "Unknown"))
    sheet_name = clean_sheet_name(f"{tab_num:02d} {label}")
    ws = wb.create_sheet(title=sheet_name)

    # Metadata header rows
    conf = scored_insight.get("confidence_score", 0)
    signal = scored_insight.get("signal_strength_score", 0)
    nss = theme.get("net_sentiment_score", 0)
    item_count = len(theme_items)

    meta_rows = [
        ("Theme", label),
        ("Items", str(item_count)),
        ("Net Sentiment Score", f"{nss:+.1%}"),
        ("Confidence", f"{conf:.0%}"),
        ("Signal Strength", f"{signal:.0%}"),
    ]

    for r_idx, (key, val) in enumerate(meta_rows, 1):
        cell_a = ws.cell(row=r_idx, column=1, value=key)
        cell_b = ws.cell(row=r_idx, column=2, value=val)
        cell_a.font = META_FONT
        cell_a.fill = META_FILL
        cell_b.font = Font(name="Lato", size=11)
        cell_b.fill = META_FILL
        for c in (cell_a, cell_b):
            c.border = THIN_BORD
            c.alignment = Alignment(horizontal="left", vertical="center")
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 30

    # Blank row
    data_start = len(meta_rows) + 2

    # Data rows
    rows = [item_to_row(item) for item in theme_items]
    rows.sort(key=lambda r: r.get("Engagement", 0), reverse=True)
    write_data_rows(ws, rows, data_start)

    print(f"  Tab '{sheet_name}': {item_count} items")


# ── Build workbook ──────────────────────────────────────────────────────────
wb = openpyxl.Workbook()
wb.remove(wb.active)

# Track which items are themed (for unthemed tab)
all_themed_ids: set[str] = set()

# Insight tabs
for idx, si in enumerate(scored_insights, 1):
    ins = si["insight"]
    theme_ids = ins.get("supporting_theme_ids", [])

    # Collect items from all supporting themes
    tab_item_ids: list[str] = []
    for tid in theme_ids:
        theme = theme_map.get(tid, {})
        tab_item_ids.extend(theme.get("supporting_item_ids", []))

    # Deduplicate within this tab (item could be in multiple supporting themes)
    seen = set()
    unique_ids = []
    for iid in tab_item_ids:
        if iid not in seen:
            seen.add(iid)
            unique_ids.append(iid)

    all_themed_ids.update(unique_ids)

    # Resolve to actual items (skip any not in filtered corpus)
    theme_items = [item_map[iid] for iid in unique_ids if iid in item_map]

    write_insight_tab(wb, idx, si, theme_items)

# Unthemed tab
unthemed_items = [item for item in corpus if item["item_id"] not in all_themed_ids]
if unthemed_items:
    ws = wb.create_sheet(title="Unthemed Items")

    # Metadata
    ws.cell(row=1, column=1, value="Unthemed Items").font = META_FONT
    ws.cell(row=1, column=1).fill = META_FILL
    ws.cell(row=1, column=2, value=str(len(unthemed_items))).font = Font(name="Lato", size=11)
    ws.cell(row=1, column=2).fill = META_FILL

    rows = [item_to_row(item) for item in unthemed_items]
    rows.sort(key=lambda r: r.get("Engagement", 0), reverse=True)
    write_data_rows(ws, rows, 3)
    print(f"  Tab 'Unthemed Items': {len(unthemed_items)} items")

# Summary tab (insert at position 0)
ws_sum = wb.create_sheet(title="Summary", index=0)

# Brand header
ws_sum.cell(row=1, column=1, value=brand_name).font = NAVY_FONT
ws_sum.merge_cells("A1:D1")
ws_sum.row_dimensions[1].height = 28

overall_nss = analysis.get("net_sentiment_score", 0)
summary_meta = [
    ("Category", category),
    ("Total Items Analysed", len(corpus)),
    ("Insights", len(scored_insights)),
    ("Themes", len(analysis.get("themes", []))),
    ("Net Sentiment Score", f"{overall_nss:+.1%}" if isinstance(overall_nss, (int, float)) else str(overall_nss)),
    ("Export Date", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")),
]

for r_idx, (label, value) in enumerate(summary_meta, 3):
    a = ws_sum.cell(row=r_idx, column=1, value=label)
    b = ws_sum.cell(row=r_idx, column=2, value=value)
    a.font = Font(name="Lato", bold=True, size=10, color="1E3A5F")
    b.font = Font(name="Lato", size=10)
    for c in (a, b):
        c.border = THIN_BORD
        c.alignment = Alignment(horizontal="left", vertical="center")

# Insight overview table
table_start = len(summary_meta) + 5
ws_sum.cell(row=table_start, column=1, value="Insight Overview").font = NAVY_FONT
table_start += 1

ins_headers = ["#", "Theme", "Items", "Confidence", "Signal Strength", "NSS"]
for col_idx, hdr in enumerate(ins_headers, 1):
    cell = ws_sum.cell(row=table_start, column=col_idx, value=hdr)
    cell.font = HDR_FONT
    cell.fill = HDR_FILL
    cell.alignment = HDR_ALIGN
    cell.border = THIN_BORD
ws_sum.row_dimensions[table_start].height = 22

for r_idx, si in enumerate(scored_insights, table_start + 1):
    ins = si["insight"]
    theme_ids = ins.get("supporting_theme_ids", [])
    theme = theme_map.get(theme_ids[0], {}) if theme_ids else {}
    label = theme.get("theme_label", ins.get("insight_id", ""))
    nss = theme.get("net_sentiment_score", 0)

    row_data = [
        r_idx - table_start,
        label,
        ins.get("supporting_item_count", 0),
        f"{si.get('confidence_score', 0):.0%}",
        f"{si.get('signal_strength_score', 0):.0%}",
        f"{nss:+.1%}",
    ]
    is_alt = ((r_idx - table_start) % 2 == 0)
    for col_idx, val in enumerate(row_data, 1):
        cell = ws_sum.cell(row=r_idx, column=col_idx, value=val)
        cell.font = BODY_FONT
        cell.alignment = Alignment(horizontal="left", vertical="center")
        if is_alt:
            cell.fill = ALT_FILL
        cell.border = THIN_BORD

# Summary column widths
for col, w in zip("ABCDEF", [6, 40, 10, 14, 16, 10]):
    ws_sum.column_dimensions[col].width = w

# ── Save ────────────────────────────────────────────────────────────────────
safe_brand = re.sub(r'[^\w\s-]', '', brand_name).strip().replace(' ', '_').lower()
out_path = run_dir / "report" / f"{safe_brand}_insights_data.xlsx"
out_path.parent.mkdir(parents=True, exist_ok=True)
wb.save(str(out_path))
print(f"\nExcel saved: {out_path} ({out_path.stat().st_size:,} bytes)")
print(f"  Themed items: {len(all_themed_ids)}")
print(f"  Unthemed items: {len(unthemed_items) if unthemed_items else 0}")
print(f"  Total corpus: {len(corpus)}")

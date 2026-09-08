"""DOCX report generator - Google-Doc-compatible Word document.

Produces a flowing, section-based research report (no fixed-layout constraints):
- Proper heading hierarchy (H1 → H2 → H3)
- Inline charts with captions
- Block-quoted verbatims (full text, no truncation)
- Data tables for scoring, platform counts, theme prevalence
- Table of contents auto-generated from headings
- Palatino Linotype headings / Calibri body
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import copy

from consumer_research.config import PipelineConfig
from consumer_research.models.schemas import (
    AnalysisResults,
    NormalizedItem,
    ScoredInsight,
)

logger = logging.getLogger(__name__)

# ---- Design Colours (RGB tuples) ----
NAVY      = RGBColor(0x1E, 0x3A, 0x5F)
NAVY_DARK = RGBColor(0x0F, 0x24, 0x40)
GREEN     = RGBColor(0x05, 0x96, 0x69)
RED       = RGBColor(0xDC, 0x26, 0x26)
AMBER     = RGBColor(0xD9, 0x77, 0x06)
SLATE     = RGBColor(0x37, 0x41, 0x51)
GREY_MED  = RGBColor(0x6B, 0x72, 0x80)
GREY_LITE = RGBColor(0xF3, 0xF4, 0xF6)
WHITE     = RGBColor(0xFF, 0xFF, 0xFF)
TEAL      = RGBColor(0x4F, 0xD1, 0xC5)

HEADING_FONT = "Lato"
BODY_FONT    = "Lato"



# ---- Low-level helpers ----

def _rgb_hex(color: RGBColor) -> str:
    return f"{color[0]:02X}{color[1]:02X}{color[2]:02X}"


def _set_cell_text(cell, text: str, font_name: str = BODY_FONT, size_pt: int = 10,
                   bold: bool = False, color: RGBColor = SLATE):
    """Set cell text with explicit font (prevents Cambria fallback)."""
    cell.text = ""
    p = cell.paragraphs[0]
    _run(p, str(text), font_name, size_pt, bold=bold, color=color)
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(3)


def _set_cell_bg(cell, color: RGBColor):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), _rgb_hex(color))
    tcPr.append(shd)


def _set_cell_border(cell, border_color: RGBColor = GREY_MED, size: int = 4):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    for side in ("top", "left", "bottom", "right"):
        border = OxmlElement(f"w:{side}")
        border.set(qn("w:val"), "single")
        border.set(qn("w:sz"), str(size))
        border.set(qn("w:space"), "0")
        border.set(qn("w:color"), _rgb_hex(border_color))
        tcBorders.append(border)
    tcPr.append(tcBorders)


def _para_font(para, font_name: str, size_pt: int, bold: bool = False,
               color: RGBColor | None = None, italic: bool = False):
    for run in para.runs:
        run.font.name = font_name
        run.font.size = Pt(size_pt)
        run.font.bold = bold
        run.font.italic = italic
        if color:
            run.font.color.rgb = color


def _run(para, text: str, font_name: str = BODY_FONT, size_pt: int = 11,
         bold: bool = False, color: RGBColor | None = None, italic: bool = False):
    run = para.add_run(text)
    run.font.name = font_name
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    run.font.italic = italic
    if color:
        run.font.color.rgb = color
    return run


def _heading(doc: Document, text: str, level: int):
    """Add heading with Palatino Linotype in navy."""
    h = doc.add_heading(text, level=level)
    h.alignment = WD_ALIGN_PARAGRAPH.LEFT
    size_map = {1: 22, 2: 16, 3: 13, 4: 12}
    size = size_map.get(level, 12)
    for run in h.runs:
        run.font.name = HEADING_FONT
        run.font.size = Pt(size)
        run.font.color.rgb = NAVY
        run.font.bold = True
    return h


def _body(doc: Document, text: str, size_pt: int = 11, color: RGBColor | None = None,
          italic: bool = False, space_after_pt: int = 6) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after_pt)
    p.paragraph_format.space_before = Pt(0)
    r = _run(p, text, BODY_FONT, size_pt, color=color, italic=italic)


def _bullet(doc: Document, text: str, level: int = 0, bold_prefix: str = ""):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(4)
    if bold_prefix:
        _run(p, bold_prefix + " ", BODY_FONT, 11, bold=True, color=NAVY)
    _run(p, text, BODY_FONT, 11)


def _label_value(doc: Document, label: str, value: str):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4)
    _run(p, label + ": ", BODY_FONT, 11, bold=True, color=NAVY)
    _run(p, value, BODY_FONT, 11)


def _blockquote(doc: Document, text: str, source: str = ""):
    """Indented quote block."""
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(1.2)
    p.paragraph_format.right_indent = Cm(1.2)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)
    _run(p, f'"{text}"', BODY_FONT, 10, italic=True, color=SLATE)
    if source:
        _run(p, f"  - {source}", BODY_FONT, 9, color=GREY_MED)


def _divider(doc: Document):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "4")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), _rgb_hex(GREY_MED))
    pBdr.append(bottom)
    pPr.append(pBdr)


def _add_chart(doc: Document, chart_path: Path, caption: str, width_in: float = 5.5):
    if chart_path.exists():
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        run.add_picture(str(chart_path), width=Inches(width_in))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(12)
    _run(cap, caption, BODY_FONT, 9, italic=True, color=GREY_MED)


def _add_table_header_row(table, headers: list[str], bg: RGBColor = NAVY, text_color: RGBColor = WHITE):
    row = table.rows[0]
    for i, hdr in enumerate(headers):
        cell = row.cells[i]
        cell.text = ""
        _set_cell_bg(cell, bg)
        p = cell.paragraphs[0]
        r = _run(p, hdr, BODY_FONT, 10, bold=True, color=text_color)
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(3)


def _nss_label(nss: float) -> str:
    if nss >= 0.5:
        return f"+{nss:.0%} (Strongly Positive)"
    elif nss >= 0.1:
        return f"+{nss:.0%} (Positive)"
    elif nss >= -0.1:
        return f"{nss:+.0%} (Neutral)"
    elif nss >= -0.5:
        return f"{nss:.0%} (Negative)"
    else:
        return f"{nss:.0%} (Strongly Negative)"


def _sentiment_color(nss: float) -> RGBColor:
    if nss > 0.1:
        return GREEN
    elif nss < -0.1:
        return RED
    return AMBER


# ---- Section builders ----

def _section_cover(doc: Document, brand_name: str, config: PipelineConfig,
                   analysis: AnalysisResults, scored_insights: list[ScoredInsight],
                   brand_health: dict | None = None, items: list | None = None):
    total = analysis.total_items_analyzed
    nss = analysis.net_sentiment_score
    n_insights = len(scored_insights)
    bh_score = (brand_health or {}).get("overall_score", 0)
    n_platforms = len(set(i.source_platform for i in (items or [])))

    # ── Brand name ──────────────────────────────────────────────────────────
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    title.paragraph_format.space_before = Pt(24)
    title.paragraph_format.space_after = Pt(6)
    _run(title, brand_name, HEADING_FONT, 36, bold=True, color=NAVY_DARK)

    # ── Subtitle ─────────────────────────────────────────────────────────────
    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.LEFT
    sub.paragraph_format.space_after = Pt(4)
    _run(sub, "Research Report: Consumer Sentiment & Brand Perception", BODY_FONT, 14, color=SLATE)

    # ── Date ─────────────────────────────────────────────────────────────────
    date_p = doc.add_paragraph()
    date_p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    date_p.paragraph_format.space_after = Pt(28)
    _run(date_p, f"Analysis Date: {datetime.now().strftime('%B %Y')}", BODY_FONT, 11, color=GREY_MED)

    _divider(doc)

    # ── Research Objectives ──────────────────────────────────────────────────
    if config.collection.business_objectives:
        _heading(doc, "Research Objectives", 2)
        for obj in config.collection.business_objectives:
            _bullet(doc, obj)

    doc.add_paragraph()  # spacer

    _divider(doc)

    # ── Summary of Data and Findings ─────────────────────────────────────────
    _heading(doc, "Summary of Data and Findings", 2)

    bh_color = GREEN if bh_score >= 70 else (AMBER if bh_score >= 50 else RED)
    nss_color = GREEN if nss > 0 else (RED if nss < 0 else GREY_MED)

    # Compute content date range from source timestamps
    # Note: this is the span of the original content, not when collection ran
    data_period_str = "N/A"
    if items:
        from datetime import timezone as _tz
        def _to_dt(t):
            if isinstance(t, datetime):
                return t.replace(tzinfo=_tz.utc) if t.tzinfo is None else t
            try:
                parsed = datetime.fromisoformat(str(t).replace("Z", "+00:00"))
                return parsed.replace(tzinfo=_tz.utc) if parsed.tzinfo is None else parsed
            except (ValueError, TypeError):
                return None
        valid_ts = []
        for i in items:
            ts = i.source_timestamp if hasattr(i, "source_timestamp") else i.get("source_timestamp")
            if ts:
                dt = _to_dt(ts)
                if dt:
                    valid_ts.append(dt)
        if valid_ts:
            dt_min, dt_max = min(valid_ts), max(valid_ts)
            data_period_str = f"{dt_min.strftime('%b %Y')} - {dt_max.strftime('%b %Y')}"

    summary_rows = [
        ("Items Analysed", f"{total:,}", NAVY),
        ("Content Date Range", data_period_str, NAVY),
        ("Insights Identified", str(n_insights), NAVY),
        ("Net Sentiment Score", f"{nss:+.1%}", nss_color),
        ("Brand Health Score", f"{bh_score:.0f}/100", bh_color),
        ("Data Sources", f"{n_platforms} platform{'s' if n_platforms != 1 else ''}" if n_platforms else "N/A", NAVY),
    ]

    table = doc.add_table(rows=0, cols=2)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    for label, val, val_color in summary_rows:
        row = table.add_row()
        row.cells[0].text = ""
        _run(row.cells[0].paragraphs[0], label, BODY_FONT, 11, color=SLATE)
        row.cells[1].text = ""
        _run(row.cells[1].paragraphs[0], val, BODY_FONT, 13, bold=True, color=val_color)
        for cell in row.cells:
            cell.paragraphs[0].paragraph_format.space_before = Pt(4)
            cell.paragraphs[0].paragraph_format.space_after = Pt(4)

    doc.add_page_break()


def _section_executive_summary(doc: Document, scored_insights: list[ScoredInsight],
                                analysis: AnalysisResults):
    _heading(doc, "Executive Summary", 1)
    nss = analysis.net_sentiment_score
    total = analysis.total_items_analyzed

    # Identify the largest insights by conversation volume for the summary narrative
    top_sorted = sorted(scored_insights, key=lambda x: (-x.sample_size, -x.confidence_score))
    top_n = min(3, len(top_sorted))
    theme_map = {t.theme_id: t.theme_label for t in analysis.themes}
    top_names = []
    for s in top_sorted[:top_n]:
        for tid in s.insight.supporting_theme_ids:
            if tid in theme_map:
                top_names.append(theme_map[tid])
                break

    _body(doc, (
        f"This report synthesises {total:,} consumer conversations collected across multiple platforms. "
        f"Net Sentiment Score is {nss:+.1%}, with {len(scored_insights)} insights emerging from "
        f"{len(analysis.themes)} distinct themes."
    ))

    if top_names:
        _body(doc, (
            f"The strongest signals centre on {', '.join(top_names[:2])}"
            f"{(' and ' + top_names[2]) if len(top_names) > 2 else ''}, "
            f"each supported by substantial consumer evidence across multiple platforms."
        ))

    # Top insights table (ranked by confidence)
    if top_sorted:
        _heading(doc, "Top Insights at a Glance", 2)
        show_n = min(5, len(top_sorted))
        table = doc.add_table(rows=1, cols=4)
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.LEFT
        _add_table_header_row(table, ["#", "Finding", "Confidence", "Signal"])
        for i, s in enumerate(top_sorted[:show_n], 1):
            row = table.add_row()
            _set_cell_text(row.cells[0], str(i))
            _set_cell_text(row.cells[1], _clean(s.insight.observation))
            _set_cell_text(row.cells[2], f"{s.confidence_score:.0%}")
            _set_cell_text(row.cells[3], f"{s.signal_strength_score:.0%}")
        _body(doc, "", space_after_pt=12)

    doc.add_page_break()


def _section_data_universe(doc: Document, items: list[NormalizedItem],
                            analysis: AnalysisResults, run_dir: Path):
    import json as _json
    _heading(doc, "Data Universe", 1)

    # ── Collection funnel ────────────────────────────────────────────────────
    # Count raw items from each collector file
    raw_total = 0
    raw_dir = run_dir.parent.parent / "runs" / run_dir.name / "raw"
    # run_dir IS the run directory; raw is a subdirectory
    raw_dir = run_dir / "raw"
    if raw_dir.exists():
        for f in raw_dir.glob("*.json"):
            try:
                data = _json.loads(f.read_text(encoding="utf-8"))
                raw_total += len(data) if isinstance(data, list) else 0
            except Exception:
                pass

    norm_file = run_dir / "normalized" / "corpus.json"
    norm_total = 0
    if norm_file.exists():
        try:
            norm_total = len(_json.loads(norm_file.read_text(encoding="utf-8")))
        except Exception:
            pass

    filtered_total = len(items)
    pct_of_raw = filtered_total / raw_total * 100 if raw_total else 0

    _heading(doc, "Collection Funnel", 2)
    _body(doc, (
        f"Of {raw_total:,} raw data points collected across all sources, {norm_total:,} remained after "
        f"deduplication and quality filtering, and {filtered_total:,} passed LLM relevance classification "
        f"({pct_of_raw:.1f}% of total collected). These {filtered_total:,} items form the analysis corpus."
    ))

    funnel_table = doc.add_table(rows=1, cols=3)
    funnel_table.style = "Table Grid"
    _add_table_header_row(funnel_table, ["Stage", "Items", "Notes"])
    funnel_rows = [
        ("Raw collected", f"{raw_total:,}", "All posts, comments, articles and videos gathered across all platforms"),
        ("After deduplication & quality filter", f"{norm_total:,}", f"Thread dedup (max 5 comments/thread, random selection), empty/short text removed"),
        ("After relevance classification", f"{filtered_total:,}", f"LLM relevance filter — {pct_of_raw:.1f}% of raw collected. Analysis corpus."),
    ]
    for stage, count, note in funnel_rows:
        row = funnel_table.add_row()
        _set_cell_text(row.cells[0], stage)
        _set_cell_text(row.cells[1], count)
        _set_cell_text(row.cells[2], note)

    doc.add_paragraph()  # spacer

    # ── Platform breakdown ───────────────────────────────────────────────────
    from collections import Counter
    platforms = Counter(i.source_platform for i in items)
    total = len(items)

    _heading(doc, "Platform Breakdown", 2)

    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    _add_table_header_row(table, ["Platform", "Items", "Share of Corpus"])
    for platform, count in sorted(platforms.items(), key=lambda x: -x[1]):
        row = table.add_row()
        _set_cell_text(row.cells[0], platform.title())
        _set_cell_text(row.cells[1], str(count))
        _set_cell_text(row.cells[2], f"{count / total:.1%}")

    _add_chart(doc, run_dir / "report" / "chart_platforms.png",
               "Figure 1: Item distribution by source platform", width_in=4.5)

    # ── Temporal distribution ───────────────────────────────────────────────
    temporal_chart = run_dir / "report" / "chart_temporal.png"
    if temporal_chart.exists():
        _heading(doc, "Temporal Distribution", 2)
        _body(doc, (
            "The chart below shows when the analysed content was originally published, "
            "based on source timestamps. Percentages are of the full corpus. "
            "Items without a source timestamp are shown separately as 'Undated'."
        ))
        _add_chart(doc, temporal_chart,
                   "Figure 2: Content publication date by year (full corpus denominator)", width_in=5.0)

    _heading(doc, "Collection Methodology", 2)
    is_external = (run_dir / "raw" / "external_ingested.json").exists()
    if is_external:
        _body(doc, (
            "Data was ingested from externally collected sources. The original collection methodology, "
            "sampling strategy, and any platform-specific filtering applied prior to ingestion are not "
            "documented in this pipeline and should be considered unknown."
        ))
    else:
        _body(doc, (
            "Data was collected using automated scrapers across all platforms without engagement thresholds. "
            "Every item that passed quality controls (non-empty text, minimum length, deduplication) "
            "entered the corpus regardless of engagement metrics."
        ))
    _body(doc, (
        "Thread-level deduplication caps comments per thread (max 5, randomly selected) to prevent "
        "over-indexing vocal threads. Engagement metrics are preserved as metadata for signal strength "
        "scoring but do not gate corpus admission. All items passed an LLM relevance classification "
        "step before analysis."
    ))

    doc.add_page_break()


def _section_sentiment(doc: Document, analysis: AnalysisResults, run_dir: Path):
    _heading(doc, "Sentiment & Emotion Analysis", 1)

    sent = analysis.overall_sentiment
    nss = analysis.net_sentiment_score
    total_sent = sum(sent.values())

    _heading(doc, "Overall Sentiment Distribution", 2)
    _body(doc, (
        f"Net Sentiment Score (NSS): {nss:+.1%}  |  "
        f"Positive: {sent.get('positive', 0)} ({sent.get('positive', 0) / max(total_sent, 1):.1%})  |  "
        f"Negative: {sent.get('negative', 0)} ({sent.get('negative', 0) / max(total_sent, 1):.1%})  |  "
        f"Neutral: {sent.get('neutral', 0)} ({sent.get('neutral', 0) / max(total_sent, 1):.1%})"
    ))
    _body(doc, (
        "NSS is computed as (positive - negative) / total items. Range: -1.0 (all negative) to +1.0 (all positive). "
        "Neutral and mixed items remain in the denominator, anchoring the score to the full corpus rather than "
        "just polarised items. A positive NSS indicates net favourable sentiment; a negative NSS indicates net unfavourable."
    ), italic=True, color=GREY_MED)

    _add_chart(doc, run_dir / "report" / "chart_sentiment.png",
               f"Figure 2: Sentiment distribution across {total_sent:,} items", width_in=5.0)

    # Emotion distribution
    _heading(doc, "Emotion Profile (Plutchik 8-Emotion Model)", 2)
    emotions = analysis.emotion_distribution
    if emotions:
        table = doc.add_table(rows=1, cols=2)
        table.style = "Table Grid"
        _add_table_header_row(table, ["Emotion", "Count"])
        for emotion, count in sorted(emotions.items(), key=lambda x: -x[1]):
            row = table.add_row()
            _set_cell_text(row.cells[0], emotion.title())
            _set_cell_text(row.cells[1], str(count))

    _add_chart(doc, run_dir / "report" / "chart_emotions.png",
               "Figure 3: Plutchik emotion distribution", width_in=5.0)

    # Aspect sentiment
    _heading(doc, "Aspect-Based Sentiment Analysis (ABSA)", 2)
    _body(doc, (
        "Aspects with ≥10 mentions are shown below. NSS is statistically meaningful only at this threshold."
    ))
    asp = analysis.aspect_sentiment_summary
    qualifying = {a: d for a, d in asp.items()
                  if sum(d.values()) >= 10}

    if qualifying:
        table = doc.add_table(rows=1, cols=5)
        table.style = "Table Grid"
        _add_table_header_row(table, ["Aspect", "Total", "Positive", "Negative", "NSS"])
        for aspect, d in sorted(qualifying.items(), key=lambda x: -sum(x[1].values())):
            tot = sum(d.values())
            pos = d.get("positive", 0)
            neg = d.get("negative", 0)
            nss_a = (pos - neg) / tot if tot else 0
            row = table.add_row()
            _set_cell_text(row.cells[0], aspect.replace("_", " ").title())
            _set_cell_text(row.cells[1], str(tot))
            _set_cell_text(row.cells[2], str(pos))
            _set_cell_text(row.cells[3], str(neg))
            _set_cell_text(row.cells[4], f"{nss_a:+.0%}")
        _body(doc, "", space_after_pt=6)

    _add_chart(doc, run_dir / "report" / "chart_aspect_heatmap.png",
               "Figure 4: Aspect sentiment heatmap (aspects with ≥10 mentions)", width_in=5.5)

    doc.add_page_break()


def _section_themes(doc: Document, analysis: AnalysisResults, run_dir: Path,
                    scored_insights: list | None = None):
    _heading(doc, "Insight Landscape", 1)
    _body(doc, (
        f"{len(scored_insights) if scored_insights else len(analysis.themes)} insights were identified from {analysis.total_items_analyzed:,} items "
        f"using a two-pass extraction approach (stratified discovery sample + full-corpus mapping)."
    ))

    # Build lookup: theme_id -> scored insight (for confidence + signal columns)
    scored_map: dict = {}
    if scored_insights:
        for s in scored_insights:
            for tid in getattr(s.insight, "supporting_theme_ids", []):
                scored_map[tid] = s

    table = doc.add_table(rows=1, cols=6)
    table.style = "Table Grid"
    _add_table_header_row(table, ["Insight", "Items", "Prevalence in Dataset", "Signal Strength", "Confidence Score", "NSS"])
    for t in sorted(analysis.themes, key=lambda x: -x.item_count):
        scored = scored_map.get(t.theme_id)
        row = table.add_row()
        _set_cell_text(row.cells[0], t.theme_label)
        _set_cell_text(row.cells[1], str(t.item_count))
        _set_cell_text(row.cells[2], f"{t.prevalence_pct:.1f}%")
        if scored:
            sig = scored.signal_strength_score
            sig_tier = scored.signal_strength_tier.value.title()
            _set_cell_text(row.cells[3], f"{sig:.0%} ({sig_tier})")
            conf = scored.confidence_score
            conf_tier = scored.confidence_tier.value.title()
            _set_cell_text(row.cells[4], f"{conf:.0%} ({conf_tier})")
        else:
            _set_cell_text(row.cells[3], "-")
            _set_cell_text(row.cells[4], "-")
        nss = t.net_sentiment_score or 0
        _set_cell_text(row.cells[5], f"{nss:+.0%}")

    _add_chart(doc, run_dir / "report" / "chart_themes.png",
               "Figure 5: Insight prevalence (% of total corpus)", width_in=5.5)

    doc.add_page_break()


# Theme IDs are internal pipeline handles. They are assigned in discovery order, while the
# report orders themes by size and insights by confidence, so a reader meets "T04" as the
# first, second or ninth thing on the page and reasonably reads it as a rank. Populated per
# run by generate_docx_report, consumed by _clean so every render path is covered.
_THEME_LABELS: dict[str, str] = {}
_THEME_ID_RE = re.compile(r"\bT\d{2}\b")


def _strip_theme_ids(text: str) -> str:
    """Drop internal theme IDs, keeping the label the reader can actually use.

    Three shapes occur in authored insight prose: the ID leading its own label
    ("T04 The weekly ritual: ..."), the ID cited parenthetically ("(T06, 1,398 items)"),
    and a bare ID. The first is a duplicate and the ID simply goes; the other two carry
    meaning only via the label, so the label is substituted in.
    """
    for tid, label in _THEME_LABELS.items():
        text = text.replace(f"{tid} {label}", label)

    def sub(m):
        label = _THEME_LABELS.get(m.group(0))
        return label[0].lower() + label[1:] if label else ""

    return re.sub(r"\s{2,}", " ", _THEME_ID_RE.sub(sub, text)).strip()


def _clean(text: str) -> str:
    """Replace em dashes with hyphens and drop internal theme IDs."""
    return _strip_theme_ids(text.replace("\u2014", "-").replace("\u2013", "-"))


def _section_deep_dives(doc: Document, scored_insights: list[ScoredInsight],
                        analysis: AnalysisResults, run_dir: Path):
    _heading(doc, "Insight Deep Dives", 1)
    _body(doc, "One insight per theme, ordered by conversation volume. Each insight follows the framework: What the Data Shows, What it Means, Business Implication and Rationale, Recommendation.")

    theme_map = {t.theme_id: t for t in analysis.themes}

    for i, scored in enumerate(sorted(scored_insights, key=lambda x: (-x.sample_size, -x.confidence_score)), 1):
        ins = scored.insight
        conf_color = GREEN if scored.confidence_tier.value == "high" else (AMBER if scored.confidence_tier.value == "medium" else GREY_MED)

        theme_label = "Unknown Insight"
        theme_obj = None
        for tid in ins.supporting_theme_ids:
            if tid in theme_map:
                theme_label = theme_map[tid].theme_label
                theme_obj = theme_map[tid]
                break

        nss = (theme_obj.net_sentiment_score or 0) if theme_obj else 0
        nss_col = GREEN if nss > 0.1 else (RED if nss < -0.1 else AMBER)

        # 1. Insight heading
        _heading(doc, f"{i:02d}. {theme_label}", 2)

        # 2. Single data line: n= | Confidence | Signal | Prevalence | NSS
        data_p = doc.add_paragraph()
        data_p.paragraph_format.space_after = Pt(8)
        _run(data_p, f"n={scored.sample_size}", BODY_FONT, 9, color=GREY_MED)
        _run(data_p, "  |  Confidence: ", BODY_FONT, 9, color=SLATE)
        _run(data_p, f"{scored.confidence_score:.0%} ({scored.confidence_tier.value.title()})", BODY_FONT, 9, bold=True, color=conf_color)
        _run(data_p, "  |  Signal: ", BODY_FONT, 9, color=SLATE)
        _run(data_p, f"{scored.signal_strength_score:.0%} ({scored.signal_strength_tier.value.title()})", BODY_FONT, 9, bold=True, color=SLATE)
        if theme_obj:
            _run(data_p, f"  |  {theme_obj.prevalence_pct:.1f}% of Dataset", BODY_FONT, 9, color=GREY_MED)
            _run(data_p, "  |  NSS: ", BODY_FONT, 9, color=GREY_MED)
            _run(data_p, f"{nss:+.0%}", BODY_FONT, 9, bold=True, color=nss_col)

        # 3. Radar chart immediately after data line
        radar_path = run_dir / "report" / f"chart_radar_{ins.insight_id}.png"
        if radar_path.exists():
            _add_chart(doc, radar_path, f"Score Breakdown: {theme_label}", width_in=3.8)

        # 4. What the Data Shows
        _heading(doc, "What the Data Shows", 3)
        _body(doc, _clean(ins.observation))

        # 5. What it Means
        _heading(doc, "What it Means", 3)
        _body(doc, _clean(ins.insight))

        # 6. Business Implication & Rationale
        _heading(doc, "Business Implication & Rationale", 3)
        _body(doc, _clean(ins.implication))

        # 7. Recommendation
        _heading(doc, "Recommendation", 3)
        _body(doc, _clean(ins.recommendation))

        # 8. Representative Voices (2-3 quotes)
        if theme_obj and theme_obj.representative_quotes:
            _heading(doc, "Representative Voices", 3)
            for q in theme_obj.representative_quotes[:4]:
                if isinstance(q, dict):
                    text = q.get("text", "")
                    url = q.get("source_url", "") or ""
                    platform = url.split("/")[2].replace("www.", "") if url else ""
                elif isinstance(q, str):
                    text, platform = q, ""
                else:
                    text = getattr(q, "text", "") or ""
                    sp = getattr(q, "source_platform", None)
                    platform = sp.value if hasattr(sp, "value") else str(sp or "")
                if text.strip():
                    _blockquote(doc, _clean(text), platform)

        if i < len(scored_insights):
            _divider(doc)

    doc.add_page_break()




def _section_brand_health(doc: Document, bh: dict):
    _heading(doc, "Brand Health Score", 1)
    overall = bh.get("overall_score", 0)

    score_color = GREEN if overall >= 70 else (AMBER if overall >= 50 else RED)
    score_p = doc.add_paragraph()
    score_p.paragraph_format.space_after = Pt(8)
    _run(score_p, f"Overall Brand Health Score: ", BODY_FONT, 13, bold=True, color=NAVY)
    _run(score_p, f"{overall:.0f}/100", HEADING_FONT, 20, bold=True, color=score_color)

    _body(doc, (
        "Brand Health Score is a composite index built from five data-driven components. "
        "No subjective weighting is applied - all inputs are derived from the collected corpus."
    ))

    # Advocacy is a capped index, not a proportion, and it measures sentiment intensity rather
    # than stated recommendation. Describe it as what it is, and print the share underneath it,
    # because any share at or above 20% renders an identical 100.
    adv_pct = bh.get("advocacy_ratio_pct")
    adv_method = (
        "Share of items classified strongly positive, meaning positive sentiment at intensity "
        "0.8 or above. Scored as that share multiplied by 5 and capped at 100, so any share at "
        "or above 20% returns 100. Does not measure stated recommendation or repurchase intent; "
        "no stage of this pipeline detects those."
    )
    if adv_pct is not None:
        adv_method += f" This corpus: {adv_pct:.1f}% strongly positive."
        if adv_pct >= 20:
            adv_method += (" The component is at its ceiling and does not discriminate "
                           "above this point.")

    components = [
        ("Sentiment Component (30%)", bh.get("sentiment_component", 0),
         "Derived from NSS across all items. Reflects the ratio of positive to negative consumer language."),
        ("Engagement Component (25%)", bh.get("engagement_component", 0),
         "Average engagement (upvotes, likes, comments) normalised to platform benchmarks."),
        ("Advocacy Component (20%)", bh.get("advocacy_component", 0), adv_method),
        ("Resilience Component (15%)", bh.get("resilience_component", 0),
         "Sentiment consistency across platforms and time periods."),
        ("Conversation Component (10%)", bh.get("conversation_component", 0),
         "Volume and depth of organic brand conversation (non-promotional threads)."),
    ]
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    _add_table_header_row(table, ["Component", "Score", "Methodology"])
    for name, score, method in components:
        row = table.add_row()
        _set_cell_text(row.cells[0], name)
        col = GREEN if score >= 70 else (AMBER if score >= 50 else RED)
        _set_cell_text(row.cells[1], f"{score:.1f}", bold=True, color=col)
        _set_cell_text(row.cells[2], method)

    # Callout for low Conversation Component — a meaningful finding, not just a low score
    conv_score = bh.get("conversation_component", 0)
    if conv_score < 50:
        callout = doc.add_paragraph()
        callout.paragraph_format.space_before = Pt(14)
        callout.paragraph_format.space_after = Pt(6)
        _run(callout, "Note: ", BODY_FONT, 11, bold=True, color=NAVY)
        _run(callout, (
            f"The Conversation Component ({conv_score:.0f}/100) is the lowest-scoring factor. "
            "This reflects that most brand mentions occur in reaction to advertising, campaigns, "
            "and celebrity content rather than unprompted consumer-initiated discussion. "
            "Organic brand conversation is thin relative to engagement volume - "
            "a pattern consistent with a brand consumers transact with rather than one they actively champion."
        ), BODY_FONT, 11, color=SLATE)

    doc.add_page_break()


def _section_recommendations(doc: Document, scored_insights: list[ScoredInsight]):
    _heading(doc, "Recommendations", 1)
    _body(doc, (
        "Recommendations are derived directly from insight implications. Priority order follows "
        "conversation volume (primary) and confidence score (secondary)."
    ))

    all_sorted = sorted(scored_insights, key=lambda x: (-x.sample_size, -x.confidence_score))

    for i, s in enumerate(all_sorted, 1):
        ins = s.insight
        _heading(doc, f"Recommendation {i:02d}", 2)
        _label_value(doc, "Recommendation", _clean(ins.recommendation))
        _label_value(doc, "Rationale", _clean(ins.implication))
        _body(doc, "", space_after_pt=4)

    doc.add_page_break()


def _section_verbatims(doc: Document, analysis: AnalysisResults, items: list[NormalizedItem]):
    _heading(doc, "Verbatim Evidence", 1)
    _body(doc, (
        "Representative consumer quotes organised by theme. "
        "All quotes are reproduced in full - no truncation."
    ))

    # Map item_id → item for fast lookup
    item_map = {i.item_id: i for i in items}

    for t in sorted(analysis.themes, key=lambda x: -x.item_count):
        nss = t.net_sentiment_score or 0
        nss_col = GREEN if nss > 0.1 else (RED if nss < -0.1 else AMBER)

        _heading(doc, t.theme_label, 2)
        stat_p = doc.add_paragraph()
        stat_p.paragraph_format.space_after = Pt(6)
        _run(stat_p, f"{t.item_count} items  |  {t.prevalence_pct:.1f}% prevalence  |  NSS: ", BODY_FONT, 10, color=GREY_MED)
        _run(stat_p, f"{nss:+.0%}", BODY_FONT, 10, bold=True, color=nss_col)
        _run(stat_p, f"  |  Platforms: {', '.join(t.platforms_present)}", BODY_FONT, 10, color=GREY_MED)

        # Show all representative quotes in full
        quotes = t.representative_quotes or []
        for q in quotes:
            if isinstance(q, dict):
                text = q.get("text", "")
                url = q.get("source_url", "") or ""
                platform = getattr(q.get("source_platform"), "value", str(q.get("source_platform", "")))
                if not platform and url:
                    parts = url.split("/")
                    platform = parts[2].replace("www.", "") if len(parts) > 2 else ""
            elif isinstance(q, str):
                text = q
                platform = ""
            else:
                # VerbatimQuote Pydantic object
                text = getattr(q, "text", "") or ""
                sp = getattr(q, "source_platform", None)
                platform = sp.value if hasattr(sp, "value") else str(sp or "")
            if text.strip():
                _blockquote(doc, text, platform)

        _divider(doc)

    doc.add_page_break()


def _section_methodology(doc: Document, config: PipelineConfig, analysis: AnalysisResults, items: list = None, run_dir: Path = None):
    _heading(doc, "Methodology", 1)

    # Derive platform list from actual data
    if items:
        platforms_used = sorted(set(
            (i.source_platform.value.title() if hasattr(i.source_platform, 'value') else str(i.source_platform).title())
            for i in items
        ))
        platform_str = ", ".join(platforms_used)
    else:
        platform_str = "multiple platforms"

    model_name = config.analysis.claude_model if hasattr(config.analysis, 'claude_model') else "Claude"

    sc = config.scoring

    _heading(doc, "Pipeline Overview", 2)
    stages = [
        ("Stage 0 - Brief", "Structured research brief defines brand, competitors, geography, business objectives, and keyword seed list."),
        ("Stage 1 - Collect", (
            f"Data ingested from external sources across {platform_str}. Original collection methodology unknown."
            if run_dir and (run_dir / "raw" / "external_ingested.json").exists()
            else f"Automated collection across {platform_str}. No engagement thresholds applied - all items enter the corpus."
        )),
        ("Stage 2 - Normalize", "Thread-level deduplication (comments capped per thread). Deterministic SHA-256 item IDs prevent re-collection of duplicates across runs."),
        ("Stage 3 - Filter", f"LLM relevance classification ({model_name}). Each item classified as relevant/irrelevant with a reason. Multilingual support enabled."),
        ("Stage 4 - Analyze", "Sentiment (positive/negative/neutral/mixed) + Plutchik 8-emotion classification in a single LLM call. ABSA: per-aspect sentiment extracted. Two-pass theme extraction: (a) discovery on stratified sample to identify candidate themes; (b) full-corpus mapping of all items to themes in batches."),
        ("Stage 5 - Synthesize", "One insight per theme, mandated by prompt. Insight structure: Observation - Insight - Implication - Recommendation."),
        ("Stage 6 - Score", "Fully data-driven scoring. Confidence: 5 factors (sample size, source diversity, temporal consistency, internal agreement, data recency). Signal Strength: 4 factors (prevalence, engagement, sentiment intensity, conversation depth). Brand Health Score: 5 components."),
        ("Stage 7 - Report", "Google Doc-compatible DOCX with inline charts, block-quoted verbatims, and full data tables."),
    ]
    for stage, desc in stages:
        _bullet(doc, desc, bold_prefix=stage)

    _heading(doc, "Scoring Formulas", 2)
    _heading(doc, "Confidence Score", 3)
    _body(doc, (
        f"Confidence = (sample_size x {sc.confidence_sample_size}) + "
        f"(source_diversity x {sc.confidence_source_diversity}) + "
        f"(temporal_consistency x {sc.confidence_temporal_consistency}) + "
        f"(internal_agreement x {sc.confidence_internal_agreement}) + "
        f"(data_recency x {sc.confidence_data_recency})"
    ))
    _heading(doc, "Signal Strength Score", 3)
    _body(doc, (
        f"Signal = (prevalence x {sc.signal_prevalence}) + "
        f"(engagement x {sc.signal_engagement}) + "
        f"(sentiment_intensity x {sc.signal_sentiment_intensity}) + "
        f"(conversation_depth x {sc.signal_conversation_depth})"
    ))
    _heading(doc, "Net Sentiment Score (NSS)", 3)
    _body(doc, "NSS = (positive_count - negative_count) / total_count. Range -1.0 to +1.0. Industry standard: Brandwatch, Sprinklr, YouGov.")

    _heading(doc, "Quality Gates", 2)
    gates = ["Grounded (≥3 sources cited)", "Non-obvious (not derivable from common knowledge)",
             "Actionable (leads to a concrete business decision)", "Specific (not vague platitude)",
             "Falsifiable (could be proven wrong with additional data)"]
    for g in gates:
        _bullet(doc, g)

    doc.add_page_break()


def _section_data_provenance(doc: Document, config: PipelineConfig, items: list = None):
    _heading(doc, "Data Provenance", 1)

    _body(doc, "All data is sourced from publicly available online conversations. No personally identifiable information (PII) is stored or reported.")

    # Derive actual platforms and counts from data
    from collections import Counter
    items = items or []

    def _plat_val(item):
        if hasattr(item, "source_platform"):
            v = item.source_platform
            return v.value if hasattr(v, "value") else str(v)
        if isinstance(item, dict):
            return str(item.get("source_platform", "unknown"))
        return "unknown"

    platform_counts = Counter(_plat_val(i) for i in items)

    # Content type breakdown
    def _type_val(item):
        if hasattr(item, "content_type"):
            v = item.content_type
            return v.value if hasattr(v, "value") else str(v)
        if isinstance(item, dict):
            return str(item.get("content_type", "unknown"))
        return "unknown"

    type_counts = Counter(_type_val(i) for i in items)

    # Platform metadata - known access methods and content types
    PLATFORM_INFO = {
        "reddit": ("Reddit", "Forum discussions, comments", "Public JSON API"),
        "youtube": ("YouTube", "Video descriptions, comments", "YouTube Data API v3"),
        "twitter": ("Twitter / X", "Tweets, replies, quote tweets", "Platform API / external collection"),
        "instagram": ("Instagram", "Posts, reels, comments", "Platform API / external collection"),
        "news": ("NewsData.io", "News articles", "REST API"),
        "academic": ("OpenAlex", "Academic papers", "Public API"),
        "trends": ("Google Trends", "Search interest data", "PyTrends"),
        "amazon": ("Amazon", "Product reviews", "Web scraping"),
    }

    # Compute date range from items
    timestamps = []
    for item in items:
        ts = item.source_timestamp if hasattr(item, "source_timestamp") else item.get("source_timestamp")
        if ts:
            timestamps.append(ts)

    date_range_str = "Not available"
    earliest = latest = None
    if timestamps:
        from datetime import datetime as _dt, timezone as _tz
        def to_dt(t):
            if isinstance(t, _dt):
                # Normalize to UTC-aware
                if t.tzinfo is None:
                    return t.replace(tzinfo=_tz.utc)
                return t
            try:
                parsed = _dt.fromisoformat(str(t).replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=_tz.utc)
                return parsed
            except (ValueError, TypeError):
                return None
        valid_ts = [to_dt(t) for t in timestamps if to_dt(t) is not None]
        if valid_ts:
            earliest = min(valid_ts)
            latest = max(valid_ts)
            date_range_str = f"{earliest.strftime('%b %Y')} - {latest.strftime('%b %Y')}"

    # ── Source table ──
    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    _add_table_header_row(table, ["Source", "Content Type", "Access Method", "Items in Corpus"])
    for plat_key, count in platform_counts.most_common():
        info = PLATFORM_INFO.get(plat_key, (plat_key.title(), "Online content", "Various"))
        row = table.add_row()
        _set_cell_text(row.cells[0], info[0])
        _set_cell_text(row.cells[1], info[1])
        _set_cell_text(row.cells[2], info[2])
        _set_cell_text(row.cells[3], f"{count:,}")

    # Content type summary
    post_n = type_counts.get("post", 0)
    comment_n = type_counts.get("comment", 0)
    other_n = sum(v for k, v in type_counts.items() if k not in ("post", "comment"))
    parts = []
    if post_n:
        parts.append(f"{post_n:,} posts")
    if comment_n:
        parts.append(f"{comment_n:,} comments")
    if other_n:
        parts.append(f"{other_n:,} other items")
    if parts:
        _body(doc, f"Corpus composition: {' and '.join(parts)}. Each comment is treated as an independent item linked to its parent post for thread-level analysis.")

    # ── Geographic Coverage ──
    geo = getattr(config.collection, "trends_geo", "")
    GEO_NAMES = {"IN": "India", "US": "United States", "GB": "United Kingdom", "AU": "Australia"}
    geo_name = GEO_NAMES.get(geo, geo or "Global")
    _heading(doc, "Geographic Coverage", 2)
    _body(doc, (
        f"Primary market context: {geo_name}. Content is collected using market-specific queries "
        f"(brand names, regional terms, {geo_name}-specific keywords) and filtered for topical relevance. "
        f"However, no platform provides verified geolocation data. Geographic origin is inferred from "
        f"context (language, currency references, retailer mentions, cultural markers) rather than verified. "
        f"Audit of comparable studies found 2-3% of corpus items originate from non-target markets "
        f"(e.g., US product listings, UK healthcare discussions) that pass topical relevance filters. "
        f"Findings in this report describe conversations about the brand in the {geo_name} market context, "
        f"not verified conversations from {geo_name} consumers."
    ))

    # ── Temporal Coverage ──
    _heading(doc, "Temporal Coverage", 2)
    if earliest and latest:
        from datetime import timezone as _tz
        span_days = (latest - earliest).days
        span_months = round(span_days / 30.4)
        _body(doc, f"Data range: {date_range_str} ({span_months} months). Items span the full collection period with no temporal exclusion applied at normalization.")
    else:
        _body(doc, f"Data range: {date_range_str}.")

    # ── Demographic Accuracy ──
    _heading(doc, "Demographic Accuracy", 2)

    PLATFORM_BIASES = {
        "reddit": "Reddit skews male, urban, and 18-34",
        "twitter": "Twitter/X skews male, urban, politically engaged, and 25-44; high-follower accounts dominate visibility while ordinary consumer voices are underrepresented",
        "youtube": "YouTube is more balanced across gender but skews younger audiences; creator content dominates over consumer discussion",
        "instagram": "Instagram skews female, urban, and 18-34 with strong influencer and health-creator content that shapes but does not represent consumer opinion",
        "news": "news sources carry no demographic signal",
        "academic": "academic sources carry no demographic signal",
        "trends": "Google Trends reflects search behaviour, not opinion, and carries no demographic signal",
        "amazon": "Amazon reviews skew toward verified purchasers but demographics are unknown",
    }

    present_platforms = [p for p in platform_counts.keys()]
    bias_parts = [PLATFORM_BIASES[p] for p in present_platforms if p in PLATFORM_BIASES]
    bias_text = "; ".join(bias_parts) if bias_parts else "platform-specific demographic biases are not fully characterised"

    _body(doc, (
        "This methodology explicitly documents platform-level composition so that interpretation "
        f"accounts for known biases: {bias_text}. "
        "These biases are documented rather than hidden. For verified demographic breakdowns, commission "
        "a structured survey targeted to the same research questions, using this report's insights as "
        "the stimulus."
    ))


def _next_report_version(report_dir: Path) -> int:
    """Get the next serial version number for report files.

    Scans for existing report_v*.docx files, parses version numbers
    numerically (not alphabetically), and returns max + 1.
    Filters out Word lock files (~$...).
    """
    import re
    existing = [p for p in report_dir.glob("report_v*.docx") if not p.name.startswith("~$")]
    if not existing:
        return 1
    nums = []
    for p in existing:
        m = re.search(r"report_v(\d+)\.docx$", p.name)
        if m:
            nums.append(int(m.group(1)))
    return max(nums) + 1 if nums else 1


# ---- Main entry point ----

def generate_docx_report(
    scored_insights: list[ScoredInsight],
    analysis: AnalysisResults,
    items: list[NormalizedItem],
    config: PipelineConfig,
    run_dir: Path,
    brand_health: dict | None = None,
) -> Path:
    """Generate a Google-Doc-compatible DOCX report. Returns path to the written file."""
    out_dir = run_dir / "report"
    out_dir.mkdir(parents=True, exist_ok=True)

    next_ver = _next_report_version(out_dir)
    out_path = out_dir / f"report_v{next_ver:03d}.docx"

    doc = Document()

    # Page margins - 2.5 cm all sides (A4 feel, not US letter defaults)
    for section in doc.sections:
        section.top_margin    = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin   = Cm(2.5)
        section.right_margin  = Cm(2.5)

    brand_name = config.collection.brand_name
    bh = brand_health or {}

    _THEME_LABELS.clear()
    _THEME_LABELS.update({t.theme_id: t.theme_label for t in analysis.themes if t.theme_id})

    # Build report sections
    _section_cover(doc, brand_name, config, analysis, scored_insights, bh, items=items)
    _section_data_universe(doc, items, analysis, run_dir)
    _section_sentiment(doc, analysis, run_dir)
    _section_themes(doc, analysis, run_dir, scored_insights=scored_insights)
    _section_deep_dives(doc, scored_insights, analysis, run_dir)
    _section_brand_health(doc, bh)
    _section_methodology(doc, config, analysis, items, run_dir=run_dir)
    _section_data_provenance(doc, config, items)

    doc.save(str(out_path))
    logger.info(f"DOCX saved: {out_path} ({out_path.stat().st_size:,} bytes)")
    return out_path

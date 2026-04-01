"""PPTX report generator using python-pptx.

Generates a 20-22 slide editable deck with a consulting design language:
- Dark navy slides for Cover + Executive Summary (sandwich structure)
- White slides for data/analysis sections
- Card-style rows, metric callout bars, number circles
- No accent lines under titles (whitespace-driven hierarchy)
"""

from __future__ import annotations

import logging
from datetime import datetime
from io import BytesIO
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

from consumer_research.config import PipelineConfig
from consumer_research.models.schemas import (
    AnalysisResults,
    MatrixQuadrant,
    NormalizedItem,
    ScoredInsight,
    ConfidenceTier,
    SignalStrengthTier,
)
from consumer_research.report.charts import generate_all_charts

logger = logging.getLogger(__name__)

# ---- Design Spec Colors ----
NAVY_DARK = RGBColor(0x0F, 0x24, 0x40)
NAVY = RGBColor(0x1E, 0x3A, 0x5F)
NAVY_LIGHT = RGBColor(0x2E, 0x5A, 0x8A)
SLATE = RGBColor(0x37, 0x41, 0x51)
LIGHT_SLATE = RGBColor(0x4B, 0x55, 0x63)
MEDIUM_GREY = RGBColor(0x6B, 0x72, 0x80)
GREY_100 = RGBColor(0xF3, 0xF4, 0xF6)
BORDER_GREY = RGBColor(0xE5, 0xE7, 0xEB)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GREEN = RGBColor(0x05, 0x96, 0x69)
RED = RGBColor(0xDC, 0x26, 0x26)
AMBER = RGBColor(0xD9, 0x77, 0x06)
TEAL = RGBColor(0x4F, 0xD1, 0xC5)
BLUE = RGBColor(0x2B, 0x6C, 0xB0)

# Badge / table colors
ALT_ROW = GREY_100
BADGE_HIGH = NAVY
BADGE_MEDIUM = TEAL
BADGE_DIRECTIONAL = AMBER
BADGE_INSUFFICIENT = RGBColor(0x9C, 0xA3, 0xAF)

# Font families
TITLE_FONT = "Palatino Linotype"
BODY_FONT = "Inter"

QUADRANT_COLORS = {
    MatrixQuadrant.KEY_FINDING: NAVY,
    MatrixQuadrant.EMERGING_TREND: TEAL,
    MatrixQuadrant.WATCH_CLOSELY: AMBER,
    MatrixQuadrant.NOISE: MEDIUM_GREY,
}

CONFIDENCE_BADGE_COLORS = {
    ConfidenceTier.HIGH: NAVY,
    ConfidenceTier.MEDIUM: TEAL,
    ConfidenceTier.DIRECTIONAL: AMBER,
    ConfidenceTier.INSUFFICIENT: BADGE_INSUFFICIENT,
}

# Slide dimensions (16:9 widescreen)
SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

# Margins
LEFT_MARGIN = Inches(0.8)
RIGHT_MARGIN = Inches(0.8)
TOP_MARGIN = Inches(0.5)
CONTENT_TOP = Inches(1.3)
CONTENT_W = Inches(11.7)


def generate_pptx_report(
    scored_insights: list[ScoredInsight],
    analysis: AnalysisResults,
    items: list[NormalizedItem],
    config: PipelineConfig,
    run_dir: Path,
) -> Path:
    """Generate a professional multi-slide PPTX report."""
    report_dir = run_dir / "report"
    report_dir.mkdir(parents=True, exist_ok=True)

    # Generate all charts first
    charts = generate_all_charts(analysis, scored_insights, items, report_dir)

    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    # Compute shared data
    platform_counts = {}
    for item in items:
        p = item.source_platform.value
        platform_counts[p] = platform_counts.get(p, 0) + 1

    # SECTION A: FOUNDATION
    _slide_cover(prs, config, run_dir)
    _slide_objectives(prs, config)
    _slide_methodology_overview(prs, config, analysis, items, platform_counts)
    _slide_data_universe(prs, items, analysis, scored_insights, platform_counts, charts)
    _slide_executive_summary(prs, scored_insights, analysis)

    # SECTION B: PERCEPTION ANALYSIS
    _slide_sentiment_emotion(prs, analysis, items, charts)
    _slide_emotional_profile(prs, analysis, charts)
    _slide_aspect_sentiment(prs, analysis, charts)
    _slide_themes_overview(prs, analysis, charts)

    # Insight deep dives — top 5
    for i, scored in enumerate(scored_insights[:5]):
        _slide_insight_deep_dive(prs, scored, i, charts)

    # SECTION C: STRATEGIC FRAMEWORK
    _slide_matrix(prs, scored_insights, charts)
    _slide_recommendations(prs, scored_insights)
    _slide_further_research(prs, scored_insights)
    _slide_risk_limitations(prs, config, analysis)

    # SECTION D: APPENDIX
    _slide_scoring_breakdown(prs, scored_insights)
    _slide_methodology_detail(prs, analysis)
    _slide_data_provenance(prs, items, run_dir)
    _slide_verbatim_index(prs, analysis)
    _slide_glossary(prs)

    # Serial-numbered naming: report_v001.pptx, report_v002.pptx, ...
    max_num = 0
    for f in report_dir.glob("report_v*.pptx"):
        if f.name.startswith("~$"):
            continue
        try:
            num = int(f.stem.split("_v")[1])
            max_num = max(max_num, num)
        except (IndexError, ValueError):
            pass
    next_num = max_num + 1
    pptx_path = report_dir / f"report_v{next_num:03d}.pptx"
    prs.save(str(pptx_path))
    logger.info(f"PPTX generated: {pptx_path} ({len(prs.slides)} slides)")
    return pptx_path


# ---- Slide Helpers ----

def _add_slide(prs):
    """Add a blank slide with white background."""
    layout = prs.slide_layouts[6]  # Blank
    slide = prs.slides.add_slide(layout)
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = WHITE
    return slide


def _dark_slide(prs):
    """Add a blank slide with dark navy background."""
    layout = prs.slide_layouts[6]  # Blank
    slide = prs.slides.add_slide(layout)
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = NAVY_DARK
    return slide


def _add_header(slide, title: str, subtitle: str = "", dark: bool = False):
    """Add a section header using whitespace hierarchy (no rule line).

    On white slides: navy title, grey subtitle.
    On dark slides: white title, light grey subtitle.
    """
    title_color = WHITE if dark else NAVY
    subtitle_color = RGBColor(0x94, 0xA3, 0xB8) if dark else MEDIUM_GREY

    box_h = Inches(0.65) if subtitle else Inches(0.45)
    txbox = slide.shapes.add_textbox(LEFT_MARGIN, Inches(0.35), CONTENT_W, box_h)
    tf = txbox.text_frame
    tf.word_wrap = True
    tf.margin_bottom = Pt(0)
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = title_color
    p.font.name = TITLE_FONT
    p.space_after = Pt(2)

    if subtitle:
        p2 = tf.add_paragraph()
        p2.text = subtitle
        p2.font.size = Pt(10)
        p2.font.color.rgb = subtitle_color
        p2.font.name = BODY_FONT
        p2.space_before = Pt(2)
        p2.space_after = Pt(0)


def _add_textbox(slide, text, left, top, width, height, size=11, color=None,
                 bold=False, italic=False, font_name="Inter", align=None):
    """Add a styled text box."""
    if color is None:
        color = SLATE
    txbox = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = txbox.text_frame
    tf.word_wrap = True
    tf.margin_left = Pt(10)
    tf.margin_right = Pt(10)
    tf.margin_top = Pt(10)
    tf.margin_bottom = Pt(10)
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(size)
    p.font.color.rgb = color
    p.font.bold = bold
    p.font.italic = italic
    p.font.name = font_name
    if align:
        p.alignment = align
    return tf


def _add_image(slide, image_path, left, top, width=None, height=None):
    """Add an image to the slide if the file exists."""
    if image_path and Path(image_path).exists():
        kwargs = {"image_file": str(image_path), "left": Inches(left), "top": Inches(top)}
        if width:
            kwargs["width"] = Inches(width)
        if height:
            kwargs["height"] = Inches(height)
        slide.shapes.add_picture(**kwargs)
        return True
    return False


def _add_badge(slide, text, x, y, bg_color, text_color=None, width=0.9):
    """Add a colored pill badge (rounded rectangle with text)."""
    if text_color is None:
        text_color = WHITE
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(x), Inches(y), Inches(width), Inches(0.25)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = bg_color
    shape.line.fill.background()
    shape.adjustments[0] = 0.5  # Maximum rounding
    tf = shape.text_frame
    tf.word_wrap = False
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = text
    run.font.size = Pt(8)
    run.font.bold = True
    run.font.name = BODY_FONT
    run.font.color.rgb = text_color
    tf.margin_top = Pt(4)
    tf.margin_bottom = Pt(4)
    return shape


def _add_table(slide, headers, rows, left, top, width, row_height=0.38, col_widths=None):
    """Add a clean data table with navy header and alternating rows."""
    from lxml import etree
    cols = len(headers)
    n_rows = len(rows) + 1

    table_shape = slide.shapes.add_table(
        n_rows, cols, Inches(left), Inches(top),
        Inches(width), Inches(row_height * n_rows)
    )
    table = table_shape.table

    # Disable default table style
    tbl = table._tbl
    tblPr = tbl.find('.//{http://schemas.openxmlformats.org/drawingml/2006/main}tblPr')
    if tblPr is not None:
        styleEl = tblPr.find('{http://schemas.openxmlformats.org/drawingml/2006/main}tableStyleId')
        if styleEl is not None:
            tblPr.remove(styleEl)
        for attr in ['firstRow', 'lastRow', 'firstCol', 'lastCol', 'bandRow', 'bandCol']:
            tblPr.set(attr, '0')

    if col_widths:
        for i, cw in enumerate(col_widths):
            table.columns[i].width = Inches(cw)

    # Header row
    for i, header in enumerate(headers):
        cell = table.cell(0, i)
        cell.text_frame.paragraphs[0].text = header
        cell.text_frame.paragraphs[0].font.size = Pt(11)
        cell.text_frame.paragraphs[0].font.bold = True
        cell.text_frame.paragraphs[0].font.color.rgb = WHITE
        cell.text_frame.paragraphs[0].font.name = TITLE_FONT
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY

    # Data rows
    for r, row in enumerate(rows):
        bg = ALT_ROW if r % 2 == 0 else WHITE
        for c, val in enumerate(row):
            cell = table.cell(r + 1, c)
            cell.text_frame.paragraphs[0].text = str(val)
            cell.text_frame.paragraphs[0].font.size = Pt(10)
            cell.text_frame.paragraphs[0].font.color.rgb = SLATE
            cell.text_frame.paragraphs[0].font.name = BODY_FONT
            cell.fill.solid()
            cell.fill.fore_color.rgb = bg

    return table


def _add_number_circle(slide, number, x, y, size=0.38, bg_color=None):
    """Add a numbered circle (oval shape with centered number)."""
    if bg_color is None:
        bg_color = NAVY
    shape = slide.shapes.add_shape(
        MSO_SHAPE.OVAL,
        Inches(x), Inches(y), Inches(size), Inches(size)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = bg_color
    shape.line.fill.background()
    tf = shape.text_frame
    tf.word_wrap = False
    tf.margin_left = Pt(0)
    tf.margin_right = Pt(0)
    tf.margin_top = Pt(0)
    tf.margin_bottom = Pt(0)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = str(number)
    run.font.size = Pt(14)
    run.font.bold = True
    run.font.name = TITLE_FONT
    run.font.color.rgb = WHITE
    return shape


def _add_card_row(slide, x, y, width, height, border_color=None, bg_color=None):
    """Add a card-style row with subtle background and optional left border.

    Returns the background shape so content can be layered on top.
    """
    if bg_color is None:
        bg_color = GREY_100
    # Background rectangle
    bg_shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(x), Inches(y), Inches(width), Inches(height)
    )
    bg_shape.fill.solid()
    bg_shape.fill.fore_color.rgb = bg_color
    bg_shape.line.fill.background()

    # Left border accent (thin vertical bar)
    if border_color:
        border = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(x), Inches(y), Inches(0.06), Inches(height)
        )
        border.fill.solid()
        border.fill.fore_color.rgb = border_color
        border.line.fill.background()

    return bg_shape


def _add_metric_bar(slide, metrics, y, dark=False):
    """Add a row of metric callout bars (large value + small uppercase label).

    metrics: list of (value_str, label_str, color) tuples.
    Distributes evenly across content width.
    """
    n = len(metrics)
    bar_w = 11.7 / n
    for i, (value, label, color) in enumerate(metrics):
        x = 0.8 + i * bar_w
        # Value
        _add_textbox(slide, value, x, y, bar_w - 0.2, 0.55,
                     size=36, color=color, bold=True, font_name=TITLE_FONT)
        # Label
        label_color = RGBColor(0x94, 0xA3, 0xB8) if dark else MEDIUM_GREY
        _add_textbox(slide, label.upper(), x, y + 0.55, bar_w - 0.2, 0.25,
                     size=9, color=label_color, bold=True, font_name=TITLE_FONT)


def _confidence_label(tier):
    if tier == ConfidenceTier.HIGH:
        return "HIGH"
    elif tier == ConfidenceTier.MEDIUM:
        return "MEDIUM"
    elif tier == ConfidenceTier.DIRECTIONAL:
        return "DIRECTIONAL"
    return "INSUFFICIENT"


def _signal_label(tier):
    if tier == SignalStrengthTier.STRONG:
        return "STRONG"
    elif tier == SignalStrengthTier.MODERATE:
        return "MODERATE"
    elif tier == SignalStrengthTier.WEAK:
        return "WEAK"
    return "TRACE"


def _quadrant_border_color(quadrant):
    """Return the left-border accent color for a matrix quadrant."""
    return QUADRANT_COLORS.get(quadrant, MEDIUM_GREY)


# ---- SECTION A: FOUNDATION ----

# ---- SECTION A: FOUNDATION ----

def _slide_cover(prs, config, run_dir):
    """Cover page -- dark navy background."""
    slide = _dark_slide(prs)

    # Brand name -- large hero text
    _add_textbox(slide, config.collection.brand_name, 0.8, 1.8, 11, 1.2,
                 size=48, color=WHITE, bold=True, font_name=TITLE_FONT)

    # Subtitle
    _add_textbox(slide, "Consumer Research Report", 0.8, 3.0, 11, 0.5,
                 size=18, color=RGBColor(0x94, 0xA3, 0xB8), font_name=BODY_FONT)

    # Objectives as bullets (merged from old objectives slide)
    objectives = config.collection.business_objectives or [
        "Understand consumer perception of the brand",
        "Identify key consumption occasions and drivers",
        "Assess competitive positioning",
        "Surface emerging trends and concerns",
    ]
    obj_y = 3.8
    for i, obj in enumerate(objectives):
        _add_textbox(slide, f"  {obj}", 0.8, obj_y + i * 0.38, 10, 0.35,
                     size=11, color=RGBColor(0x94, 0xA3, 0xB8), font_name=BODY_FONT)

    # Meta info at bottom
    meta_lines = [
        f"{config.collection.category}  |  Last {config.collection.time_period_days} days  |  "
        f"{datetime.now().strftime('%B %d, %Y')}  |  {run_dir.name}"
    ]
    _add_textbox(slide, meta_lines[0], 0.8, 6.4, 11, 0.4,
                 size=9, color=MEDIUM_GREY, font_name=BODY_FONT)


def _slide_objectives(prs, config):
    """Business Objectives & Research Questions."""
    slide = _add_slide(prs)
    _add_header(slide, "Business Objectives & Research Questions")

    objectives = config.collection.business_objectives or [
        "Understand consumer perception of the brand",
        "Identify key consumption occasions and drivers",
        "Assess competitive positioning",
        "Surface emerging trends and concerns",
    ]

    tf = _add_textbox(slide, "", 0.8, 1.4, 11, 5, size=13)
    for i, obj in enumerate(objectives):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = f"{i + 1}.  {obj}"
        p.font.size = Pt(14)
        p.font.color.rgb = NAVY
        p.font.bold = True
        p.font.name = TITLE_FONT
        if i > 0:
            p.space_before = Pt(12)
            p.space_after = Pt(0)


def _slide_methodology_overview(prs, config, analysis, items, platform_counts):
    """Methodology overview — data sources, analysis methods, quality gates."""
    slide = _add_slide(prs)
    _add_header(slide, "Methodology")

    sources_text = "  |  ".join(f"{p.capitalize()}: {c} items" for p, c in platform_counts.items())
    n_insights = len(analysis.themes)
    sections = [
        ("DATA SOURCES", sources_text),
        ("ANALYSIS", f"{analysis.analysis_model}  |  temperature=0  |  deterministic"),
        ("SENTIMENT", "4-class sentiment  |  Plutchik 8-emotion wheel  |  Aspect-level sentiment (per product attribute, n\u226510 threshold)  |  Net Sentiment Score (NSS)"),
        ("THEMES \u2192 INSIGHTS", f"Two-pass theme extraction (300-item sample \u2192 full corpus mapping)  |  One insight per theme ({n_insights} themes)  |  5 quality gates per insight"),
        ("SCORING", "Confidence (5 factors) \u00d7 Signal Strength (4 factors)  |  Insights Matrix quadrant classification  |  Wilson score 95% confidence intervals"),
        ("QUALITY GATES", "Grounded (\u22653 sources)  |  Non-obvious  |  Actionable  |  Specific  |  Falsifiable"),
    ]
    left_tf = _add_textbox(slide, "", 0.8, 1.45, 6.2, 5.7, size=11)
    first = True
    for label, content in sections:
        if not first:
            p = left_tf.add_paragraph()
            p.text = ""
            p.space_before = Pt(12)
            p.space_after = Pt(0)
        p_label = left_tf.paragraphs[0] if first else left_tf.add_paragraph()
        p_label.text = label
        p_label.font.size = Pt(11)
        p_label.font.bold = True
        p_label.font.color.rgb = NAVY
        p_label.font.name = TITLE_FONT
        p_content = left_tf.add_paragraph()
        p_content.text = content
        p_content.font.size = Pt(11)
        p_content.font.color.rgb = SLATE
        p_content.font.name = BODY_FONT
        first = False

    # Right column — caveat box
    caveat_tf = _add_textbox(slide, "", 7.3, 1.45, 5.4, 5.7, size=11, italic=True, color=MEDIUM_GREY)
    caveat_tf.paragraphs[0].text = (
        "Scope & Limitations\n\n"
        "This report analyzes a convenience sample of publicly available online discussions. "
        "Findings are directional \u2014 they indicate patterns in online discourse but cannot be "
        "extrapolated to the general consumer population.\n\n"
        "Demographics of contributors are unknown. Platform audiences differ significantly "
        "(Reddit vs. YouTube vs. News). Organic discussions may over-represent strong opinions "
        "relative to the silent majority.\n\n"
        f"Collection period: last {config.collection.time_period_days} days.  "
        f"Total items analyzed: {len(items)}."
    )
    for para in caveat_tf.paragraphs:
        para.font.size = Pt(11)
        para.font.italic = True
        para.font.color.rgb = MEDIUM_GREY
        para.font.name = BODY_FONT


def _slide_data_universe(prs, items, analysis, scored_insights, platform_counts, charts):
    """Slide 2: Data Universe -- white bg, 4 hero stats, platform chart + table."""
    slide = _add_slide(prs)
    _add_header(slide, "Data Universe",
                f"{len(items):,} items collected across {len(platform_counts)} platforms")

    # 4 hero stats at top
    stats = [
        (f"{len(items):,}", "Items Analyzed", NAVY),
        (str(len(analysis.themes)), "Themes Identified", NAVY),
        (str(len(scored_insights)), "Insights Scored", NAVY),
        (str(sum(1 for s in scored_insights if s.confidence_tier == ConfidenceTier.HIGH)),
         "High Confidence", GREEN),
    ]
    _add_metric_bar(slide, stats, 1.25)

    # Platform chart -- left
    _add_image(slide, charts.get("platforms"), 0.8, 2.4, width=7.0)

    # Platform table -- right
    headers = ["Platform", "Items", "% of Corpus"]
    total = len(items)
    rows = [[p.capitalize(), f"{c:,}", f"{c / total * 100:.1f}%"]
            for p, c in sorted(platform_counts.items(), key=lambda x: -x[1])]
    if rows:
        _add_table(slide, headers, rows, 8.3, 2.4, 4.5, row_height=0.45)


def _slide_executive_summary(prs, scored_insights, analysis=None):
    """Slide 3: Executive Summary -- dark navy bg, metric bar + card rows."""
    slide = _dark_slide(prs)

    # Title
    nss = getattr(analysis, "net_sentiment_score", None) if analysis else None
    brand_health = getattr(analysis, "brand_health_score", None) if analysis else None
    if brand_health is not None and nss is not None:
        exec_title = f"Brand health is {brand_health}/100 with {nss:+.0%} net sentiment"
    elif nss is not None:
        exec_title = f"Executive Summary  --  Net sentiment {nss:+.0%}"
    else:
        exec_title = "Executive Summary"
    _add_header(slide, exec_title, "If you read only one slide, read this one.", dark=True)

    # Metric bar: NSS, themes, key findings, items analyzed
    nss_pct = f"{nss * 100:+.0f}%" if nss is not None else "N/A"
    nss_color = GREEN if (nss is not None and nss >= 0) else RED if nss is not None else MEDIUM_GREY
    key_finding_count = sum(1 for s in scored_insights if s.matrix_quadrant == MatrixQuadrant.KEY_FINDING)
    theme_count = len(analysis.themes) if analysis else 0
    total_items = analysis.total_items_analyzed if analysis else 0

    metrics = [
        (nss_pct, "Net Sentiment", nss_color),
        (str(theme_count), "Themes", WHITE),
        (str(key_finding_count), "Key Findings", WHITE),
        (f"{total_items:,}", "Items Analyzed", WHITE),
    ]
    _add_metric_bar(slide, metrics, 1.20, dark=True)

    # Top 5 findings as card rows with number circles + confidence badges
    card_y = 2.3
    card_h = 0.92
    card_gap = 0.12

    for i, scored in enumerate(scored_insights[:5]):
        y = card_y + i * (card_h + card_gap)
        border_color = _quadrant_border_color(scored.matrix_quadrant)

        # Card background (dark navy-light)
        _add_card_row(slide, 0.8, y, 11.7, card_h,
                      border_color=border_color,
                      bg_color=NAVY_LIGHT)

        # Number circle
        _add_number_circle(slide, i + 1, 1.0, y + 0.27, size=0.38, bg_color=border_color)

        # Observation text
        _add_textbox(slide, scored.insight.observation[:280], 1.55, y + 0.05, 7.8, 0.50,
                     size=11, color=WHITE, bold=True, font_name=TITLE_FONT)

        # Recommendation (italic, smaller)
        _add_textbox(slide, scored.insight.recommendation[:200], 1.55, y + 0.52, 7.8, 0.35,
                     size=9, color=RGBColor(0x94, 0xA3, 0xB8), italic=True, font_name=BODY_FONT)

        # Confidence badge
        conf_label = _confidence_label(scored.confidence_tier)
        badge_color = CONFIDENCE_BADGE_COLORS.get(scored.confidence_tier, MEDIUM_GREY)
        _add_badge(slide, conf_label, 9.7, y + 0.12, badge_color, width=1.1)

        # Quadrant badge
        _add_badge(slide, scored.matrix_quadrant.value, 9.7, y + 0.48,
                   _quadrant_border_color(scored.matrix_quadrant), width=1.3)


# ---- SECTION B: ANALYSIS ----

def _slide_sentiment_emotion(prs, analysis, items, charts):
    """Slide 4: Sentiment + Emotion merged -- white bg.

    Left: sentiment chart + NSS callout.
    Right: emotion distribution.
    """
    slide = _add_slide(prs)

    # Data-driven action title
    nss_val = getattr(analysis, "net_sentiment_score", None)
    if nss_val is not None and analysis.overall_sentiment:
        dominant_sentiment = max(analysis.overall_sentiment, key=analysis.overall_sentiment.get)
        action_title = f"Net sentiment is {nss_val:+.0%}, driven by {dominant_sentiment} responses"
    else:
        action_title = "Sentiment & Emotional Profile"
    _add_header(slide, action_title,
                "4-class sentiment + Plutchik 8 primary emotions")

    # LEFT: Sentiment chart
    _add_image(slide, charts.get("sentiment"), 0.8, 1.35, width=6.0)

    # NSS hero callout below chart
    nss = getattr(analysis, "net_sentiment_score", None)
    if nss is not None:
        nss_pct = nss * 100
        nss_text = f"{nss_pct:+.0f}%"
        nss_color = GREEN if nss >= 0 else RED
        _add_textbox(slide, nss_text, 0.8, 5.2, 2.0, 0.55,
                     size=36, color=nss_color, bold=True, font_name=TITLE_FONT)
        _add_textbox(slide, "NET SENTIMENT SCORE", 0.8, 5.75, 3.0, 0.25,
                     size=9, color=MEDIUM_GREY, bold=True, font_name=TITLE_FONT)

    # Sentiment breakdown stats (below NSS)
    total = len(items)
    color_map = {"positive": GREEN, "negative": RED, "neutral": MEDIUM_GREY, "mixed": AMBER}
    stat_x = 3.5
    for sent, count in sorted(analysis.overall_sentiment.items(), key=lambda x: -x[1]):
        pct = count / total * 100 if total > 0 else 0
        _add_textbox(slide, f"{sent.capitalize()}: {count:,} ({pct:.0f}%)",
                     stat_x, 5.35, 2.5, 0.25,
                     size=10, color=color_map.get(sent, SLATE), bold=True, font_name=BODY_FONT)
        stat_x += 2.3

    # RIGHT: Emotion chart
    emotion_chart = charts.get("emotions")
    if emotion_chart and Path(emotion_chart).exists():
        _add_image(slide, emotion_chart, 7.2, 1.35, width=5.5)

    # Emotion stats below chart
    emotion_dist = getattr(analysis, "emotion_distribution", None) or {}
    if emotion_dist:
        total_emotions = sum(emotion_dist.values()) or 1
        sorted_emotions = sorted(emotion_dist.items(), key=lambda x: -x[1])
        emo_y = 5.2
        col = 0
        for idx, (emotion, count) in enumerate(sorted_emotions[:8]):
            pct = count / total_emotions * 100
            x = 7.2 + (col * 3.0)
            row = idx // 2
            _add_textbox(slide, f"{emotion.capitalize()}: {pct:.0f}%",
                         x, emo_y + row * 0.28, 2.8, 0.25,
                         size=9, color=NAVY, bold=True, font_name=BODY_FONT)
            col = 1 - col  # alternate columns

    # Caveat
    _add_textbox(slide, f"n = {total:,}. Convenience sample -- interpret as directional.",
                 0.8, 6.9, 11.7, 0.25,
                 size=8, color=MEDIUM_GREY, italic=True, font_name=BODY_FONT)


def _slide_emotional_profile(prs, analysis, charts):
    """Emotional Profile — Plutchik 8 primary emotions from consumer discussions."""
    emotion_chart = charts.get("emotions")
    if not emotion_chart or not Path(emotion_chart).exists():
        return  # Skip if no emotion chart

    slide = _add_slide(prs)
    _add_header(slide, "Emotional Profile",
                "Plutchik\u2019s 8 primary emotions identified in consumer discussions")

    # Emotion chart — left side
    _add_image(slide, emotion_chart, 0.8, 1.35, width=8.0)

    # Emotion breakdown on the right
    emotion_dist = getattr(analysis, "emotion_distribution", None) or {}
    if emotion_dist:
        total_emotions = sum(emotion_dist.values()) or 1
        tf = _add_textbox(slide, "", 9.2, 1.5, 3.6, 5.5, size=11)
        first = True
        for emotion, count in sorted(emotion_dist.items(), key=lambda x: -x[1]):
            pct = count / total_emotions * 100
            p = tf.paragraphs[0] if first else tf.add_paragraph()
            p.text = emotion.capitalize()
            p.font.size = Pt(11)
            p.font.bold = True
            p.font.color.rgb = NAVY
            p.font.name = TITLE_FONT
            if not first:
                p.space_before = Pt(12)
                p.space_after = Pt(0)
            p2 = tf.add_paragraph()
            p2.text = f"{count:,} items  ({pct:.1f}%)"
            p2.font.size = Pt(8)
            p2.font.color.rgb = SLATE
            p2.font.name = BODY_FONT
            first = False


def _slide_aspect_sentiment(prs, analysis, charts):
    """Aspect-Level Sentiment -- white bg, heatmap + top 5 aspects.

    Skipped entirely if no aspects with n>=10.
    """
    aspect_summary = getattr(analysis, "aspect_sentiment_summary", None) or {}
    # Filter to aspects with n>=10
    qualified_aspects = []
    for aspect, counts in aspect_summary.items():
        pos = counts.get("positive", 0)
        neg = counts.get("negative", 0)
        neu = counts.get("neutral", 0)
        mix = counts.get("mixed", 0)
        total = pos + neg + neu + mix
        if total >= 10:
            nss_val = (pos - neg) / total
            qualified_aspects.append((aspect, nss_val, total, pos, neg, neu, mix))

    if not qualified_aspects:
        return  # Skip slide entirely

    qualified_aspects.sort(key=lambda x: -x[2])  # Sort by sample size

    slide = _add_slide(prs)
    top_aspect = qualified_aspects[0]
    action_title = (f"{top_aspect[0].replace('_', ' ').title()} is the most discussed aspect "
                    f"with {top_aspect[1]:+.0%} NSS")
    _add_header(slide, action_title, "Net sentiment by product/brand aspect (n >= 10 only)")

    # Heatmap chart -- left
    heatmap_chart = charts.get("aspect_heatmap")
    _add_image(slide, heatmap_chart, 0.8, 1.35, width=7.0)

    # Right panel -- top 5 aspects as card rows
    _add_textbox(slide, "TOP ASPECTS BY DISCUSSION VOLUME", 8.2, 1.35, 4.5, 0.3,
                 size=10, color=NAVY, bold=True, font_name=TITLE_FONT)

    for idx, (aspect, nss_val, total, pos, neg, neu, mix) in enumerate(qualified_aspects[:5]):
        y = 1.85 + idx * 0.95
        nss_color = GREEN if nss_val >= 0 else RED

        # Card background
        _add_card_row(slide, 8.2, y, 4.5, 0.82, border_color=nss_color, bg_color=GREY_100)

        # Aspect name
        _add_textbox(slide, aspect.replace("_", " ").title(), 8.45, y + 0.05, 2.5, 0.3,
                     size=12, color=SLATE, bold=True, font_name=TITLE_FONT)

        # NSS value
        _add_textbox(slide, f"{nss_val * 100:+.0f}%", 11.2, y + 0.05, 1.3, 0.3,
                     size=18, color=nss_color, bold=True, font_name=TITLE_FONT)

        # Breakdown line
        _add_textbox(slide, f"n={total}  |  +{pos} -{neg} ~{neu}",
                     8.45, y + 0.45, 4.0, 0.25,
                     size=8, color=MEDIUM_GREY, font_name=BODY_FONT)


def _slide_themes_overview(prs, analysis, charts):
    """Slide 6: Themes Overview -- white bg, theme chart + table."""
    slide = _add_slide(prs)
    if analysis.themes:
        lead_theme = analysis.themes[0]
        action_title = (f"{len(analysis.themes)} themes identified, "
                        f"led by {lead_theme.theme_label} at {lead_theme.prevalence_pct:.1f}%")
    else:
        action_title = "Key Themes"
    _add_header(slide, action_title,
                f"{len(analysis.themes)} themes extracted from consumer discussions")

    # Theme chart -- left
    _add_image(slide, charts.get("themes"), 0.8, 1.35, width=6.0)

    # Theme table -- right
    headers = ["Theme", "Items", "%", "NSS", "Multi"]
    rows = []
    for t in analysis.themes:
        nss_val = getattr(t, "net_sentiment_score", 0)
        rows.append([
            t.theme_label[:50],
            str(t.item_count),
            f"{t.prevalence_pct:.1f}%",
            f"{nss_val:+.0%}" if nss_val else "0%",
            "Yes" if t.is_multi_source else "No",
        ])
    if rows:
        _add_table(slide, headers, rows, 7.0, 1.35, 6.1,
                   row_height=0.34,
                   col_widths=[3.2, 0.55, 0.55, 0.65, 0.55])


# ---- SECTION C: KEY INSIGHTS ----

def _slide_insight_deep_dive(prs, scored, index, charts):
    """Slides 7-9: Insight deep dive -- white bg, one per top insight.

    Left column: OBSERVATION -> INSIGHT -> SO WHAT -> NOW WHAT
    Right: radar chart + supporting data.
    """
    slide = _add_slide(prs)
    _add_header(slide, f"Insight {scored.insight.insight_id}",
                f"{scored.matrix_quadrant.value}  |  "
                f"Confidence: {scored.confidence_score:.2f}  |  "
                f"Signal: {scored.signal_strength_score:.2f}")

    # Left column sections
    sections = [
        ("OBSERVATION", scored.insight.observation[:400], SLATE),
        ("INSIGHT", scored.insight.insight[:400], NAVY),
        ("SO WHAT", scored.insight.implication[:400], LIGHT_SLATE),
        ("NOW WHAT", scored.insight.recommendation[:400], NAVY),
    ]

    y = 1.40
    for label, text, color in sections:
        # Section label
        _add_textbox(slide, label, 0.8, y, 7.0, 0.25,
                     size=10, color=NAVY, bold=True, font_name=TITLE_FONT)
        y += 0.28
        # Content text
        _add_textbox(slide, text, 0.8, y, 7.0, 0.85,
                     size=11, color=color, font_name=BODY_FONT)
        y += 0.95

    # Right column: Radar chart
    radar_path = charts.get(f"radar_{index}")
    _add_image(slide, radar_path, 8.0, 1.35, width=5.0)

    # Supporting data box
    support_y = 5.5
    _add_card_row(slide, 8.0, support_y, 4.8, 1.4, bg_color=GREY_100)
    _add_textbox(slide, f"n = {scored.sample_size} items", 8.2, support_y + 0.1, 4.4, 0.25,
                 size=9, color=SLATE, bold=True, font_name=BODY_FONT)

    if scored.confidence_interval_95:
        ci = scored.confidence_interval_95
        _add_textbox(slide, f"95% CI: [{ci[0]:.1%}, {ci[1]:.1%}]",
                     8.2, support_y + 0.38, 4.4, 0.25,
                     size=9, color=MEDIUM_GREY, font_name=BODY_FONT)

    _add_textbox(slide, f"Sources: {len(scored.insight.source_urls)} URLs",
                 8.2, support_y + 0.65, 4.4, 0.25,
                 size=9, color=MEDIUM_GREY, font_name=BODY_FONT)

    # Further validation
    if scored.insight.further_validation:
        _add_textbox(slide, f"Validate: {scored.insight.further_validation[:200]}",
                     8.2, support_y + 0.92, 4.4, 0.35,
                     size=8, color=MEDIUM_GREY, italic=True, font_name=BODY_FONT)


# ---- SECTION D: STRATEGIC FRAMEWORK ----

def _slide_matrix(prs, scored_insights, charts):
    """Slide 10: Insights Matrix (2x2 scatter plot) -- white bg."""
    slide = _add_slide(prs)
    key_finding_count = sum(1 for s in scored_insights if s.matrix_quadrant == MatrixQuadrant.KEY_FINDING)
    total = len(scored_insights)
    action_title = f"{key_finding_count} of {total} insights are Key Findings"
    _add_header(slide, action_title,
                "Both axes computed from data. No LLM opinion on business feasibility.")

    # Matrix chart
    _add_image(slide, charts.get("matrix"), 0.8, 1.35, width=7.0)

    # Legend table on right
    headers = ["Insight", "Conf.", "Signal", "Quadrant"]
    rows = [
        [s.insight.insight_id,
         f"{s.confidence_score:.2f}",
         f"{s.signal_strength_score:.2f}",
         s.matrix_quadrant.value]
        for s in scored_insights
    ]
    if rows:
        _add_table(slide, headers, rows, 8.3, 1.35, 4.5,
                   row_height=0.34,
                   col_widths=[1.4, 0.7, 0.7, 1.3])


def _slide_recommendations(prs, scored_insights):
    """Slide 11: Strategic Recommendations -- white bg, paginated 5 per slide.

    Each recommendation as a numbered card row.
    """
    key_findings = [s for s in scored_insights if s.matrix_quadrant == MatrixQuadrant.KEY_FINDING]
    if not key_findings:
        key_findings = scored_insights[:5]

    per_page = 5
    for page_start in range(0, len(key_findings), per_page):
        page_items = key_findings[page_start:page_start + per_page]
        page_num = page_start // per_page + 1
        total_pages = (len(key_findings) + per_page - 1) // per_page
        subtitle = "Derived from Key Finding insights -- high confidence + strong signal"
        if total_pages > 1:
            subtitle += f"  --  Page {page_num} of {total_pages}"

        slide = _add_slide(prs)
        _add_header(slide, "Strategic Recommendations", subtitle)

        card_y = 1.30
        card_h = 1.05
        card_gap = 0.12

        for i, scored in enumerate(page_items):
            y = card_y + i * (card_h + card_gap)
            border_color = _quadrant_border_color(scored.matrix_quadrant)

            # Card background
            _add_card_row(slide, 0.8, y, 11.7, card_h,
                          border_color=border_color, bg_color=GREY_100)

            # Number circle
            _add_number_circle(slide, page_start + i + 1, 1.0, y + 0.33,
                               size=0.38, bg_color=border_color)

            # Recommendation text
            _add_textbox(slide, scored.insight.recommendation[:300],
                         1.55, y + 0.08, 8.5, 0.45,
                         size=12, color=NAVY, bold=True, font_name=TITLE_FONT)

            # Basis (observation)
            _add_textbox(slide, f"Based on: {scored.insight.observation[:250]}",
                         1.55, y + 0.55, 8.5, 0.35,
                         size=9, color=LIGHT_SLATE, italic=True, font_name=BODY_FONT)

            # Confidence + signal badges on right
            conf_label = _confidence_label(scored.confidence_tier)
            badge_color = CONFIDENCE_BADGE_COLORS.get(scored.confidence_tier, MEDIUM_GREY)
            _add_badge(slide, conf_label, 10.5, y + 0.15, badge_color, width=1.1)

            sig_label = _signal_label(scored.signal_strength_tier)
            _add_badge(slide, sig_label, 10.5, y + 0.50, NAVY_LIGHT, width=1.1)


def _slide_further_research(prs, scored_insights):
    """Further Research Agenda — paginated if needed."""
    items_with_validation = [s for s in scored_insights if s.insight.further_validation]
    per_page = 5
    for page_start in range(0, max(len(items_with_validation), 1), per_page):
        page_items = items_with_validation[page_start:page_start + per_page]
        total_pages = (len(items_with_validation) + per_page - 1) // per_page
        subtitle = "What additional research would strengthen these findings"
        if total_pages > 1:
            page_num = page_start // per_page + 1
            subtitle += f"  \u2014  Page {page_num} of {total_pages}"

        slide = _add_slide(prs)
        _add_header(slide, "Further Research Agenda", subtitle)

        tf = _add_textbox(slide, "", 0.8, 1.5, 11.5, 5.5, size=11)
        first = True
        for scored in page_items:
            if not first:
                p = tf.add_paragraph()
                p.text = ""
                p.space_before = Pt(12)
                p.space_after = Pt(0)
            p_id = tf.paragraphs[0] if first else tf.add_paragraph()
            p_id.text = f"{scored.insight.insight_id}  ({scored.matrix_quadrant.value})"
            p_id.font.size = Pt(11)
            p_id.font.bold = True
            p_id.font.color.rgb = NAVY
            p_id.font.name = TITLE_FONT
            p_val = tf.add_paragraph()
            p_val.text = f"  {scored.insight.further_validation[:300]}"
            p_val.font.size = Pt(11)
            p_val.font.color.rgb = SLATE
            p_val.font.name = BODY_FONT
            first = False


def _slide_risk_limitations(prs, config, analysis):
    """Slide 12: Risk Factors + Limitations combined -- white bg."""
    slide = _add_slide(prs)
    _add_header(slide, "Risk Factors & Limitations",
                "Important caveats for interpreting this research")

    risks = [
        ("SAMPLING BIAS",
         "Convenience sample of online discussions -- not representative of the general population. "
         "Demographics of contributors are unknown."),
        ("PLATFORM BIAS",
         "Each platform attracts different demographics and discussion styles. "
         "Reddit skews younger/male, YouTube varies by content type, news reflects editorial choices."),
        ("GEOGRAPHIC SCOPE",
         f"Coverage limited to regions where the brand is discussed online. "
         f"Time period: last {config.collection.time_period_days} days."),
        ("OPINION AMPLIFICATION",
         "Organic online discussions may over-index on complaints and strong opinions "
         "relative to the silent majority."),
    ]

    single_source = sum(1 for t in analysis.themes if not t.is_multi_source)
    if single_source:
        risks.append((
            "SINGLE-SOURCE THEMES",
            f"{single_source} of {len(analysis.themes)} themes based on a single platform "
            f"-- no cross-validation available for these findings."
        ))

    card_y = 1.30
    card_h = 0.85
    card_gap = 0.10

    for i, (label, text) in enumerate(risks):
        y = card_y + i * (card_h + card_gap)

        # Card background with amber left border (warning color)
        _add_card_row(slide, 0.8, y, 11.7, card_h,
                      border_color=AMBER, bg_color=GREY_100)

        # Risk label
        _add_textbox(slide, label, 1.05, y + 0.08, 11.2, 0.25,
                     size=10, color=AMBER, bold=True, font_name=TITLE_FONT)

        # Risk description
        _add_textbox(slide, text, 1.05, y + 0.35, 11.2, 0.42,
                     size=10, color=SLATE, font_name=BODY_FONT)


# ---- SECTION E: APPENDIX ----

def _slide_methodology(prs, config, analysis, items, platform_counts):
    """Slide 13: Methodology -- single slide, overview + scoring combined."""
    slide = _add_slide(prs)
    _add_header(slide, "Methodology",
                "How raw data becomes scored insights -- fully transparent and reproducible")

    sources_text = "  |  ".join(f"{p.capitalize()}: {c}" for p, c in platform_counts.items())

    # Left column -- methodology details
    sections_left = [
        ("DATA SOURCES", sources_text),
        ("ANALYSIS MODEL", f"{analysis.analysis_model}  |  temperature=0  |  deterministic"),
        ("SENTIMENT", "4-class sentiment + Plutchik 8 emotions + ABSA (per-aspect, n>=10) + NSS"),
        ("THEME EXTRACTION", "Two-pass: 300-item sample discovers themes, then full corpus mapping in batches of 30"),
        ("INSIGHT SYNTHESIS", f"One insight per theme ({len(analysis.themes)} themes). "
         "Framework: Observation -> Insight -> Implication -> Recommendation -> Further Validation"),
    ]

    left_tf = _add_textbox(slide, "", 0.8, 1.35, 5.8, 5.8, size=11)
    first = True
    for label, content in sections_left:
        if not first:
            p = left_tf.add_paragraph()
            p.text = ""
            p.space_before = Pt(8)
            p.space_after = Pt(0)

        p_label = left_tf.paragraphs[0] if first else left_tf.add_paragraph()
        p_label.text = label
        p_label.font.size = Pt(10)
        p_label.font.bold = True
        p_label.font.color.rgb = NAVY
        p_label.font.name = TITLE_FONT

        p_content = left_tf.add_paragraph()
        p_content.text = content
        p_content.font.size = Pt(10)
        p_content.font.color.rgb = SLATE
        p_content.font.name = BODY_FONT
        first = False

    # Right column -- scoring formulas + quality gates
    sections_right = [
        ("CONFIDENCE SCORE", "Sample Size (0.25) + Source Diversity (0.25) + "
         "Temporal Consistency (0.15) + Internal Agreement (0.20) + Data Recency (0.15)"),
        ("SIGNAL STRENGTH", "Prevalence (0.35) + Engagement Level (0.30) + "
         "Sentiment Intensity (0.20) + Conversation Depth (0.15)"),
        ("INSIGHTS MATRIX", "High conf + Strong signal = Key Finding | "
         "High + Weak = Emerging Trend | Low + Strong = Watch Closely | Low + Low = Noise"),
        ("QUALITY GATES", "Grounded (>=3 sources) | Non-obvious | Actionable | Specific | Falsifiable"),
        ("SCOPE NOTE", f"Convenience sample. Last {config.collection.time_period_days} days. "
         f"{len(items):,} items. Platform audiences differ. Interpret as directional."),
    ]

    right_tf = _add_textbox(slide, "", 6.9, 1.35, 5.8, 5.8, size=11)
    first = True
    for label, content in sections_right:
        if not first:
            p = right_tf.add_paragraph()
            p.text = ""
            p.space_before = Pt(8)
            p.space_after = Pt(0)

        p_label = right_tf.paragraphs[0] if first else right_tf.add_paragraph()
        p_label.text = label
        p_label.font.size = Pt(10)
        p_label.font.bold = True
        p_label.font.color.rgb = NAVY
        p_label.font.name = TITLE_FONT

        p_content = right_tf.add_paragraph()
        p_content.text = content
        p_content.font.size = Pt(10)
        p_content.font.color.rgb = SLATE
        p_content.font.name = BODY_FONT
        first = False


def _slide_scoring_breakdown(prs, scored_insights):
    """Slide 14: Full Scoring Breakdown -- TWO tables side by side on ONE slide.

    Confidence table (left), Signal Strength table (right).
    Uses 9pt font and 0.30 row height to fit all rows.
    """
    slide = _add_slide(prs)
    _add_header(slide, "Scoring Breakdown",
                "All scores computed from data -- fully transparent")

    row_h = 0.30

    # LEFT: Confidence table
    conf_headers = ["Insight", "Sample", "Src Div", "Temporal", "Agree.", "Recency", "Conf."]
    conf_rows = []
    for s in scored_insights:
        cb = s.confidence_breakdown
        conf_rows.append([
            s.insight.insight_id,
            f"{cb.sample_size_score:.2f}",
            f"{cb.source_diversity_score:.2f}",
            f"{cb.temporal_consistency_score:.2f}",
            f"{cb.internal_agreement_score:.2f}",
            f"{cb.data_recency_score:.2f}",
            f"{s.confidence_score:.2f}",
        ])

    if conf_rows:
        t1 = _add_table(slide, conf_headers, conf_rows, 0.8, 1.35, 5.8, row_height=row_h)
        # Override to 9pt for compact fit
        for row_idx in range(len(conf_rows) + 1):
            for col_idx in range(len(conf_headers)):
                cell = t1.cell(row_idx, col_idx)
                cell.text_frame.paragraphs[0].font.size = Pt(9)

    # RIGHT: Signal Strength table
    sig_headers = ["Insight", "Prev.", "Engage.", "Intens.", "Depth", "Signal", "Quadrant"]
    sig_rows = []
    for s in scored_insights:
        sb = s.signal_strength_breakdown
        sig_rows.append([
            s.insight.insight_id,
            f"{sb.prevalence_score:.2f}",
            f"{sb.engagement_level_score:.2f}",
            f"{sb.sentiment_intensity_score:.2f}",
            f"{sb.conversation_depth_score:.2f}",
            f"{s.signal_strength_score:.2f}",
            s.matrix_quadrant.value,
        ])

    if sig_rows:
        t2 = _add_table(slide, sig_headers, sig_rows, 6.9, 1.35, 5.8, row_height=row_h)
        for row_idx in range(len(sig_rows) + 1):
            for col_idx in range(len(sig_headers)):
                cell = t2.cell(row_idx, col_idx)
                cell.text_frame.paragraphs[0].font.size = Pt(9)


def _slide_methodology_detail(prs, analysis):
    """Methodology Detail — analysis pipeline and scoring formulas across two slides."""

    def _render_detail_sections(slide, sections):
        tf = _add_textbox(slide, "", 0.8, 1.5, 11.5, 5.5, size=11)
        first = True
        for label, content in sections:
            p_label = tf.paragraphs[0] if first else tf.add_paragraph()
            p_label.text = label
            p_label.font.size = Pt(11)
            p_label.font.bold = True
            p_label.font.color.rgb = NAVY
            p_label.font.name = TITLE_FONT
            if not first:
                p_label.space_before = Pt(12)
                p_label.space_after = Pt(0)
            p_text = tf.add_paragraph()
            p_text.text = content
            p_text.font.size = Pt(11)
            p_text.font.color.rgb = SLATE
            p_text.font.name = BODY_FONT
            first = False

    # Slide 1: Analysis Pipeline
    slide1 = _add_slide(prs)
    _add_header(slide1, "Methodology: Analysis Pipeline", "How raw data becomes scored insights")
    _render_detail_sections(slide1, [
        ("ANALYSIS MODEL", analysis.analysis_model or "claude-sonnet (temperature=0)"),
        ("RELEVANCE FILTER", "LLM classifier at temperature=0. Each item classified relevant/irrelevant with reason. Rejected items saved for audit."),
        ("SENTIMENT + EMOTION", "Per-item: 4-class sentiment (positive/negative/neutral/mixed) + Plutchik 8 primary emotions (joy, trust, fear, surprise, sadness, disgust, anger, anticipation) + intensity (0-1). Batch size 15, temperature=0."),
        ("ASPECT-BASED SENTIMENT", "Per-aspect sentiment scoring (e.g., taste: positive 0.85, price: negative 0.30). Aspects require n\u226510 mentions to appear in report."),
        ("NET SENTIMENT SCORE", "NSS = (positive \u2212 negative) / total. Range -1.0 to +1.0. Computed overall, per-theme, and per-aspect (n\u226510). Industry standard metric."),
        ("THEME EXTRACTION", "Two-pass: (1) Stratified 300-item sample \u2192 discover 8-15 themes. (2) All remaining items mapped in batches of 30. Min 3 items per theme."),
        ("INSIGHT SYNTHESIS", "One insight per theme \u2014 no consolidation, no omissions. Framework: Observation \u2192 Insight \u2192 Implication \u2192 Recommendation \u2192 Further Validation. All 5 quality gates must pass."),
    ])

    # Slide 2: Scoring Formulas
    slide2 = _add_slide(prs)
    _add_header(slide2, "Methodology: Scoring Formulas", "Fully transparent and reproducible \u2014 no LLM opinion")
    _render_detail_sections(slide2, [
        ("CONFIDENCE SCORE", "Weighted sum of 5 factors: Sample Size (0.25) + Source Diversity (0.25) + Temporal Consistency (0.15) + Internal Agreement (0.20) + Data Recency (0.15). Range 0-1."),
        ("SIGNAL STRENGTH", "Weighted sum of 4 factors: Prevalence (0.35) + Engagement Level (0.30) + Sentiment Intensity (0.20) + Conversation Depth (0.15). Range 0-1."),
        ("INSIGHTS MATRIX", "High confidence + Strong signal = Key Finding  |  High conf + Weak signal = Emerging Trend  |  Low conf + Strong signal = Watch Closely  |  Low + Low = Noise."),
        ("QUALITY GATES", "All 5 must pass: Grounded (\u22653 source items) | Non-obvious | Actionable (concrete next step) | Specific (names occasions/segments) | Falsifiable (testable claim)."),
        ("CONFIDENCE INTERVALS", "Wilson score interval at 95% confidence level. Appropriate for small, non-random convenience samples."),
    ])


def _slide_data_provenance(prs, items, run_dir):
    """Data Provenance — source URLs and collection info."""
    slide = _add_slide(prs)
    _add_header(slide, "Data Provenance", "Every insight is traceable to source data")

    platform_counts = {}
    for item in items:
        p = item.source_platform.value
        platform_counts[p] = platform_counts.get(p, 0) + 1

    tf = _add_textbox(slide, "", 0.8, 1.5, 11.5, 5.5, size=11)
    tf.paragraphs[0].text = f"Run ID: {run_dir.name}"
    tf.paragraphs[0].font.size = Pt(11)
    tf.paragraphs[0].font.color.rgb = SLATE
    tf.paragraphs[0].font.name = BODY_FONT

    p = tf.add_paragraph()
    p.text = f"Total source URLs: {len(set(item.source_url for item in items))}"
    p.font.size = Pt(11)
    p.font.color.rgb = SLATE
    p.font.name = BODY_FONT

    for platform, count in platform_counts.items():
        p = tf.add_paragraph()
        p.text = f"  {platform.capitalize()}: {count} items"
        p.font.size = Pt(11)
        p.font.color.rgb = SLATE
        p.font.name = BODY_FONT

    p = tf.add_paragraph()
    p.text = ""
    p = tf.add_paragraph()
    p.text = "Full source URL list and collection parameters saved in run directory."
    p.font.size = Pt(8)
    p.font.italic = True
    p.font.color.rgb = MEDIUM_GREY
    p.font.name = BODY_FONT


def _slide_verbatim_index(prs, analysis):
    """Verbatim Index -- compact tables with theme headers.

    For each theme: navy header row, then 2-3 quotes as table rows.
    Target 4-5 themes per page = max 2-3 pages.

    Uses TWO-PASS RENDER (backgrounds first, then text) to prevent overlap.
    """
    import html as html_module
    from math import ceil
    from lxml import etree
    from pptx.oxml.ns import qn

    def _soft_break(paragraph):
        """Insert a soft line break into a paragraph element."""
        br = etree.SubElement(paragraph._p, qn("a:br"))
        rPr = etree.SubElement(br, qn("a:rPr"))
        rPr.set("lang", "en-US")
        rPr.set("dirty", "0")

    # Column geometry
    X_LEFT = 0.80
    W_QUOTE = 8.50
    X_PLAT = X_LEFT + W_QUOTE + 0.10
    W_PLAT = 1.10
    X_ENG = X_PLAT + W_PLAT + 0.06
    W_ENG = 0.90
    W_TOTAL = W_QUOTE + 0.10 + W_PLAT + 0.06 + W_ENG

    # Height constants
    CHARS_PER_LINE = 90
    LINE_H = 0.22
    ROW_PAD = 0.14
    MIN_ROW_H = 0.44
    THEME_HDR_H = 0.32
    COL_HDR_H = 0.24

    def row_h(text: str) -> float:
        visual_lines = 0
        for segment in text.split("\n"):
            seg = segment.strip()
            if seg:
                visual_lines += ceil(len(seg) / CHARS_PER_LINE)
            else:
                visual_lines += 1
        return max(MIN_ROW_H, visual_lines * LINE_H + ROW_PAD)

    # Group by theme, limit to 3 quotes per theme for compact layout
    theme_groups = []
    for theme in analysis.themes:
        quotes = []
        for q in theme.representative_quotes[:3]:
            clean_text = html_module.unescape(q.text).strip()
            if clean_text:
                quotes.append({
                    "quote": clean_text,
                    "platform": q.source_platform.value.capitalize(),
                    "engagement": int(q.engagement_score) if q.engagement_score else 0,
                })
        if quotes:
            theme_groups.append({"theme": theme.theme_label, "quotes": quotes})

    # Build flat render list
    render_list = []
    for tg in theme_groups:
        render_list.append(("theme_hdr", tg["theme"], THEME_HDR_H))
        for i, q in enumerate(tg["quotes"]):
            render_list.append(("row", q, row_h(q["quote"]), i % 2 == 0))

    # Paginate
    PAGE_CONTENT_TOP = 1.45 + COL_HDR_H
    CONTENT_BOTTOM = 7.35
    AVAIL_H = CONTENT_BOTTOM - PAGE_CONTENT_TOP

    pages: list[list] = []
    cur: list = []
    y_used = 0.0
    for item in render_list:
        h = item[2]
        if y_used + h > AVAIL_H and cur:
            pages.append(cur)
            cur = []
            y_used = 0.0
        cur.append(item)
        y_used += h
    if cur:
        pages.append(cur)

    # Render pages
    for pg_idx, page_items in enumerate(pages):
        slide = _add_slide(prs)
        pg_label = f"  --  Page {pg_idx + 1} of {len(pages)}" if len(pages) > 1 else ""
        _add_header(slide, "Verbatim Index",
                    f"Consumer quotes by theme{pg_label}")

        # Column headers
        hdr_y = 1.45
        _add_textbox(slide, "Verbatim Quote", X_LEFT, hdr_y, W_QUOTE, COL_HDR_H,
                     size=8, color=MEDIUM_GREY, bold=True, font_name=TITLE_FONT)
        _add_textbox(slide, "Platform", X_PLAT, hdr_y, W_PLAT, COL_HDR_H,
                     size=8, color=MEDIUM_GREY, bold=True, font_name=TITLE_FONT)
        _add_textbox(slide, "Engmt", X_ENG, hdr_y, W_ENG, COL_HDR_H,
                     size=8, color=MEDIUM_GREY, bold=True, font_name=TITLE_FONT)

        sep = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(X_LEFT), Inches(hdr_y + COL_HDR_H - 0.01),
            Inches(W_TOTAL), Pt(1)
        )
        sep.fill.solid()
        sep.fill.fore_color.rgb = BORDER_GREY
        sep.line.fill.background()

        # PASS 1: draw ALL backgrounds
        y = hdr_y + COL_HDR_H
        for item in page_items:
            item_type = item[0]
            data = item[1]
            h = item[2]

            if item_type == "theme_hdr":
                bar = slide.shapes.add_shape(
                    MSO_SHAPE.RECTANGLE,
                    Inches(X_LEFT), Inches(y), Inches(W_TOTAL), Inches(h)
                )
                bar.fill.solid()
                bar.fill.fore_color.rgb = NAVY
                bar.line.fill.background()
            else:
                even = item[3]
                row_bg = ALT_ROW if even else WHITE
                bg = slide.shapes.add_shape(
                    MSO_SHAPE.RECTANGLE,
                    Inches(X_LEFT), Inches(y), Inches(W_TOTAL), Inches(h)
                )
                bg.fill.solid()
                bg.fill.fore_color.rgb = row_bg
                bg.line.fill.background()

                # Row bottom separator
                ln = slide.shapes.add_shape(
                    MSO_SHAPE.RECTANGLE,
                    Inches(X_LEFT), Inches(y + h),
                    Inches(W_TOTAL), Pt(1)
                )
                ln.fill.solid()
                ln.fill.fore_color.rgb = BORDER_GREY
                ln.line.fill.background()

            y += h

        # PASS 2: draw ALL text (on top of backgrounds)
        y = hdr_y + COL_HDR_H
        for item in page_items:
            item_type = item[0]
            data = item[1]
            h = item[2]
            PAD = ROW_PAD / 2

            if item_type == "theme_hdr":
                txbox = slide.shapes.add_textbox(
                    Inches(X_LEFT + 0.10), Inches(y + PAD),
                    Inches(W_TOTAL - 0.15), Inches(h - PAD)
                )
                tf = txbox.text_frame
                tf.word_wrap = False
                p = tf.paragraphs[0]
                p.text = data
                p.font.size = Pt(9)
                p.font.bold = True
                p.font.color.rgb = WHITE
                p.font.name = TITLE_FONT
            else:
                q = data

                # Quote text
                qtbox = slide.shapes.add_textbox(
                    Inches(X_LEFT + 0.08), Inches(y + PAD),
                    Inches(W_QUOTE - 0.10), Inches(h - PAD)
                )
                qtf = qtbox.text_frame
                qtf.word_wrap = True
                p = qtf.paragraphs[0]
                p.font.size = Pt(8)
                p.font.italic = True
                p.font.color.rgb = SLATE
                p.font.name = BODY_FONT

                full_text = f'"{q["quote"]}"'
                flat_segs = full_text.split("\n")
                for si, seg in enumerate(flat_segs):
                    if si > 0:
                        _soft_break(p)
                    run = p.add_run()
                    run.text = seg
                    run.font.size = Pt(8)
                    run.font.italic = True
                    run.font.color.rgb = SLATE
                    run.font.name = BODY_FONT

                # Platform
                ptbox = slide.shapes.add_textbox(
                    Inches(X_PLAT), Inches(y + PAD),
                    Inches(W_PLAT), Inches(h - PAD)
                )
                ptf = ptbox.text_frame
                pp = ptf.paragraphs[0]
                pp.text = q["platform"]
                pp.font.size = Pt(8)
                pp.font.color.rgb = LIGHT_SLATE
                pp.font.name = BODY_FONT

                # Engagement
                if q["engagement"]:
                    etbox = slide.shapes.add_textbox(
                        Inches(X_ENG), Inches(y + PAD),
                        Inches(W_ENG), Inches(h - PAD)
                    )
                    etf = etbox.text_frame
                    ep = etf.paragraphs[0]
                    ep.text = f"{q['engagement']}"
                    ep.font.size = Pt(8)
                    ep.font.color.rgb = MEDIUM_GREY
                    ep.font.name = BODY_FONT

            y += h


def _slide_glossary(prs):
    """Glossary & Definitions slide."""
    slide = _add_slide(prs)
    _add_header(slide, "Glossary & Definitions")

    definitions = [
        ("Net Sentiment Score (NSS)", "(positive - negative) / total. Range -1.0 to +1.0. Industry standard metric."),
        ("Confidence Score", "Multi-factor score (0-1): sample size, source diversity, temporal consistency, internal agreement, data recency."),
        ("Signal Strength", "Multi-factor score (0-1): prevalence, engagement level, sentiment intensity, conversation depth."),
        ("Key Finding", "High confidence + Strong signal. Lead with these in business decisions."),
        ("Emerging Trend", "High confidence + Weak signal. Data supports it but few are talking about it yet."),
        ("Watch Closely", "Low confidence + Strong signal. Consumers care but data is thin."),
        ("ABSA", "Aspect-Based Sentiment Analysis. Sentiment scored per product/brand attribute, not per item."),
        ("Multi-coded", "An item may appear in multiple themes. Theme percentages may sum to >100%."),
        ("Convenience Sample", "Data from publicly available online discussions. Not a random or probability-based sample."),
        ("Wilson Score Interval", "Statistical method for confidence intervals on proportions, appropriate for small samples."),
    ]

    # Two-column layout for glossary
    col_defs = [definitions[:5], definitions[5:]]
    for col_idx, col_items in enumerate(col_defs):
        x = 0.8 + col_idx * 6.2
        tf = _add_textbox(slide, "", x, 1.35, 5.8, 5.5, size=10)
        first = True
        for term, defn in col_items:
            p_term = tf.paragraphs[0] if first else tf.add_paragraph()
            p_term.text = term
            p_term.font.size = Pt(11)
            p_term.font.bold = True
            p_term.font.color.rgb = NAVY
            p_term.font.name = TITLE_FONT
            if not first:
                p_term.space_before = Pt(12)
                p_term.space_after = Pt(0)

            p_def = tf.add_paragraph()
            p_def.text = defn
            p_def.font.size = Pt(9)
            p_def.font.color.rgb = SLATE
            p_def.font.name = BODY_FONT

            first = False

"""PDF report generator using WeasyPrint + Jinja2.

Renders the HTML template with analysis data, generates charts as SVG,
and produces a professional consulting-style PDF.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from consumer_research.config import PipelineConfig
from consumer_research.models.schemas import (
    AnalysisResults,
    MatrixQuadrant,
    NormalizedItem,
    ScoredInsight,
)

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"


def generate_pdf_report(
    scored_insights: list[ScoredInsight],
    analysis: AnalysisResults,
    items: list[NormalizedItem],
    config: PipelineConfig,
    run_dir: Path,
) -> Path:
    """Generate a professional PDF report from pipeline results.

    Args:
        scored_insights: Scored insights from Stage 6.
        analysis: Analysis results from Stage 4.
        items: Filtered corpus items.
        config: Pipeline configuration.
        run_dir: Run directory.

    Returns:
        Path to the generated PDF.
    """
    report_dir = run_dir / "report"
    report_dir.mkdir(parents=True, exist_ok=True)

    # Generate charts
    sentiment_chart_path = _generate_sentiment_chart(analysis, report_dir)

    # Prepare template data
    platform_counts = {}
    for item in items:
        p = item.source_platform.value
        platform_counts[p] = platform_counts.get(p, 0) + 1

    sources = list(platform_counts.keys())
    sources_summary = ", ".join(f"{p.capitalize()} ({c} items)" for p, c in platform_counts.items())

    key_findings = [s for s in scored_insights if s.matrix_quadrant == MatrixQuadrant.KEY_FINDING]
    single_source_themes = sum(1 for t in analysis.themes if not t.is_multi_source)

    # Load run config for keywords
    config_path = run_dir / "config.json"
    run_config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}

    template_data = {
        "brand_name": config.collection.brand_name,
        "category": config.collection.category,
        "date_range": f"Last {config.collection.time_period_days} days",
        "report_date": datetime.now().strftime("%B %d, %Y"),
        "run_id": run_dir.name,
        "objectives": config.collection.business_objectives,
        "sources_summary": sources_summary,
        "analysis_model": analysis.analysis_model,
        "total_collected": run_config.get("keywords", ["N/A"]),
        "total_after_filter": len(items),
        "themes_count": len(analysis.themes),
        "insights_count": len(scored_insights),
        "platform_counts": platform_counts,
        "overall_sentiment": analysis.overall_sentiment,
        "themes": analysis.themes,
        "top_insights": scored_insights[:5],
        "all_insights": scored_insights,
        "key_findings": key_findings,
        "single_source_themes": single_source_themes,
        "sentiment_chart": sentiment_chart_path.name if sentiment_chart_path else None,
        "keywords_used": ", ".join(run_config.get("keywords", [])[:20]),
        # Fix total_collected to be the actual number
        "total_collected": sum(platform_counts.values()) + (len(items) - sum(platform_counts.values())),
    }

    # Render HTML
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("report.html")
    html_content = template.render(**template_data)

    # Write HTML (useful for debugging)
    html_path = report_dir / "report.html"
    html_path.write_text(html_content, encoding="utf-8")

    # Generate PDF — try WeasyPrint, then fallback to HTML
    pdf_path = report_dir / "report.pdf"
    try:
        from weasyprint import HTML
        HTML(
            string=html_content,
            base_url=str(TEMPLATES_DIR),
        ).write_pdf(str(pdf_path))
        logger.info(f"PDF generated: {pdf_path}")
    except Exception as e:
        logger.error(f"WeasyPrint PDF generation failed (GTK not installed?): {e}")
        logger.info(f"HTML report saved as fallback: {html_path}")
        logger.info("To convert to PDF on Windows, run the PPTX through pptx_to_pdf.py instead.")
        return html_path

    return pdf_path


def pptx_report_to_pdf(pptx_path: Path) -> Path:
    """Convert the PPTX report to PDF using PowerPoint COM automation (Windows).

    This is the preferred PDF path on Windows — WeasyPrint requires GTK
    libraries not pre-installed on Windows, but PowerPoint is always present.

    Args:
        pptx_path: Path to the generated report.pptx.

    Returns:
        Path to the PDF, or raises RuntimeError on failure.
    """
    from consumer_research.report.pptx_to_pdf import pptx_to_pdf
    pdf_path = pptx_path.with_suffix(".pdf")
    return pptx_to_pdf(pptx_path, pdf_path)


def _generate_sentiment_chart(analysis: AnalysisResults, report_dir: Path) -> Path | None:
    """Generate a sentiment distribution bar chart as SVG."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        sentiments = analysis.overall_sentiment
        if not sentiments or all(v == 0 for v in sentiments.values()):
            return None

        labels = list(sentiments.keys())
        values = list(sentiments.values())
        colors = {
            "positive": "#38A169",
            "negative": "#E53E3E",
            "neutral": "#A0AEC0",
            "mixed": "#ED8936",
        }
        bar_colors = [colors.get(l, "#2B6CB0") for l in labels]

        fig, ax = plt.subplots(figsize=(6, 3))
        bars = ax.barh(labels, values, color=bar_colors, height=0.6)
        ax.set_xlabel("Count", fontsize=9, color="#4A5568")
        ax.set_title("Sentiment Distribution", fontsize=11, fontweight="bold", color="#1B2A4A")
        ax.tick_params(labelsize=9, colors="#4A5568")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#E2E8F0")
        ax.spines["bottom"].set_color("#E2E8F0")

        # Add value labels
        for bar, val in zip(bars, values):
            ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                    str(val), va="center", fontsize=9, color="#2D3748")

        plt.tight_layout()
        chart_path = report_dir / "sentiment_chart.svg"
        plt.savefig(str(chart_path), format="svg", bbox_inches="tight")
        plt.close()

        return chart_path

    except Exception as e:
        logger.warning(f"Chart generation failed: {e}")
        return None

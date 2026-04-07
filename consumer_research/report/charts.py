"""Chart generation for reports — produces PNG images embeddable in PPTX and HTML.

All charts follow the consulting design spec:
- Lato/Source Sans Pro fonts
- Navy (#1E3A5F) primary, deep grey (#374151) text
- No decorative elements, no 3D, no gradients
- Horizontal bars preferred, sorted by value
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Colors
NAVY = "#1E3A5F"
SLATE = "#374151"
LIGHT_GREY = "#F3F4F6"
BORDER = "#E5E7EB"
GREEN = "#38A169"
RED = "#E53E3E"
AMBER = "#ED8936"
GREY = "#A0AEC0"
TEAL = "#4FD1C5"
BLUE = "#2B6CB0"

SENTIMENT_COLORS = {
    "positive": GREEN,
    "negative": RED,
    "neutral": GREY,
    "mixed": AMBER,
}


# Plutchik's emotion colors (industry standard palette)
EMOTION_COLORS = {
    "joy": "#F6C344",          # gold
    "trust": "#38A169",        # green
    "fear": "#2D6A4F",         # dark green
    "surprise": "#4FD1C5",     # teal
    "sadness": "#3182CE",      # blue
    "disgust": "#805AD5",      # purple
    "anger": "#E53E3E",        # red
    "anticipation": "#ED8936", # orange
    "none": GREY,
}


def _setup_chart_style():
    """Configure matplotlib for clean consulting charts."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Lato", "Source Sans Pro", "Segoe UI", "Arial"],
        "font.size": 10,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.labelsize": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.spines.bottom": True,
        "axes.edgecolor": BORDER,
        "axes.labelcolor": SLATE,
        "axes.grid": True,
        "axes.grid.axis": "x",
        "grid.color": LIGHT_GREY,
        "grid.linewidth": 0.5,
        "xtick.color": SLATE,
        "ytick.color": SLATE,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    })
    return plt


def generate_sentiment_chart(sentiment_counts: dict, total: int, output_dir: Path) -> Path | None:
    """Horizontal bar chart of sentiment distribution with percentages."""
    try:
        plt = _setup_chart_style()
        fig, ax = plt.subplots(figsize=(8, 3.0))

        labels = list(sentiment_counts.keys())
        values = list(sentiment_counts.values())
        colors = [SENTIMENT_COLORS.get(l, GREY) for l in labels]

        bars = ax.barh(labels, values, color=colors, height=0.55, edgecolor="white", linewidth=0.5)

        for bar, val in zip(bars, values):
            pct = val / total * 100 if total > 0 else 0
            ax.text(bar.get_width() + max(values) * 0.02, bar.get_y() + bar.get_height() / 2,
                    f"{val} ({pct:.0f}%)", va="center", fontsize=10, color=SLATE, fontweight="500")

        ax.set_title("Sentiment Distribution", color=NAVY, pad=12)
        ax.invert_yaxis()
        ax.set_xlim(0, max(values) * 1.3 if values else 1)
        ax.tick_params(left=False)
        ax.spines["left"].set_visible(False)
        ax.spines["bottom"].set_color(BORDER)
        ax.spines["bottom"].set_linewidth(0.5)

        plt.tight_layout()
        path = output_dir / "chart_sentiment.png"
        plt.savefig(str(path), dpi=200, bbox_inches="tight", facecolor="white")
        plt.close()
        return path
    except Exception as e:
        logger.warning(f"Sentiment chart failed: {e}")
        return None


def generate_platform_chart(platform_counts: dict, output_dir: Path) -> Path | None:
    """Horizontal bar chart showing items per platform."""
    try:
        plt = _setup_chart_style()
        fig, ax = plt.subplots(figsize=(8, 2.8))

        # Sort by count descending
        sorted_items = sorted(platform_counts.items(), key=lambda x: x[1], reverse=True)
        labels = [k.capitalize() for k, v in sorted_items]
        values = [v for k, v in sorted_items]

        bars = ax.barh(labels, values, color=BLUE, height=0.55, edgecolor="white", linewidth=0.5)

        for bar, val in zip(bars, values):
            ax.text(bar.get_width() + max(values) * 0.02, bar.get_y() + bar.get_height() / 2,
                    str(val), va="center", fontsize=10, color=SLATE, fontweight="500")

        ax.set_title("Items by Platform", color=NAVY, pad=12)
        ax.invert_yaxis()
        ax.set_xlim(0, max(values) * 1.25 if values else 1)
        ax.tick_params(left=False)
        ax.spines["left"].set_visible(False)
        ax.spines["bottom"].set_color(BORDER)
        ax.spines["bottom"].set_linewidth(0.5)

        plt.tight_layout()
        path = output_dir / "chart_platforms.png"
        plt.savefig(str(path), dpi=200, bbox_inches="tight", facecolor="white")
        plt.close()
        return path
    except Exception as e:
        logger.warning(f"Platform chart failed: {e}")
        return None


def generate_theme_chart(themes: list, output_dir: Path) -> Path | None:
    """Horizontal bar chart of theme prevalence."""
    try:
        plt = _setup_chart_style()
        fig, ax = plt.subplots(figsize=(8, max(3.0, len(themes) * 0.5)))

        labels = [t.theme_label[:50] for t in themes]
        values = [t.prevalence_pct for t in themes]

        bars = ax.barh(labels, values, color=NAVY, height=0.55, edgecolor="white", linewidth=0.5)

        for bar, val in zip(bars, values):
            ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                    f"{val:.1f}%", va="center", fontsize=9, color=SLATE)

        ax.set_title("Theme Prevalence (% of corpus)", color=NAVY, pad=12)
        ax.invert_yaxis()
        ax.set_xlim(0, max(values) * 1.3 if values else 1)
        ax.set_xlabel("%")
        ax.tick_params(left=False)
        ax.spines["left"].set_visible(False)
        ax.spines["bottom"].set_color(BORDER)
        ax.spines["bottom"].set_linewidth(0.5)

        plt.tight_layout()
        path = output_dir / "chart_themes.png"
        plt.savefig(str(path), dpi=200, bbox_inches="tight", facecolor="white")
        plt.close()
        return path
    except Exception as e:
        logger.warning(f"Theme chart failed: {e}")
        return None



def generate_confidence_radar(scored: object, output_dir: Path, index: int = 0,
                              theme_label: str = "") -> Path | None:
    """Radar chart for a single insight's confidence + signal strength breakdown."""
    try:
        import numpy as np
        plt = _setup_chart_style()

        cb = scored.confidence_breakdown
        sb = scored.signal_strength_breakdown

        categories = ["Sample\nSize", "Source\nDiversity", "Temporal\nConsistency",
                      "Internal\nAgreement", "Data\nRecency", "Prevalence",
                      "Engagement", "Sentiment\nIntensity", "Conversation\nDepth"]
        values = [
            cb.sample_size_score, cb.source_diversity_score, cb.temporal_consistency_score,
            cb.internal_agreement_score, cb.data_recency_score,
            sb.prevalence_score, sb.engagement_level_score,
            sb.sentiment_intensity_score, sb.conversation_depth_score,
        ]

        N = len(categories)
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        values_plot = values + [values[0]]
        angles += [angles[0]]

        fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
        ax.plot(angles, values_plot, "o-", linewidth=2, color=NAVY, markersize=5)
        ax.fill(angles, values_plot, alpha=0.15, color=NAVY)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=7, color=SLATE)
        ax.set_ylim(0, 1)
        ax.set_yticks([0.25, 0.5, 0.75, 1.0])
        ax.set_yticklabels(["0.25", "0.50", "0.75", "1.00"], fontsize=7, color=GREY)
        ax.spines["polar"].set_visible(True)
        ax.spines["polar"].set_color(BORDER)
        ax.grid(True, color=BORDER, linewidth=0.5)

        title = theme_label if theme_label else scored.insight.insight_id
        ax.set_title(title, y=1.08, fontsize=9, fontweight="bold", color=NAVY)

        plt.tight_layout()
        insight_id = getattr(getattr(scored, "insight", None), "insight_id", None) or str(index)
        path = output_dir / f"chart_radar_{insight_id}.png"
        plt.savefig(str(path), dpi=200, bbox_inches="tight", facecolor="white")
        plt.close()
        return path
    except Exception as e:
        logger.warning(f"Radar chart failed: {e}")
        return None


def generate_emotion_chart(emotion_distribution: dict, output_dir: Path) -> Path | None:
    """Horizontal bar chart of Plutchik emotion distribution."""
    try:
        plt = _setup_chart_style()

        # Filter out zero-count and sort descending
        data = {k: v for k, v in emotion_distribution.items() if v > 0 and k != "none"}
        if not data:
            return None

        data = dict(sorted(data.items(), key=lambda x: x[1], reverse=True))
        labels = [k.capitalize() for k in data.keys()]
        values = list(data.values())
        colors = [EMOTION_COLORS.get(k, GREY) for k in data.keys()]

        fig, ax = plt.subplots(figsize=(8, max(3.0, len(labels) * 0.5)))
        bars = ax.barh(labels, values, color=colors, height=0.55, edgecolor="white", linewidth=0.5)

        total = sum(values)
        for bar, val in zip(bars, values):
            pct = val / total * 100 if total > 0 else 0
            ax.text(bar.get_width() + max(values) * 0.02, bar.get_y() + bar.get_height() / 2,
                    f"{val} ({pct:.0f}%)", va="center", fontsize=10, color=SLATE, fontweight="500")

        ax.set_title("Emotional Profile (Plutchik)", color=NAVY, pad=12)
        ax.invert_yaxis()
        ax.set_xlim(0, max(values) * 1.3 if values else 1)
        ax.tick_params(left=False)
        ax.spines["left"].set_visible(False)
        ax.spines["bottom"].set_color(BORDER)
        ax.spines["bottom"].set_linewidth(0.5)

        plt.tight_layout()
        path = output_dir / "chart_emotions.png"
        plt.savefig(str(path), dpi=200, bbox_inches="tight", facecolor="white")
        plt.close()
        return path
    except Exception as e:
        logger.warning(f"Emotion chart failed: {e}")
        return None


def generate_aspect_heatmap(aspect_summary: dict, output_dir: Path) -> Path | None:
    """Heatmap: rows=aspects, columns=sentiment categories, cells=count intensity."""
    try:
        import numpy as np
        plt = _setup_chart_style()

        if not aspect_summary:
            return None

        # Sort aspects by total mentions, take top 15
        sorted_aspects = sorted(
            aspect_summary.items(),
            key=lambda x: sum(x[1].values()),
            reverse=True,
        )[:15]

        if not sorted_aspects:
            return None

        sentiment_cols = ["positive", "negative", "neutral", "mixed"]
        aspect_labels = [a[0].capitalize() for a in sorted_aspects]
        data = np.array([
            [a[1].get(s, 0) for s in sentiment_cols]
            for a in sorted_aspects
        ], dtype=float)

        fig, ax = plt.subplots(figsize=(6, max(3, len(aspect_labels) * 0.4)))

        im = ax.imshow(data, cmap="YlOrRd", aspect="auto")

        ax.set_xticks(range(len(sentiment_cols)))
        ax.set_xticklabels([s.capitalize() for s in sentiment_cols], fontsize=9)
        ax.set_yticks(range(len(aspect_labels)))
        ax.set_yticklabels(aspect_labels, fontsize=9)
        ax.tick_params(top=True, bottom=False, labeltop=True, labelbottom=False)

        # Add text annotations in cells
        for i in range(len(aspect_labels)):
            for j in range(len(sentiment_cols)):
                val = int(data[i, j])
                if val > 0:
                    text_color = "white" if data[i, j] > data.max() * 0.6 else SLATE
                    ax.text(j, i, str(val), ha="center", va="center",
                            fontsize=9, color=text_color, fontweight="bold")

        ax.set_title("Aspect × Sentiment", color=NAVY, pad=25, fontsize=13)

        plt.tight_layout()
        path = output_dir / "chart_aspect_heatmap.png"
        plt.savefig(str(path), dpi=200, bbox_inches="tight", facecolor="white")
        plt.close()
        return path
    except Exception as e:
        logger.warning(f"Aspect heatmap failed: {e}")
        return None


def generate_temporal_chart(items, output_dir: Path) -> Path | None:
    """Vertical bar chart showing item count by year."""
    try:
        from collections import Counter
        from datetime import datetime as _dt, timezone as _tz

        plt = _setup_chart_style()

        # Extract years from timestamps
        year_counts = Counter()
        no_date = 0
        for item in items:
            ts = item.source_timestamp if hasattr(item, "source_timestamp") else item.get("source_timestamp")
            if not ts:
                no_date += 1
                continue
            if isinstance(ts, _dt):
                year_counts[ts.year] += 1
            else:
                try:
                    parsed = _dt.fromisoformat(str(ts).replace("Z", "+00:00"))
                    year_counts[parsed.year] += 1
                except (ValueError, TypeError):
                    no_date += 1

        if not year_counts:
            return None

        # Use full corpus as denominator (not just dated subset)
        corpus_total = len(items)

        # Sort by year
        years = sorted(year_counts.keys())
        counts = [year_counts[y] for y in years]
        labels = [str(y) for y in years]

        # Append undated bar if any items lack timestamps
        if no_date > 0:
            years.append("Undated")
            counts.append(no_date)
            labels.append("Undated")

        fig, ax = plt.subplots(figsize=(8, 3.5))

        # Use grey for the undated bar
        bar_colors = [BLUE] * (len(counts) - (1 if no_date > 0 else 0))
        if no_date > 0:
            bar_colors.append(GREY)

        bars = ax.bar(labels, counts, color=bar_colors, width=0.6, edgecolor="white", linewidth=0.5)

        # Add count + percentage labels on top of each bar
        # Percentages are of full corpus, not just dated subset
        for bar, val in zip(bars, counts):
            pct = val / corpus_total * 100
            label = f"{val:,}\n({pct:.0f}%)" if pct >= 2 else f"{val:,}"
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(counts) * 0.02,
                    label, ha="center", va="bottom", fontsize=9, color=SLATE, fontweight="500")

        title = "Data Distribution by Year"
        ax.set_title(title, color=NAVY, pad=12)
        ax.set_ylabel("Items", color=SLATE)
        ax.set_ylim(0, max(counts) * 1.25)
        ax.spines["bottom"].set_color(BORDER)
        ax.spines["bottom"].set_linewidth(0.5)
        ax.tick_params(bottom=False)

        # Switch grid to y-axis for vertical bar chart
        ax.yaxis.grid(True, color=LIGHT_GREY, linewidth=0.5)
        ax.xaxis.grid(False)

        plt.tight_layout()
        path = output_dir / "chart_temporal.png"
        plt.savefig(str(path), dpi=200, bbox_inches="tight", facecolor="white")
        plt.close()
        return path
    except Exception as e:
        logger.warning(f"Temporal chart failed: {e}")
        return None


def generate_all_charts(analysis, scored_insights, items, output_dir: Path) -> dict:
    """Generate all charts and return paths dict."""
    output_dir.mkdir(parents=True, exist_ok=True)

    platform_counts = {}
    for item in items:
        p = item.source_platform.value
        platform_counts[p] = platform_counts.get(p, 0) + 1

    total = len(items)

    charts = {
        "sentiment": generate_sentiment_chart(analysis.overall_sentiment, total, output_dir),
        "platforms": generate_platform_chart(platform_counts, output_dir),
        "themes": generate_theme_chart(analysis.themes, output_dir),
        "emotions": generate_emotion_chart(
            getattr(analysis, "emotion_distribution", {}), output_dir
        ),
        "aspect_heatmap": generate_aspect_heatmap(
            getattr(analysis, "aspect_sentiment_summary", {}), output_dir
        ),
        "temporal": generate_temporal_chart(items, output_dir),
    }

    # Build theme_id → label lookup
    theme_label_map = {t.theme_id: t.theme_label for t in getattr(analysis, "themes", [])}

    # Generate radar charts for ALL insights, titled with theme label
    for i, scored in enumerate(scored_insights):
        theme_ids = getattr(scored.insight, "supporting_theme_ids", [])
        label = theme_label_map.get(theme_ids[0], "") if theme_ids else ""
        charts[f"radar_{i}"] = generate_confidence_radar(scored, output_dir, i, theme_label=label)

    logger.info(f"Charts generated: {sum(1 for v in charts.values() if v)}/{len(charts)}")
    return charts

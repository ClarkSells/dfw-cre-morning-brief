"""Capital-markets chart for the brief (matplotlib, styled to match the CSS)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import datetime as dt

ACCENT, INK, MUTED, GRID = "#16704b", "#14181c", "#5f6368", "#e3e7ea"


def render_series(series, out="chart.png", label="10-Year U.S. Treasury Yield", pct=True):
    """series: list of (YYYY-MM-DD, value). Draws one clean line."""
    xs = [dt.date.fromisoformat(d) for d, _ in series]
    ys = [v for _, v in series]
    fig, ax = plt.subplots(figsize=(7.2, 2.6), dpi=200)
    ax.plot(xs, ys, color=ACCENT, linewidth=2.2, marker="o", markersize=4,
            markerfacecolor=ACCENT, markeredgecolor="white", markeredgewidth=0.8)
    ax.fill_between(xs, ys, min(ys) - (max(ys) - min(ys)) * 0.15, color=ACCENT, alpha=0.06)
    for xv, yv in zip(xs, ys):
        ax.annotate(f"{yv:.2f}%", (xv, yv), textcoords="offset points", xytext=(0, 7),
                    ha="center", fontsize=8, color=INK, weight="bold")
    ax.set_title(label, loc="left", fontsize=12, color=INK, weight="bold")
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.xaxis.set_major_formatter(DateFormatter("%b %d"))
    if pct:
        ax.yaxis.set_major_formatter(lambda v, _: f"{v:.2f}%")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.margins(x=0.01)
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


def render_bars(rows, out="bars.png", title="CMBS Delinquency Rate by Property Type", pct=True):
    """rows: list of (label, value). Horizontal bars with value labels."""
    labels = [r[0] for r in rows]
    vals = [r[1] for r in rows]
    fig, ax = plt.subplots(figsize=(7.2, 1.9), dpi=200)
    ys = range(len(rows))[::-1]
    colors = [ACCENT if l.lower() != "all property" else "#9aa4ab" for l in labels]
    ax.barh(list(ys), vals, height=0.62, color=colors)
    for y, v in zip(ys, vals):
        ax.text(v + max(vals) * 0.012, y, f"{v:.2f}%" if pct else f"{v:,}",
                va="center", fontsize=8, color=INK, weight="bold")
    ax.set_yticks(list(ys))
    ax.set_yticklabels(labels, fontsize=8, color=INK)
    ax.set_title(title, loc="left", fontsize=11, color=INK, weight="bold")
    ax.set_xlim(0, max(vals) * 1.14)
    ax.tick_params(axis="x", colors=MUTED, labelsize=7)
    if pct:
        ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.grid(axis="x", color=GRID, linewidth=0.5)
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out

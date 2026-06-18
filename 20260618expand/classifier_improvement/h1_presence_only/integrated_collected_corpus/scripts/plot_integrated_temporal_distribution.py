"""
plot_integrated_temporal_distribution.py

Integrated collected corpus (current, before through-2021 backfill)
의 시간적 분포 및 humor rate를 시각화한다.

N = 68,039
Sources: fortune100, wendys_legacy, moonpie_legacy, cocacola_legacy,
         fortune100_raw_append

Panel layout:
  Top-left:     Year (post count bar + humor_rate_t50 line)
  Top-right:    Month (post count bar + humor_rate_t50 line)
  Bottom-left:  Day of Week (post count bar + humor_rate_t50 line)
  Bottom-right: Hour UTC (post count bar + humor_rate_t50 line)

Output: figures/integrated_temporal_distribution.png
"""

from __future__ import annotations
import csv
import sys
from pathlib import Path

PYPACKAGES = Path("/home/user/.local/pypackages")
if str(PYPACKAGES) not in sys.path:
    sys.path.insert(0, str(PYPACKAGES))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / "20260618expand" / "classifier_improvement" / \
       "h1_presence_only" / "integrated_collected_corpus"
RES  = BASE / "results"
FIG  = BASE / "figures"
FIG.mkdir(parents=True, exist_ok=True)

CORPUS_LABEL = "Current integrated corpus (before through-2021 backfill)  |  N=68,039"
BAR_COLOR    = "#4C72B0"
LINE_COLOR   = "#DD8452"
ALPHA_BAR    = 0.85

MONTH_LABELS = ["Jan","Feb","Mar","Apr","May","Jun",
                "Jul","Aug","Sep","Oct","Nov","Dec"]
DOW_LABELS   = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def dual_axis_bar_line(ax_bar, xs, counts, rates,
                       xtick_labels, xlabel, bar_width=0.65):
    """Bar chart (post count) on primary axis, humor_rate line on secondary."""
    ax_bar.bar(xs, counts, width=bar_width,
               color=BAR_COLOR, alpha=ALPHA_BAR,
               edgecolor="white", linewidth=0.4, label="Post count")
    ax_bar.set_xlabel(xlabel, fontsize=9)
    ax_bar.set_ylabel("Post count", fontsize=9, color=BAR_COLOR)
    ax_bar.tick_params(axis="y", labelcolor=BAR_COLOR)
    ax_bar.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    if xtick_labels is not None:
        ax_bar.set_xticks(xs)
        ax_bar.set_xticklabels(xtick_labels, fontsize=8)
    ax_bar.spines[["top"]].set_visible(False)

    ax_line = ax_bar.twinx()
    ax_line.plot(xs, [r * 100 for r in rates], color=LINE_COLOR,
                 marker="o", markersize=3.5, linewidth=1.5,
                 label="Humor rate t50 (%)")
    ax_line.set_ylabel("Humor rate t50 (%)", fontsize=9, color=LINE_COLOR)
    ax_line.tick_params(axis="y", labelcolor=LINE_COLOR)
    ax_line.set_ylim(0, 100)
    ax_line.spines[["top"]].set_visible(False)

    # legend
    h1, l1 = ax_bar.get_legend_handles_labels()
    h2, l2 = ax_line.get_legend_handles_labels()
    ax_bar.legend(h1 + h2, l1 + l2, fontsize=7, loc="upper right",
                  framealpha=0.7)

    return ax_line


def main():
    print("=== plot_integrated_temporal_distribution ===")

    year_rows  = read_csv(RES / "year_distribution.csv")
    month_rows = read_csv(RES / "month_of_year_distribution.csv")
    dow_rows   = read_csv(RES / "day_of_week_distribution.csv")
    hour_rows  = read_csv(RES / "hour_of_day_distribution.csv")

    fig, axes = plt.subplots(2, 2, figsize=(17, 10))
    fig.suptitle(CORPUS_LABEL, fontsize=11, fontweight="bold", y=1.01)

    # ── Year ──────────────────────────────────────────────────────────────────
    ax = axes[0, 0]
    ax.set_title("Year — Post Count & Humor Rate (t50)", fontsize=11, fontweight="bold")
    years  = [int(r["year"]) for r in year_rows]
    ycnt   = [int(r["total_posts"]) for r in year_rows]
    yrate  = [float(r["humor_rate_t50"]) for r in year_rows]
    dual_axis_bar_line(ax, years, ycnt, yrate,
                       [str(y) for y in years], "Year", bar_width=0.7)
    ax.set_xticks(years)
    ax.set_xticklabels([str(y) for y in years], rotation=45, ha="right", fontsize=7.5)

    # ── Month ─────────────────────────────────────────────────────────────────
    ax = axes[0, 1]
    ax.set_title("Month — Post Count & Humor Rate (t50)", fontsize=11, fontweight="bold")
    months = [int(r["month_of_year"]) for r in month_rows]
    mcnt   = [int(r["total_posts"]) for r in month_rows]
    mrate  = [float(r["humor_rate_t50"]) for r in month_rows]
    dual_axis_bar_line(ax, months, mcnt, mrate, MONTH_LABELS, "Month", bar_width=0.7)

    # ── Day of Week ───────────────────────────────────────────────────────────
    ax = axes[1, 0]
    ax.set_title("Day of Week — Post Count & Humor Rate (t50)", fontsize=11, fontweight="bold")
    dows  = [int(r["day_of_week"]) for r in dow_rows]
    dcnt  = [int(r["total_posts"]) for r in dow_rows]
    drate = [float(r["humor_rate_t50"]) for r in dow_rows]
    dual_axis_bar_line(ax, dows, dcnt, drate, DOW_LABELS, "Day of Week", bar_width=0.6)

    # ── Hour ──────────────────────────────────────────────────────────────────
    ax = axes[1, 1]
    ax.set_title("Hour (UTC) — Post Count & Humor Rate (t50)", fontsize=11, fontweight="bold")
    hours = [int(r["hour_of_day"]) for r in hour_rows]
    hcnt  = [int(r["total_posts"]) for r in hour_rows]
    hrate = [float(r["humor_rate_t50"]) for r in hour_rows]
    dual_axis_bar_line(ax, hours, hcnt, hrate,
                       [str(h) for h in hours], "Hour (UTC, 0-23)", bar_width=0.75)

    # Pre-2022 data gap annotation on Year panel
    axes[0, 0].axvspan(2009 - 0.5, 2021 + 0.5, alpha=0.07, color="red",
                       label="Pre-2022 (low coverage)")
    axes[0, 0].annotate("Pre-2022\nlow coverage\n(backfill pending)",
                        xy=(2018, max(ycnt) * 0.6),
                        fontsize=7, color="red", ha="center",
                        bbox=dict(boxstyle="round,pad=0.2", fc="white",
                                  ec="red", alpha=0.7))

    plt.tight_layout()
    out = FIG / "integrated_temporal_distribution.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out}")

    # ── Source breakdown figure ───────────────────────────────────────────────
    src_rows = read_csv(
        BASE / "data" / "integrated_h1_presence_by_source_summary.csv"
    )
    src_names = [r["source_dataset"] for r in src_rows]
    src_n     = [int(r["total_posts"]) for r in src_rows]
    src_rate  = [float(r["humor_rate_t50"]) * 100 for r in src_rows]

    fig2, axes2 = plt.subplots(1, 2, figsize=(12, 5))
    fig2.suptitle(
        "Source Breakdown  |  " + CORPUS_LABEL,
        fontsize=10, fontweight="bold", y=1.02
    )

    ax = axes2[0]
    colors = ["#4C72B0","#55A868","#C44E52","#8172B2","#937860"]
    bars = ax.bar(range(len(src_names)), src_n, color=colors,
                  edgecolor="white", linewidth=0.5)
    ax.set_title("Row count by source", fontsize=10, fontweight="bold")
    ax.set_xticks(range(len(src_names)))
    ax.set_xticklabels(src_names, rotation=25, ha="right", fontsize=8)
    ax.set_ylabel("Post count")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    for bar, v in zip(bars, src_n):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(src_n)*0.01,
                f"{v:,}", ha="center", va="bottom", fontsize=8)
    ax.spines[["top","right"]].set_visible(False)

    ax = axes2[1]
    bars2 = ax.bar(range(len(src_names)), src_rate, color=colors,
                   edgecolor="white", linewidth=0.5)
    ax.set_title("Humor rate t50 (%) by source", fontsize=10, fontweight="bold")
    ax.set_xticks(range(len(src_names)))
    ax.set_xticklabels(src_names, rotation=25, ha="right", fontsize=8)
    ax.set_ylabel("Humor rate (%)")
    ax.set_ylim(0, 100)
    for bar, v in zip(bars2, src_rate):
        ax.text(bar.get_x() + bar.get_width()/2, v + 1.5,
                f"{v:.1f}%", ha="center", va="bottom", fontsize=8)
    ax.axhline(40.4, color="gray", linestyle="--", linewidth=1,
               label="Corpus overall (40.4%)")
    ax.legend(fontsize=8)
    ax.spines[["top","right"]].set_visible(False)

    plt.tight_layout()
    out2 = FIG / "integrated_source_breakdown.png"
    fig2.savefig(out2, dpi=150, bbox_inches="tight")
    plt.close(fig2)
    print(f"  Saved: {out2}")

    # ── Summary print ─────────────────────────────────────────────────────────
    print("\n  === 분포 요약 (current integrated corpus, before through-2021 backfill) ===")
    total_n = sum(src_n)
    print(f"  Total posts: {total_n:,}")
    print(f"  Sources: {len(src_names)}")
    for s, n, r in zip(src_names, src_n, src_rate):
        print(f"    {s:25s}: {n:6,} rows  humor_rate_t50={r:.1f}%")
    print()
    print(f"  Year range: {min(years)}–{max(years)}")
    ylo = [(y, c) for y, c in zip(years, ycnt) if y <= 2021]
    print(f"  Pre-2022 rows: {sum(c for _,c in ylo):,} "
          f"({sum(c for _,c in ylo)/total_n*100:.1f}% of corpus)")
    print(f"  2022+ rows:    {sum(c for y,c in zip(years,ycnt) if y >= 2022):,}")
    print()
    print(f"  Humor rate t50 (overall): 40.4%")
    peak_month = MONTH_LABELS[months[mrate.index(max(mrate))] - 1]
    low_month  = MONTH_LABELS[months[mrate.index(min(mrate))] - 1]
    print(f"  Humor rate peak month: {peak_month} ({max(mrate)*100:.1f}%)")
    print(f"  Humor rate low month:  {low_month} ({min(mrate)*100:.1f}%)")
    peak_dow = DOW_LABELS[drate.index(max(drate))]
    low_dow  = DOW_LABELS[drate.index(min(drate))]
    print(f"  Humor rate peak DOW: {peak_dow} ({max(drate)*100:.1f}%)  "
          f"low: {low_dow} ({min(drate)*100:.1f}%)")
    peak_hr = hours[hrate.index(max(hrate))]
    low_hr  = hours[hrate.index(min(hrate))]
    print(f"  Humor rate peak hour (UTC): {peak_hr}h ({max(hrate)*100:.1f}%)  "
          f"low: {low_hr}h ({min(hrate)*100:.1f}%)")
    print("=== plot_integrated_temporal_distribution COMPLETE ===")


if __name__ == "__main__":
    main()

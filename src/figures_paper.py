"""Sinh figure EDA cơ bản (eval split, missing) theo style publication.

Quy ước style: font sans-serif, palette thân thiện mù màu, không gridline,
dpi 300, bỏ title trong hình (caption nằm ở report), xuất PNG + PDF.
Figure hành vi khách hàng nằm ở src/eda_behavior.py.

Chạy: .venv/bin/python src/figures_paper.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

# --------------------------------------------------------------------------
# Publication-quality styling (từ figure-generation/scripts/figure_template.py)
# --------------------------------------------------------------------------
plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 7,
        "axes.labelsize": 7.5,
        "axes.titlesize": 8,
        "xtick.labelsize": 6.5,
        "ytick.labelsize": 6.5,
        "legend.fontsize": 6.5,
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.05,
        "axes.grid": False,
        "axes.linewidth": 0.6,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.major.size": 2.5,
        "ytick.major.size": 2.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "pdf.fonttype": 42,  # nhúng font dạng TrueType cho PDF
    }
)

# Palette thân thiện mù màu (AGENTS.md)
PRIMARY = "#3C78B5"
SECONDARY = "#E07A5F"
TERTIARY = "#4D9A85"
NEUTRAL = "#6C757D"
ACCENT = "#D6A430"

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DOCS = ROOT / "docs"
FIG = DOCS / "figures"
FIG.mkdir(parents=True, exist_ok=True)


def _panel(ax: plt.Axes, letter: str) -> None:
    """Gắn panel label A/B/C in đậm."""
    ax.set_title(letter, loc="left", fontweight="bold", fontsize=8, pad=4)


def _vi_int(value: float) -> str:
    """Định dạng số nguyên kiểu Việt Nam: 3.214.874."""
    return f"{value:,.0f}".replace(",", ".")


def _vi_pct(value: float) -> str:
    """Định dạng phần trăm kiểu Việt Nam: 93,97%."""
    return f"{value:.2f}%".replace(".", ",")


def save(fig: plt.Figure, name: str) -> None:
    fig.savefig(FIG / f"{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {name}.png / {name}.pdf")


# --------------------------------------------------------------------------
# Hình 1: số đơn hàng theo eval_set
# --------------------------------------------------------------------------
def fig_eval_split(counts: dict[str, int]) -> None:
    """A: tỉ lệ đơn (thang tuyến tính); B: số đơn (thang log)."""
    order = ["prior", "train", "test"]
    vals = np.array([counts[k] for k in order], dtype=float)
    pct = vals / vals.sum() * 100
    colors = [PRIMARY, SECONDARY, TERTIARY]
    y = np.arange(len(order))

    fig, (ax1, ax2) = plt.subplots(
        1,
        2,
        figsize=(7.2, 2.0),
        constrained_layout=True,
        gridspec_kw={"width_ratios": [1.0, 1.15]},
    )

    # A: phần trăm trên một thanh 100% (part-to-whole, không cắt trục)
    left = 0.0
    for p, color in zip(pct, colors):
        ax1.barh(0, p, left=left, height=0.3, color=color, linewidth=0)
        left += p
    ax1.set_xlim(0, 100)
    ax1.set_ylim(-0.5, 0.5)
    ax1.set_yticks([])
    ax1.set_xlabel("Tỉ lệ đơn hàng (%)")
    ax1.spines["left"].set_visible(False)
    ax1.tick_params(axis="y", length=0)
    _panel(ax1, "A")

    # B: số đơn tuyệt đối trên thang log
    ax2.barh(y, vals, color=colors, edgecolor="white", linewidth=0.6, height=0.55)
    ax2.set_yticks(y)
    ax2.set_yticklabels(order)
    ax2.invert_yaxis()
    ax2.set_xscale("log")
    ax2.set_xlim(1e4, 2e7)
    ax2.set_xlabel("Số đơn hàng (thang log)")
    ax2.tick_params(which="minor", axis="x", length=1.5, width=0.4)
    for yi, v in zip(y, vals):
        ax2.text(v * 1.3, yi, _vi_int(v), va="center", fontsize=6.5)
    _panel(ax2, "B")

    handles = [
        Patch(facecolor=c, edgecolor="none", label=f"{name} ({_vi_pct(p)})")
        for name, p, c in zip(order, pct, colors)
    ]
    fig.legend(
        handles=handles,
        loc="outside lower center",
        ncol=3,
        frameon=False,
        handlelength=1.2,
        columnspacing=1.8,
    )
    save(fig, "fig_eval_split")


# --------------------------------------------------------------------------
# Hình 2: tỉ lệ missing theo cột
# --------------------------------------------------------------------------
COLUMNS = {
    "orders.csv": [
        "order_id", "user_id", "eval_set", "order_number", "order_dow",
        "order_hour_of_day", "days_since_prior_order",
    ],
    "order_products__prior.csv": ["order_id", "product_id", "add_to_cart_order", "reordered"],
    "order_products__train.csv": ["order_id", "product_id", "add_to_cart_order", "reordered"],
    "products.csv": ["product_id", "product_name", "aisle_id", "department_id"],
    "aisles.csv": ["aisle_id", "aisle"],
    "departments.csv": ["department_id", "department"],
}


def fig_missing(summary: dict) -> None:
    """Dot plot tỉ lệ thiếu cho toàn bộ cột; chỉ một cột khác 0."""
    missing = {
        (m["file"], m["column"]): (m["missing_pct"], m["rows"])
        for m in summary["missing_columns"]
    }

    labels, pcts, gaps = [], [], []
    pos = 0.0
    separators = []
    missing_rows: dict[tuple[str, str], int] = {}
    for file, cols in COLUMNS.items():
        for col in cols:
            labels.append(f"{file} · {col}")
            pct, rows = missing.get((file, col), (0.0, 0))
            pcts.append(pct)
            missing_rows[(file, col)] = rows
            gaps.append(pos)
            pos += 1.0
        separators.append(pos - 0.05)
        pos += 0.7  # khoảng trống giữa các file

    positions = np.array(gaps)
    pcts = np.array(pcts)

    fig, ax = plt.subplots(figsize=(7.2, 3.5), constrained_layout=True)
    for sep in separators[:-1]:
        ax.axhline(sep, color="#E3E3E3", linewidth=0.5, zorder=1)

    for ypos, p in zip(positions, pcts):
        if p > 0:
            ax.plot([0, p], [ypos, ypos], color=ACCENT, linewidth=0.9, zorder=2)
            ax.plot(p, ypos, "o", markersize=3.4, color=ACCENT, zorder=3)
        else:
            ax.plot(
                0, ypos, "o", markersize=3.0, markerfacecolor="white",
                markeredgecolor=PRIMARY, markeredgewidth=0.7, zorder=3,
            )

    ax.set_yticks(positions)
    ax.set_yticklabels(labels, fontsize=6.0)
    ax.invert_yaxis()
    ax.set_xlim(-0.15, 7.2)
    ax.set_ylim(positions.max() + 0.6, -0.6)
    ax.set_xlabel("Tỉ lệ giá trị thiếu (%)")
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", labelsize=6.5)

    # nhãn giá trị cho cột duy nhất có missing
    imax = int(np.argmax(pcts))
    column = labels[imax].split(" · ", 1)
    n_missing = round(pcts[imax] / 100 * missing_rows[tuple(column)])
    ax.text(
        pcts[imax] + 0.12, positions[imax], _vi_pct(pcts[imax]),
        va="center", fontsize=6.0, color=ACCENT,
    )
    ax.text(
        1.6, positions[imax] - 0.9,
        f"{_vi_int(n_missing)} dòng = đơn đầu tiên của mỗi khách",
        va="bottom", fontsize=5.8, color=NEUTRAL,
    )
    save(fig, "fig_missing")


def main() -> None:
    summary = json.loads((DOCS / "summary.json").read_text())
    print("Rendering publication-style figures:")
    fig_eval_split(summary["eval_set_counts"])
    fig_missing(summary)


if __name__ == "__main__":
    main()

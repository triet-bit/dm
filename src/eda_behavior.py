"""EDA hành vi mua hàng: thời gian, khoảng cách đơn, kích thước và biến động giỏ.

Năm đầu ra:
  1. Số đơn hàng trên mỗi khách hàng (orders.csv).
  2. Ngày và giờ đặt hàng (orders_prior.csv).
  3. Khoảng thời gian giữa hai đơn liên tiếp (orders_prior.csv).
  4. Phân phối kích thước giỏ (order_products__prior.csv).
  5. Biến động kích thước giỏ qua các đơn liên tiếp.

Số liệu ghi vào docs/behavior_summary.json; figure xuất PDF + PNG 300 dpi vào
docs/figures/. Chạy: .venv/bin/python src/eda_behavior.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LogNorm

# ---------------------------------------------------------------------------
# Style dùng chung (AGENTS.md: font sans-serif, palette thân thiện mù màu,
# không gridline, chỉ giữ trục trái/dưới, panel label in đậm).
# ---------------------------------------------------------------------------
PRIMARY = "#3C78B5"
SECONDARY = "#E07A5F"
TERTIARY = "#4D9A85"
NEUTRAL = "#6C757D"
ACCENT = "#D6A430"

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 7,
        "axes.labelsize": 7.5,
        "xtick.labelsize": 6.5,
        "ytick.labelsize": 6.5,
        "legend.fontsize": 6.5,
        "axes.linewidth": 0.6,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.major.size": 2.5,
        "ytick.major.size": 2.5,
        "axes.grid": False,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "savefig.dpi": 300,
        "pdf.fonttype": 42,
    }
)

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DOCS = ROOT / "docs"
FIG = DOCS / "figures"
FIG.mkdir(parents=True, exist_ok=True)

SEED = 42  # không dùng random; ghi lại để đồng bộ quy ước tái lập
CHUNK = 5_000_000


def _panel(ax: plt.Axes, letter: str) -> None:
    """Gắn panel label A/B/C in đậm."""
    ax.set_title(letter, loc="left", fontweight="bold", fontsize=8, pad=4)


def _save(fig: plt.Figure, name: str) -> None:
    """Lưu vector PDF và preview PNG 300 dpi."""
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIG / f"{name}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {name}.pdf / {name}.png")


# ---------------------------------------------------------------------------
# Số liệu
# ---------------------------------------------------------------------------
def orders_per_customer(path: Path) -> pd.Series:
    """Đếm số đơn của mỗi khách trên toàn bộ orders.csv."""
    users = pd.read_csv(path, usecols=["user_id"], dtype={"user_id": "int32"})
    return users["user_id"].value_counts().sort_index()


def basket_size_per_order(path: Path) -> pd.Series:
    """Đếm số item trong từng đơn (số dòng order-product), đọc theo chunk."""
    counts = pd.Series(dtype="int64")
    for chunk in pd.read_csv(
        path,
        usecols=["order_id"],
        dtype={"order_id": "int32"},
        chunksize=CHUNK,
    ):
        counts = counts.add(chunk["order_id"].value_counts(), fill_value=0)
    counts = counts.astype("int32")
    counts.index.name = "order_id"
    return counts


def basket_pairs(orders: pd.DataFrame, basket: pd.Series) -> tuple[pd.DataFrame, int]:
    """Ghép kích thước giỏ vào đơn và lập cặp đơn liên tiếp trong prior.

    Trả về DataFrame cặp (đơn hiện tại -> đơn kế tiếp) và số đơn không có item.
    """
    df = orders[["order_id", "user_id", "order_number"]].merge(
        basket.rename("basket_size"),
        left_on="order_id",
        right_index=True,
        how="left",
    )
    missing = int(df["basket_size"].isna().sum())
    df = df.dropna(subset=["basket_size"])
    df = df.astype({"basket_size": "int16", "order_number": "int16"})
    df = df.sort_values(["user_id", "order_number"], kind="mergesort")

    grouped = df.groupby("user_id", sort=False)
    df["next_size"] = grouped["basket_size"].shift(-1)
    df["next_number"] = grouped["order_number"].shift(-1)
    pairs = df[df["next_number"] == df["order_number"] + 1].dropna(subset=["next_size"])
    pairs = pairs.assign(change=pairs["next_size"].astype("int32") - pairs["basket_size"])
    return pairs, missing


def lag1_correlation(pairs: pd.DataFrame) -> float:
    """Tương quan lag-1 gộp giữa kích thước giỏ của hai đơn liên tiếp."""
    x = pairs["basket_size"].to_numpy(dtype=float)
    y = pairs["next_size"].to_numpy(dtype=float)
    return float(np.corrcoef(x, y)[0, 1])


def summarize(
    opc: pd.Series,
    prior: pd.DataFrame,
    basket: pd.Series,
    pairs: pd.DataFrame,
    missing_orders: int,
    overall_r: float,
) -> dict:
    """Tổng hợp toàn bộ số liệu cho report và JSON."""
    gaps = prior["days_since_prior_order"].dropna()
    dow_share = prior["order_dow"].value_counts(normalize=True).sort_index() * 100
    hour_share = prior["order_hour_of_day"].value_counts(normalize=True).sort_index() * 100
    heat = (
        pd.crosstab(prior["order_dow"], prior["order_hour_of_day"], normalize="all")
        * 100
    )

    change = pairs["change"]
    abs_change = change.abs()

    return {
        "source": {
            "orders_per_customer": "data/orders.csv",
            "timing_and_gaps": "data/orders_prior.csv",
            "basket": "data/order_products__prior.csv",
        },
        "orders_per_customer": {
            "users": int(opc.size),
            "orders": int(opc.sum()),
            "min": int(opc.min()),
            "max": int(opc.max()),
            "mean": round(float(opc.mean()), 4),
            "median": float(opc.median()),
            "q25": float(opc.quantile(0.25)),
            "q75": float(opc.quantile(0.75)),
            "mode": int(opc.mode().iloc[0]),
            "share_le_5_pct": round(float((opc <= 5).mean() * 100), 4),
            "share_le_10_pct": round(float((opc <= 10).mean() * 100), 4),
            "share_gt_50_pct": round(float((opc > 50).mean() * 100), 4),
            "at_cap_100": int((opc == 100).sum()),
        },
        "order_timing": {
            "orders": int(len(prior)),
            "dow_share_pct": {int(k): round(float(v), 4) for k, v in dow_share.items()},
            "hour_share_pct": {int(k): round(float(v), 4) for k, v in hour_share.items()},
            "peak_dow": int(dow_share.idxmax()),
            "peak_dow_share_pct": round(float(dow_share.max()), 4),
            "peak_hour": int(hour_share.idxmax()),
            "peak_hour_share_pct": round(float(hour_share.max()), 4),
            "peak_cell": {
                "dow": int(heat.stack().idxmax()[0]),
                "hour": int(heat.stack().idxmax()[1]),
                "share_pct": round(float(heat.stack().max()), 4),
            },
        },
        "days_since_prior_order": {
            "prior_orders": int(len(prior)),
            "first_orders_nan": int(prior["days_since_prior_order"].isna().sum()),
            "transitions": int(gaps.size),
            "zero_day_transitions": int((gaps == 0).sum()),
            "zero_day_share_pct": round(float((gaps == 0).mean() * 100), 4),
            "mean": round(float(gaps.mean()), 4),
            "median": float(gaps.median()),
            "q25": float(gaps.quantile(0.25)),
            "q75": float(gaps.quantile(0.75)),
            "share_le_7_pct": round(float((gaps <= 7).mean() * 100), 4),
            "share_30_pct": round(float((gaps == 30).mean() * 100), 4),
        },
        "basket_size": {
            "orders": int(basket.size),
            "items": int(basket.sum()),
            "min": int(basket.min()),
            "max": int(basket.max()),
            "mean": round(float(basket.mean()), 4),
            "median": float(basket.median()),
            "q25": float(basket.quantile(0.25)),
            "q75": float(basket.quantile(0.75)),
            "share_size_1_pct": round(float((basket == 1).mean() * 100), 4),
            "share_le_5_pct": round(float((basket <= 5).mean() * 100), 4),
            "share_ge_20_pct": round(float((basket >= 20).mean() * 100), 4),
            "orders_without_items": missing_orders,
        },
        "basket_variation": {
            "consecutive_pairs": int(len(pairs)),
            "mean_abs_change": round(float(abs_change.mean()), 4),
            "median_abs_change": float(abs_change.median()),
            "q75_abs_change": float(abs_change.quantile(0.75)),
            "share_unchanged_pct": round(float((change == 0).mean() * 100), 4),
            "share_increase_pct": round(float((change > 0).mean() * 100), 4),
            "share_decrease_pct": round(float((change < 0).mean() * 100), 4),
            "mean_signed_change": round(float(change.mean()), 4),
            "lag1_r_pooled": round(overall_r, 4),
        },
    }


# ---------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------
def fig_orders_per_customer(opc: pd.Series, stats: dict) -> None:
    """Histogram số khách theo số đơn + ECDF; đánh dấu mốc cắt 100."""
    counts = opc.value_counts().sort_index()
    values = np.sort(opc.to_numpy())
    cap = int(stats["max"])
    n_cap = int((values == cap).sum())

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 2.8), constrained_layout=True)

    colors = [ACCENT if x == cap else PRIMARY for x in counts.index]
    ax1.bar(counts.index.to_numpy(), counts.to_numpy(), width=0.92, color=colors, linewidth=0)
    ax1.set_xlim(1, cap + 3)
    ax1.set_xticks([4, 10, 20, 40, 60, 80, 100])
    ax1.set_xlabel("Số đơn hàng của một khách")
    ax1.set_ylabel("Số khách hàng")
    ax1.annotate(
        f"cắt tại {cap}\n({n_cap:,} khách)".replace(",", "."),
        xy=(cap, n_cap),
        xytext=(cap - 32, counts.max() * 0.55),
        fontsize=6.0,
        color=ACCENT,
        ha="right",
        va="center",
        arrowprops={"arrowstyle": "-", "color": ACCENT, "linewidth": 0.6},
    )
    _panel(ax1, "A")

    ux, ucounts = np.unique(values, return_counts=True)
    ecdf = np.cumsum(ucounts) / values.size * 100
    ax2.step(ux, ecdf, where="post", color=TERTIARY, linewidth=1.2)
    ax2.set_xlim(0, cap + 2)
    ax2.set_ylim(0, 101)
    ax2.set_xticks([0, 20, 40, 60, 80, 100])
    ax2.set_xlabel("Số đơn hàng của một khách")
    ax2.set_ylabel("Tỉ lệ khách hàng tích luỹ (%)")

    for x, name, dy in [
        (stats["median"], f"median = {stats['median']:.0f}", -11),
        (stats["q75"], f"Q3 = {stats['q75']:.0f}", -9),
    ]:
        cy = ecdf[np.searchsorted(ux, x, side="right") - 1]
        ax2.plot([x, x], [0, cy], linestyle=":", color=NEUTRAL, linewidth=0.7)
        ax2.plot([0, x], [cy, cy], linestyle=":", color=NEUTRAL, linewidth=0.7)
        ax2.text(
            x + 3, cy + dy, f"{name} ({cy:.0f}%)",
            fontsize=6.0, color=NEUTRAL, ha="left", va="center",
        )
    _panel(ax2, "B")

    _save(fig, "fig_orders_per_customer")


def fig_order_timing(prior: pd.DataFrame) -> None:
    """Ngày trong tuần, giờ trong ngày và heatmap ngày x giờ."""
    dow_share = prior["order_dow"].value_counts(normalize=True).sort_index() * 100
    hour_share = prior["order_hour_of_day"].value_counts(normalize=True).sort_index() * 100
    heat = pd.crosstab(prior["order_dow"], prior["order_hour_of_day"], normalize="all") * 100

    fig = plt.figure(figsize=(7.2, 5.0), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.25])

    ax1 = fig.add_subplot(gs[0, 0])
    ax1.bar(dow_share.index, dow_share.values, color=PRIMARY, width=0.75)
    for x, v in zip(dow_share.index, dow_share.values):
        ax1.text(x, v + 0.25, f"{v:.1f}", ha="center", va="bottom", fontsize=5.5)
    ax1.set_xlabel("Ngày trong tuần (mã 0–6)")
    ax1.set_ylabel("Tỉ lệ đơn (%)")
    ax1.set_xticks(range(7))
    ax1.set_ylim(0, dow_share.max() * 1.18)
    _panel(ax1, "A")

    ax2 = fig.add_subplot(gs[0, 1])
    ax2.bar(hour_share.index, hour_share.values, color=PRIMARY, width=0.8)
    ax2.set_xlabel("Giờ trong ngày (0–23)")
    ax2.set_ylabel("Tỉ lệ đơn (%)")
    ax2.set_xlim(-0.6, 23.6)
    ax2.set_xticks(range(0, 24, 3))
    ax2.set_ylim(0, hour_share.max() * 1.12)
    peak_hour = int(hour_share.idxmax())
    ax2.annotate(f"peak {peak_hour}:00\n{hour_share.max():.1f}%",
                 xy=(peak_hour, hour_share.max()), xytext=(peak_hour - 8, hour_share.max() * 0.95),
                 fontsize=6, color=SECONDARY,
                 arrowprops={"arrowstyle": "-", "color": SECONDARY, "linewidth": 0.6})
    _panel(ax2, "B")

    ax3 = fig.add_subplot(gs[1, :])
    im = ax3.imshow(heat.values, aspect="auto", origin="lower", cmap="Blues",
                    extent=(-0.5, 23.5, -0.5, 6.5))
    ax3.set_xlabel("Giờ trong ngày")
    ax3.set_ylabel("Ngày trong tuần (mã)")
    ax3.set_xticks(range(0, 24, 3))
    ax3.set_yticks(range(7))
    cb = fig.colorbar(im, ax=ax3, pad=0.01, fraction=0.035)
    cb.set_label("Tỉ lệ đơn trong ô (%)", fontsize=6.5)
    cb.ax.tick_params(labelsize=6)
    cb.outline.set_linewidth(0.4)
    _panel(ax3, "C")

    _save(fig, "fig_order_timing")


def fig_days_since_prior(prior: pd.DataFrame, stats: dict) -> None:
    """Phân phối số ngày kể từ đơn trước (đã loại đơn đầu tiên)."""
    gaps = prior["days_since_prior_order"].dropna()
    share = gaps.value_counts(normalize=True).sort_index() * 100

    fig, ax = plt.subplots(figsize=(3.5, 2.6), constrained_layout=True)
    colors = [SECONDARY if d == 0 else PRIMARY for d in share.index]
    ax.bar(share.index, share.values, color=colors, width=0.8)
    ax.axvline(stats["median"], color=ACCENT, linestyle="--", linewidth=0.8)
    ax.text(stats["median"] + 0.6, share.max() * 0.94, f"median = {stats['median']:.0f} ngày",
            fontsize=6, color=ACCENT)
    ax.set_xlabel("Số ngày kể từ đơn trước")
    ax.set_ylabel("Tỉ lệ chuyển tiếp (%)")
    ax.set_xlim(-1, 31)
    ax.set_xticks([0, 5, 10, 15, 20, 25, 30])
    ax.set_ylim(0, share.max() * 1.12)
    ax.text(10.5, 8.8, "0 ngày = hai đơn\ntrong cùng ngày", fontsize=5.5,
            color=SECONDARY, va="top")
    _save(fig, "fig_days_since_prior")


def fig_basket_size(basket: pd.Series, stats: dict) -> None:
    """Histogram (đuôi phải gộp 60+) và ECDF kích thước giỏ."""
    values = np.sort(basket.to_numpy())
    clipped = np.clip(values, None, 60)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 2.9), constrained_layout=True)

    ax1.hist(clipped, bins=np.arange(0.5, 61.5, 1), color=PRIMARY, edgecolor="white",
             linewidth=0.2)
    ax1.set_xlabel("Số item trong một đơn")
    ax1.set_ylabel("Số đơn hàng")
    ax1.set_xlim(0, 61)
    ax1.set_xticks([1, 5, 10, 20, 30, 40, 50, 60])
    ax1.set_xticklabels(["1", "5", "10", "20", "30", "40", "50", "60+"])
    ax1.axvline(stats["median"], color=SECONDARY, linestyle="--", linewidth=0.8)
    ax1.text(stats["median"] + 0.8, ax1.get_ylim()[1] * 0.9,
             f"median = {stats['median']:.0f}", fontsize=6, color=SECONDARY)
    _panel(ax1, "A")

    ecdf = np.arange(1, values.size + 1) / values.size * 100
    ax2.plot(values, ecdf, color=TERTIARY, linewidth=1.2)
    ax2.set_xlabel("Số item trong một đơn")
    ax2.set_ylabel("Tỉ lệ đơn tích luỹ (%)")
    ax2.set_xlim(0, 61)
    ax2.set_ylim(0, 101)
    ax2.set_xticks([1, 5, 10, 20, 30, 40, 50, 60])
    ax2.set_xticklabels(["1", "5", "10", "20", "30", "40", "50", "60+"])
    for x, label, color, dy in [
        (stats["median"], f"median = {stats['median']:.0f}", SECONDARY, -8),
        (stats["q75"], f"Q3 = {stats['q75']:.0f}", NEUTRAL, -16),
    ]:
        cy = ecdf[np.searchsorted(values, x, side="right") - 1]
        ax2.plot([x, x], [0, cy], color=color, linestyle=":", linewidth=0.7)
        ax2.plot([0, x], [cy, cy], color=color, linestyle=":", linewidth=0.7)
        ax2.text(x + 1.2, cy + dy, f"{label} ({cy:.0f}%)", fontsize=6, color=color, va="top")
    _panel(ax2, "B")

    _save(fig, "fig_basket_size")


def fig_basket_variation(pairs: pd.DataFrame, stats: dict) -> None:
    """Phân phối |thay đổi| và mật độ kích thước giỏ của hai đơn liên tiếp."""
    abs_change = pairs["change"].abs().to_numpy()
    clipped = np.clip(abs_change, None, 20)
    share = np.bincount(clipped, minlength=21) / abs_change.size * 100

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 2.9), constrained_layout=True)

    ax1.bar(np.arange(21), share, color=PRIMARY, width=0.8)
    ax1.set_xlabel("|Thay đổi| số item so với đơn trước")
    ax1.set_ylabel("Tỉ lệ cặp đơn (%)")
    ax1.set_xticks([0, 5, 10, 15, 20])
    ax1.set_xticklabels(["0", "5", "10", "15", "20+"])
    ax1.set_xlim(-0.8, 20.8)
    ax1.axvline(stats["median_abs_change"], color=SECONDARY, linestyle="--", linewidth=0.8)
    ax1.text(stats["median_abs_change"] + 0.3, share.max() * 0.92,
             f"median = {stats['median_abs_change']:.0f}", fontsize=6, color=SECONDARY)
    _panel(ax1, "A")

    x = np.clip(pairs["basket_size"].to_numpy(), None, 40)
    y = np.clip(pairs["next_size"].to_numpy(), None, 40)
    hist, xedges, yedges = np.histogram2d(x, y, bins=[np.arange(0.5, 41.5, 1)] * 2)
    mesh = ax2.pcolormesh(xedges, yedges, hist.T, cmap="Blues",
                          norm=LogNorm(vmin=1))
    ax2.plot([0.5, 40.5], [0.5, 40.5], color=SECONDARY, linestyle="--", linewidth=0.7)
    ax2.set_xlabel("Số item ở đơn hiện tại")
    ax2.set_ylabel("Số item ở đơn kế tiếp")
    ax2.set_xlim(0.5, 40.5)
    ax2.set_ylim(0.5, 40.5)
    ax2.set_xticks([1, 10, 20, 30, 40])
    ax2.set_yticks([1, 10, 20, 30, 40])
    ax2.set_xticklabels(["1", "10", "20", "30", "40+"])
    ax2.set_yticklabels(["1", "10", "20", "30", "40+"])
    ax2.text(2, 37, f"r = {stats['lag1_r_pooled']:.2f}", fontsize=6.5, color=SECONDARY)
    cb = fig.colorbar(mesh, ax=ax2, pad=0.01, fraction=0.045)
    cb.set_label("Số cặp đơn", fontsize=6.5)
    cb.ax.tick_params(labelsize=6)
    cb.outline.set_linewidth(0.4)
    _panel(ax2, "B")

    _save(fig, "fig_basket_variation")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    print("Loading orders ...")
    all_orders = pd.read_csv(DATA / "orders.csv", usecols=["user_id"], dtype={"user_id": "int32"})
    opc = all_orders["user_id"].value_counts().sort_index()

    prior = pd.read_csv(
        DATA / "orders_prior.csv",
        usecols=[
            "order_id",
            "user_id",
            "order_number",
            "order_dow",
            "order_hour_of_day",
            "days_since_prior_order",
        ],
        dtype={
            "order_id": "int32",
            "user_id": "int32",
            "order_number": "int16",
            "order_dow": "int8",
            "order_hour_of_day": "int8",
            "days_since_prior_order": "float32",
        },
    )
    print(f"  orders.csv: {opc.sum():,} dong | orders_prior.csv: {len(prior):,} dong")

    print("Counting basket sizes (order_products__prior.csv) ...")
    basket = basket_size_per_order(DATA / "order_products__prior.csv")
    print(f"  {len(basket):,} don, {int(basket.sum()):,} item")

    pairs, missing_orders = basket_pairs(prior, basket)
    overall_r = lag1_correlation(pairs)

    stats = summarize(opc, prior, basket, pairs, missing_orders, overall_r)
    (DOCS / "behavior_summary.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False))
    print("  -> docs/behavior_summary.json")

    print("Rendering figures ...")
    fig_orders_per_customer(opc, stats["orders_per_customer"])
    fig_order_timing(prior)
    fig_days_since_prior(prior, stats["days_since_prior_order"])
    fig_basket_size(basket, stats["basket_size"])
    fig_basket_variation(pairs, stats["basket_variation"])

    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

"""EDA sản phẩm: độ phổ biến, long-tail, đa dạng và hành vi mua lại.

Sáu đầu ra:
  1. Top sản phẩm theo số đơn chứa sản phẩm.
  2. Top department và aisle theo tỉ lệ đơn.
  3. Phân phối độ phổ biến và long-tail (rank-frequency, Lorenz, Gini).
  4. Số sản phẩm khác nhau trên mỗi khách.
  5. Tỉ lệ mua lại theo sản phẩm.
  6. Tỉ lệ mua lại theo department và aisle.

Nguồn: data/order_products__prior.csv, products.csv, aisles.csv, departments.csv,
orders_prior.csv. Số liệu ghi vào docs/product_summary.json; figure xuất PDF + PNG
300 dpi vào docs/figures/.

Chạy: .venv/bin/python src/eda_products.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

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

SEED = 42  # không dùng random; giữ quy ước tái lập
CHUNK = 4_000_000
PRODUCT_BASE = 100_000  # khoá ghép user_id * PRODUCT_BASE + product_id


def _panel(ax: plt.Axes, letter: str) -> None:
    """Gắn panel label A/B/C in đậm."""
    ax.set_title(letter, loc="left", fontweight="bold", fontsize=8, pad=4)


def _save(fig: plt.Figure, name: str) -> None:
    """Lưu vector PDF và preview PNG 300 dpi."""
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIG / f"{name}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {name}.pdf / {name}.png")


def _short(text: str, width: int = 34) -> str:
    """Rút gọn tên sản phẩm/aisle cho nhãn trục."""
    return text if len(text) <= width else text[: width - 1] + "…"


def load_orders() -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """Đọc orders prior và dựng bảng tra order_id -> user_id / eligible."""
    orders = pd.read_csv(
        DATA / "orders_prior.csv",
        usecols=["order_id", "user_id", "order_number"],
        dtype={"order_id": "int32", "user_id": "int32", "order_number": "int16"},
    )
    max_order = int(orders["order_id"].max())
    user_of_order = np.zeros(max_order + 1, dtype=np.int32)
    eligible = np.zeros(max_order + 1, dtype=bool)
    user_of_order[orders["order_id"].to_numpy()] = orders["user_id"].to_numpy()
    eligible[orders["order_id"].to_numpy()] = orders["order_number"].to_numpy() > 1
    return orders, user_of_order, eligible


def scan_items(
    n_products: int,
    user_of_order: np.ndarray,
    eligible: np.ndarray,
) -> dict:
    """Quét order_products theo chunk, tích luỹ thống kê sản phẩm và user-product."""
    lines = np.zeros(n_products + 1, dtype=np.int64)
    elig = np.zeros(n_products + 1, dtype=np.int64)
    reord = np.zeros(n_products + 1, dtype=np.int64)
    reord_all = np.zeros(n_products + 1, dtype=np.int64)
    uniq_keys: list[np.ndarray] = []

    usecols = ["order_id", "product_id", "reordered"]
    dtypes = {"order_id": "int32", "product_id": "int32", "reordered": "int8"}
    for chunk in pd.read_csv(
        DATA / "order_products__prior.csv",
        usecols=usecols,
        dtype=dtypes,
        chunksize=CHUNK,
    ):
        oid = chunk["order_id"].to_numpy()
        pid = chunk["product_id"].to_numpy()
        rec = chunk["reordered"].to_numpy()

        lines += np.bincount(pid, minlength=n_products + 1)
        reord_all += np.bincount(pid, weights=rec, minlength=n_products + 1).astype(np.int64)

        mask = eligible[oid]
        pid_e = pid[mask]
        rec_e = rec[mask]
        elig += np.bincount(pid_e, minlength=n_products + 1)
        reord += np.bincount(pid_e, weights=rec_e, minlength=n_products + 1).astype(np.int64)

        uid = user_of_order[oid]
        if np.any(uid == 0):
            raise ValueError("Có order_id không ánh xạ được sang user_id")
        uniq_keys.append(np.unique(uid.astype(np.int64) * PRODUCT_BASE + pid))

    keys = np.unique(np.concatenate(uniq_keys))
    users, distinct = np.unique(keys // PRODUCT_BASE, return_counts=True)

    return {
        "lines": lines,
        "eligible": elig,
        "reordered": reord,
        "reordered_all": reord_all,
        "users": users,
        "distinct": distinct,
    }


def build_products(scan: dict, products: pd.DataFrame) -> pd.DataFrame:
    """Ghép thống kê sản phẩm với tên, aisle, department."""
    n = len(products) + 1
    table = pd.DataFrame(
        {
            "product_id": np.arange(n, dtype=np.int32),
            "lines": scan["lines"],
            "eligible_lines": scan["eligible"],
            "reordered": scan["reordered"],
            "reordered_all": scan["reordered_all"],
        }
    )
    table = table[table["lines"] > 0].merge(products, on="product_id", how="left")
    table["reorder_rate"] = np.where(
        table["eligible_lines"] > 0,
        table["reordered"] / table["eligible_lines"],
        np.nan,
    )
    table["share_pct"] = table["lines"] / table["lines"].sum() * 100
    return table


def group_table(products: pd.DataFrame, keys: list[str], names: pd.DataFrame) -> pd.DataFrame:
    """Tổng hợp số đơn và tỉ lệ mua lại theo department/aisle."""
    agg = (
        products.groupby(keys)[["lines", "eligible_lines", "reordered", "reordered_all"]]
        .sum()
        .reset_index()
        .merge(names, on=keys, how="left")
    )
    agg["share_pct"] = agg["lines"] / agg["lines"].sum() * 100
    agg["reorder_rate"] = agg["reordered"] / agg["eligible_lines"]
    agg["reorder_rate_all"] = agg["reordered_all"] / agg["lines"]
    return agg.sort_values("share_pct", ascending=False)


def long_tail_stats(products: pd.DataFrame) -> tuple[dict, np.ndarray, np.ndarray]:
    """Tính Gini, tỉ lệ đơn của nhóm sản phẩm đầu bảng và đường Lorenz."""
    counts = np.sort(products["lines"].to_numpy(dtype=float))
    n = counts.size
    total = counts.sum()
    rank = np.arange(1, n + 1)
    gini = float(2 * np.sum(rank * counts) / (n * total) - (n + 1) / n)

    desc = counts[::-1]
    cum = np.cumsum(desc) / total * 100
    shares = {}
    for pct in (1, 5, 10, 20):
        k = max(1, int(np.ceil(n * pct / 100)))
        shares[f"top_{pct}_pct_share_pct"] = round(float(cum[k - 1]), 4)
    n80 = int(np.searchsorted(cum, 80) + 1)

    stats = {
        "products_with_purchases": int(n),
        "gini": round(gini, 4),
        "products_for_80pct": n80,
        "products_for_80pct_share_pct": round(n80 / n * 100, 4),
        **shares,
    }
    return stats, np.arange(1, n + 1) / n * 100, cum


def diversity_stats(orders: pd.DataFrame, scan: dict) -> tuple[dict, pd.DataFrame]:
    """Thống kê số sản phẩm khác nhau trên mỗi khách."""
    orders_per_user = orders.groupby("user_id").size()
    div = pd.DataFrame({"user_id": scan["users"], "distinct_products": scan["distinct"]})
    div["orders"] = div["user_id"].map(orders_per_user).astype(int)
    div["distinct_per_order"] = div["distinct_products"] / div["orders"]
    div["total_orders"] = div["orders"] + 1  # prior + 1 đơn cuối (train/test)

    bins = [3, 10, 25, 50, 100]
    labels = ["4–10", "11–25", "26–50", "51–100"]
    div["order_group"] = pd.cut(div["total_orders"], bins=bins, labels=labels)
    by_group = (
        div.groupby("order_group", observed=True)
        .agg(
            users=("user_id", "size"),
            median_distinct=("distinct_products", "median"),
            median_per_order=("distinct_per_order", "median"),
        )
        .reset_index()
    )

    stats = {
        "users": int(div.shape[0]),
        "orders_per_user_median": float(div["orders"].median()),
        "distinct_mean": round(float(div["distinct_products"].mean()), 4),
        "distinct_median": float(div["distinct_products"].median()),
        "distinct_q25": float(div["distinct_products"].quantile(0.25)),
        "distinct_q75": float(div["distinct_products"].quantile(0.75)),
        "distinct_min": int(div["distinct_products"].min()),
        "distinct_max": int(div["distinct_products"].max()),
        "distinct_per_order_median": round(float(div["distinct_per_order"].median()), 4),
        "by_order_group": [
            {
                "orders": str(row.order_group),
                "users": int(row.users),
                "median_distinct": float(row.median_distinct),
                "median_per_order": round(float(row.median_per_order), 4),
            }
            for row in by_group.itertuples()
        ],
    }
    return stats, div


def reorder_stats(products: pd.DataFrame, dept: pd.DataFrame, aisle: pd.DataFrame) -> dict:
    """Tỉ lệ mua lại ở mức sản phẩm, department và aisle."""
    total_lines = int(products["lines"].sum())
    total_elig = int(products["eligible_lines"].sum())
    total_reord = int(products["reordered"].sum())
    total_reord_all = int(products["reordered_all"].sum())

    product_rates = products.loc[products["eligible_lines"] >= 100, "reorder_rate"]
    top_products = (
        products[products["eligible_lines"] >= 5000]
        .nlargest(15, "reorder_rate")[["product_name", "lines", "eligible_lines", "reorder_rate"]]
    )
    top_aisles = (
        aisle[aisle["eligible_lines"] >= 10_000]
        .nlargest(15, "reorder_rate")[["aisle", "lines", "eligible_lines", "reorder_rate"]]
    )

    return {
        "lines_all": total_lines,
        "lines_eligible": total_elig,
        "first_order_lines": total_lines - total_elig,
        "overall_reorder_rate_all": round(total_reord_all / total_lines, 4),
        "overall_reorder_rate_eligible": round(total_reord / total_elig, 4),
        "first_order_reordered_lines": total_reord_all - total_reord,
        "products_with_100_lines": int(product_rates.size),
        "product_rate_median": round(float(product_rates.median()), 4),
        "product_rate_q25": round(float(product_rates.quantile(0.25)), 4),
        "product_rate_q75": round(float(product_rates.quantile(0.75)), 4),
        "product_rate_min": round(float(product_rates.min()), 4),
        "product_rate_max": round(float(product_rates.max()), 4),
        "top_products_by_rate": [
            {
                "product": row.product_name,
                "lines": int(row.lines),
                "eligible_lines": int(row.eligible_lines),
                "reorder_rate": round(float(row.reorder_rate), 4),
            }
            for row in top_products.itertuples()
        ],
        "departments": [
            {
                "department": row.department,
                "lines": int(row.lines),
                "eligible_lines": int(row.eligible_lines),
                "share_pct": round(float(row.share_pct), 4),
                "reorder_rate": round(float(row.reorder_rate), 4),
            }
            for row in dept.itertuples()
        ],
        "top_aisles_by_rate": [
            {
                "aisle": row.aisle,
                "lines": int(row.lines),
                "eligible_lines": int(row.eligible_lines),
                "reorder_rate": round(float(row.reorder_rate), 4),
            }
            for row in top_aisles.itertuples()
        ],
    }


# ---------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------
def fig_top_products(products: pd.DataFrame, top: pd.DataFrame) -> None:
    """Top 15 sản phẩm theo số đơn chứa sản phẩm."""
    data = top.sort_values("lines")
    y = np.arange(len(data))
    values = data["lines"].to_numpy() / 1e6

    fig, ax = plt.subplots(figsize=(3.5, 4.2), constrained_layout=True)
    ax.barh(y, values, color=PRIMARY, height=0.72)
    ax.set_yticks(y)
    ax.set_yticklabels([_short(v, 32) for v in data["product_name"]], fontsize=6)
    ax.set_xlabel("Số đơn chứa sản phẩm (triệu)")
    ax.set_xlim(0, values.max() * 1.18)
    for yi, v in zip(y, data["lines"]):
        ax.text(v / 1e6 + values.max() * 0.015, yi, f"{v / 1e6:.2f}M",
                va="center", fontsize=5.5)
    _panel(ax, "A")
    _save(fig, "fig_top_products")


def fig_top_groups(dept: pd.DataFrame, aisle: pd.DataFrame) -> None:
    """Tỉ lệ đơn theo department và top aisle."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 4.2), constrained_layout=True)

    d = dept.sort_values("share_pct")
    y = np.arange(len(d))
    ax1.barh(y, d["share_pct"], color=PRIMARY, height=0.72)
    ax1.set_yticks(y)
    ax1.set_yticklabels(d["department"], fontsize=6)
    ax1.set_xlabel("Tỉ lệ đơn (%)")
    ax1.set_xlim(0, d["share_pct"].max() * 1.22)
    for yi, v in zip(y, d["share_pct"]):
        ax1.text(v + 0.25, yi, f"{v:.1f}", va="center", fontsize=5.5)
    _panel(ax1, "A")

    a = aisle.nlargest(15, "share_pct").sort_values("share_pct")
    y = np.arange(len(a))
    ax2.barh(y, a["share_pct"], color=TERTIARY, height=0.72)
    ax2.set_yticks(y)
    ax2.set_yticklabels([_short(v, 30) for v in a["aisle"]], fontsize=6)
    ax2.set_xlabel("Tỉ lệ đơn (%)")
    ax2.set_xlim(0, a["share_pct"].max() * 1.22)
    for yi, v in zip(y, a["share_pct"]):
        ax2.text(v + 0.03, yi, f"{v:.1f}", va="center", fontsize=5.5)
    _panel(ax2, "B")

    _save(fig, "fig_top_groups")


def fig_longtail(products: pd.DataFrame, stats: dict, lorenz_x: np.ndarray,
                 lorenz_y: np.ndarray) -> None:
    """Rank-frequency (log-log) và đường Lorenz của số đơn theo sản phẩm."""
    counts = np.sort(products["lines"].to_numpy())[::-1]
    ranks = np.arange(1, counts.size + 1)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.0), constrained_layout=True)

    ax1.plot(ranks, counts, color=PRIMARY, linewidth=0.9)
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlabel("Hạng sản phẩm (log)")
    ax1.set_ylabel("Số đơn chứa sản phẩm (log)")
    _panel(ax1, "A")

    ax2.plot(lorenz_x, lorenz_y, color=TERTIARY, linewidth=1.2)
    ax2.plot([0, 100], [0, 100], color=NEUTRAL, linestyle="--", linewidth=0.7)
    for pct, color in [(1, SECONDARY), (10, ACCENT)]:
        share = stats[f"top_{pct}_pct_share_pct"]
        ax2.plot([pct, pct], [0, share], color=color, linestyle=":", linewidth=0.8)
        ax2.plot([0, pct], [share, share], color=color, linestyle=":", linewidth=0.8)
        ax2.text(pct + 2, share + 4, f"top {pct}%: {share:.0f}%", fontsize=6, color=color)
    ax2.set_xlim(0, 100)
    ax2.set_ylim(0, 101)
    ax2.set_xlabel("Tỉ lệ sản phẩm tích luỹ (%)")
    ax2.set_ylabel("Tỉ lệ đơn tích luỹ (%)")
    _panel(ax2, "B")

    _save(fig, "fig_popularity_longtail")


def fig_diversity(div: pd.DataFrame, stats: dict) -> None:
    """Phân phối và ECDF số sản phẩm khác nhau trên mỗi khách."""
    values = np.sort(div["distinct_products"].to_numpy())
    cap = max(50, int(np.ceil(np.quantile(values, 0.99) / 50) * 50))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.0), constrained_layout=True)

    ax1.hist(np.clip(values, None, cap), bins=np.arange(-0.5, cap + 5, 5),
             color=PRIMARY, edgecolor="white", linewidth=0.2)
    ax1.axvline(stats["distinct_median"], color=SECONDARY, linestyle="--", linewidth=0.8)
    ax1.text(stats["distinct_median"] + cap * 0.02, ax1.get_ylim()[1] * 0.92,
             f"median = {stats['distinct_median']:.0f}", fontsize=6, color=SECONDARY)
    ax1.set_xlabel("Số sản phẩm khác nhau của một khách")
    ax1.set_ylabel("Số khách hàng")
    ax1.set_xlim(0, cap)
    ticks = [1] + list(range(50, cap, 50)) + [cap]
    ax1.set_xticks(ticks)
    ax1.set_xticklabels(["1"] + [str(t) for t in ticks[1:-1]] + [f"{cap}+"])
    _panel(ax1, "A")

    ecdf = np.arange(1, values.size + 1) / values.size * 100
    ax2.plot(values, ecdf, color=TERTIARY, linewidth=1.2)
    ax2.set_xlabel("Số sản phẩm khác nhau của một khách")
    ax2.set_ylabel("Tỉ lệ khách hàng tích luỹ (%)")
    ax2.set_xlim(0, cap)
    ax2.set_ylim(0, 101)
    ax2.set_xticks(ticks)
    ax2.set_xticklabels(["1"] + [str(t) for t in ticks[1:-1]] + [f"{cap}+"])
    for x, label, color, dy in [
        (stats["distinct_median"], f"median = {stats['distinct_median']:.0f}", SECONDARY, -9),
        (stats["distinct_q75"], f"Q3 = {stats['distinct_q75']:.0f}", NEUTRAL, -18),
    ]:
        cy = ecdf[np.searchsorted(values, x, side="right") - 1]
        ax2.plot([x, x], [0, cy], color=color, linestyle=":", linewidth=0.8)
        ax2.plot([0, x], [cy, cy], color=color, linestyle=":", linewidth=0.8)
        ax2.text(x + cap * 0.02, cy + dy, f"{label} ({cy:.0f}%)", fontsize=6, color=color)
    _panel(ax2, "B")

    _save(fig, "fig_customer_diversity")


def fig_reorder_products(products: pd.DataFrame, stats: dict) -> None:
    """Phân phối tỉ lệ mua lại theo sản phẩm và top sản phẩm."""
    rates = products.loc[products["eligible_lines"] >= 100, "reorder_rate"] * 100
    top = products.nlargest(15, "lines").sort_values("reorder_rate")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.4), constrained_layout=True)

    counts, _, _ = ax1.hist(rates, bins=np.linspace(0, 100, 41), color=PRIMARY,
                            edgecolor="white", linewidth=0.2)
    ax1.set_ylim(0, counts.max() * 1.16)
    ax1.axvline(stats["product_rate_median"] * 100, color=SECONDARY, linestyle="--",
                linewidth=0.8)
    ax1.text(stats["product_rate_median"] * 100 + 2, counts.max() * 1.05,
             f"median = {stats['product_rate_median'] * 100:.1f}%", fontsize=6,
             color=SECONDARY)
    ax1.set_xlabel("Tỉ lệ mua lại của sản phẩm (%)")
    ax1.set_ylabel("Số sản phẩm")
    ax1.set_xlim(0, 100)
    _panel(ax1, "A")

    y = np.arange(len(top))
    ax2.barh(y, top["reorder_rate"] * 100, color=TERTIARY, height=0.72)
    ax2.set_yticks(y)
    ax2.set_yticklabels([_short(v, 30) for v in top["product_name"]], fontsize=6)
    ax2.set_xlabel("Tỉ lệ mua lại (%)")
    ax2.set_xlim(0, 100)
    for yi, v in zip(y, top["reorder_rate"] * 100):
        ax2.text(v + 1, yi, f"{v:.1f}", va="center", fontsize=5.5)
    _panel(ax2, "B")

    _save(fig, "fig_reorder_products")


def fig_reorder_groups(dept: pd.DataFrame, stats: dict) -> None:
    """Tỉ lệ mua lại theo department và top aisle."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 4.2), constrained_layout=True)

    d = dept.sort_values("reorder_rate")
    y = np.arange(len(d))
    ax1.barh(y, d["reorder_rate"] * 100, color=PRIMARY, height=0.72)
    ax1.set_yticks(y)
    ax1.set_yticklabels(d["department"], fontsize=6)
    ax1.set_xlabel("Tỉ lệ mua lại (%)")
    ax1.set_xlim(0, 100)
    _panel(ax1, "A")

    top = pd.DataFrame(stats["top_aisles_by_rate"]).sort_values("reorder_rate")
    y = np.arange(len(top))
    ax2.barh(y, top["reorder_rate"] * 100, color=TERTIARY, height=0.72)
    ax2.set_yticks(y)
    ax2.set_yticklabels([_short(v, 30) for v in top["aisle"]], fontsize=6)
    ax2.set_xlabel("Tỉ lệ mua lại (%)")
    ax2.set_xlim(0, 100)
    for yi, v in zip(y, top["reorder_rate"] * 100):
        ax2.text(v + 1, yi, f"{v:.1f}", va="center", fontsize=5.5)
    _panel(ax2, "B")

    _save(fig, "fig_reorder_groups")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    print("Loading orders and products ...")
    orders, user_of_order, eligible = load_orders()
    products = pd.read_csv(DATA / "products.csv")
    aisles = pd.read_csv(DATA / "aisles.csv")
    departments = pd.read_csv(DATA / "departments.csv")
    n_products = int(products["product_id"].max())

    print("Scanning order_products__prior.csv ...")
    scan = scan_items(n_products, user_of_order, eligible)
    table = build_products(scan, products)
    dept = group_table(table, ["department_id"], departments)
    aisle = group_table(table, ["aisle_id"], aisles)
    print(f"  {table['lines'].sum():,} dòng, {len(table):,} sản phẩm")

    tail, lorenz_x, lorenz_y = long_tail_stats(table)
    div_stats, div = diversity_stats(orders, scan)
    reorder = reorder_stats(table, dept, aisle)

    stats = {
        "source": {
            "items": "data/order_products__prior.csv",
            "orders": "data/orders_prior.csv",
            "products": "data/products.csv",
            "aisles": "data/aisles.csv",
            "departments": "data/departments.csv",
        },
        "definition": {
            "purchase_count": "số dòng order-product (mỗi đơn tối đa một dòng/sản phẩm)",
            "reorder_rate": "reordered=1 / số dòng thuộc đơn có order_number >= 2",
            "reorder_group": "tổng reordered / tổng dòng eligible (line-weighted)",
        },
        "top_products": [
            {
                "product": row.product_name,
                "aisle": row.aisle,
                "department": row.department,
                "lines": int(row.lines),
                "share_pct": round(float(row.share_pct), 4),
                "reorder_rate": round(float(row.reorder_rate), 4),
            }
            for row in table.nlargest(15, "lines").merge(
                aisles, on="aisle_id", how="left"
            ).merge(departments, on="department_id", how="left").itertuples()
        ],
        "top_departments": [
            {
                "department": row.department,
                "lines": int(row.lines),
                "share_pct": round(float(row.share_pct), 4),
                "reorder_rate": round(float(row.reorder_rate), 4),
            }
            for row in dept.head(10).itertuples()
        ],
        "top_aisles": [
            {
                "aisle": row.aisle,
                "lines": int(row.lines),
                "share_pct": round(float(row.share_pct), 4),
                "reorder_rate": round(float(row.reorder_rate), 4),
            }
            for row in aisle.head(15).itertuples()
        ],
        "long_tail": tail,
        "diversity": div_stats,
        "reorder": reorder,
    }
    (DOCS / "product_summary.json").write_text(
        json.dumps(stats, indent=2, ensure_ascii=False)
    )
    print("  -> docs/product_summary.json")

    print("Rendering figures ...")
    fig_top_products(table, table.nlargest(15, "lines"))
    fig_top_groups(dept, aisle)
    fig_longtail(table, tail, lorenz_x, lorenz_y)
    fig_diversity(div, div_stats)
    fig_reorder_products(table, reorder)
    fig_reorder_groups(dept, reorder)

    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

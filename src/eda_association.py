"""EDA kết hợp: cặp department cùng giỏ và quan hệ giữa support và lift của cặp sản phẩm.

Hai đầu ra:
  1. Ma trận support và lift của 21 department trong đơn prior (Task 29).
  2. Support so với lift của các cặp trong 300 sản phẩm phổ biến nhất (Task 30).

Nguồn: data/order_products__prior.csv, orders_prior.csv, products.csv, departments.csv.
Số liệu ghi vào docs/association_summary.json; figure xuất PDF + PNG 300 dpi.

Chạy: .venv/bin/python src/eda_association.py
"""

from __future__ import annotations

import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from scipy.stats import spearmanr

from eda_cooccurrence import MIN_SUPPORT, N_TOP, cooccurrence, count_products, pair_table
from eda_products import (
    CHUNK,
    DATA,
    DOCS,
    NEUTRAL,
    PRIMARY,
    SECONDARY,
    SEED,
    _panel,
    _save,
)

MM = 1 / 25.4
TOP_RANK = 50  # số cặp có số đơn cao nhất cho panel B của Figure support–lift


def department_presence(products: pd.DataFrame, max_order: int) -> tuple[np.ndarray, list[str]]:
    """Ma trận bool (đơn × department) cho biết đơn có sản phẩm thuộc department hay không."""
    dept_of = np.zeros(int(products["product_id"].max()) + 1, dtype=np.int16)
    dept_of[products["product_id"].to_numpy()] = products["department_id"].to_numpy()
    ids = sorted(products["department_id"].unique())
    col_of = {d: i for i, d in enumerate(ids)}
    present = np.zeros((len(ids), max_order + 1), dtype=bool)
    for chunk in pd.read_csv(
        DATA / "order_products__prior.csv",
        usecols=["order_id", "product_id"],
        dtype={"order_id": "int32", "product_id": "int32"},
        chunksize=CHUNK,
    ):
        oid = chunk["order_id"].to_numpy()
        did = dept_of[chunk["product_id"].to_numpy()]
        for d, i in col_of.items():
            present[i, oid[did == d]] = True
    return present, ids


def department_cooccurrence(present: np.ndarray, order_ids: np.ndarray) -> np.ndarray:
    """Số đơn chứa cả hai department (đường chéo là số đơn chứa department)."""
    x = present[:, order_ids].astype(np.float32)
    return np.rint(x @ x.T).astype(np.int64)


def support_lift(co: np.ndarray, n_orders: int) -> tuple[np.ndarray, np.ndarray]:
    """Support (%) và lift từ ma trận đồng xuất hiện."""
    n = np.diag(co).astype(float)
    support = co / n_orders * 100
    lift = co * n_orders / np.outer(n, n)
    return support, lift


def _heatmap(ax: plt.Axes, matrix: np.ndarray, names: list[str], cmap, norm, label: str,
             fig: plt.Figure) -> None:
    """Vẽ heatmap vuông 21 × 21, ẩn đường chéo, nhãn ở trục."""
    data = np.ma.masked_array(matrix, mask=np.eye(len(names), dtype=bool))
    im = ax.imshow(data, cmap=cmap, norm=norm)
    ax.set_xticks(range(len(names)), names, rotation=90)
    ax.set_yticks(range(len(names)), names)
    ax.tick_params(length=1.5, labelsize=5.5)
    for sp in ax.spines.values():
        sp.set_visible(False)
    cb = fig.colorbar(im, ax=ax, location="bottom", pad=0.02, fraction=0.04)
    cb.set_label(label, fontsize=6)
    cb.ax.tick_params(labelsize=5.5)


def fig_department_pairs(support: np.ndarray, lift: np.ndarray, names: list[str]) -> None:
    """Heatmap support và lift giữa các department."""
    seq = LinearSegmentedColormap.from_list("seq", ["#FFFFFF", PRIMARY])
    div = LinearSegmentedColormap.from_list("div", [SECONDARY, "#FFFFFF", PRIMARY])
    off = ~np.eye(len(names), dtype=bool)
    lo, hi = float(lift[off].min()), float(lift[off].max())
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(183 * MM, 100 * MM), constrained_layout=True)
    _heatmap(ax1, support, names, seq, None, "Đơn chứa cả hai department (% đơn prior)", fig)
    _panel(ax1, "A")
    _heatmap(ax2, lift, names, div, TwoSlopeNorm(1.0, vmin=min(lo, 0.99), vmax=max(hi, 1.01)),
             "Lift", fig)
    _panel(ax2, "B")
    _save(fig, "fig_department_pairs")


def fig_support_lift(table: pd.DataFrame, top: pd.DataFrame) -> None:
    """Support so với lift của cặp sản phẩm; lift theo hạng số đơn chứa cả hai."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(183 * MM, 70 * MM), constrained_layout=True)
    ax1.scatter(table["support_pct"], table["lift"], s=2.5, color=NEUTRAL, alpha=0.35,
                linewidths=0)
    top15 = top.head(15)
    ax1.scatter(top15["support_pct"], top15["lift"], s=5, color=SECONDARY, linewidths=0)
    ax1.axhline(1, color="black", lw=0.6, ls="--")
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlabel("Support của cặp (% đơn, thang log)")
    ax1.set_ylabel("Lift (thang log)")
    _panel(ax1, "A")

    ax2.plot(np.arange(1, len(top) + 1), top["lift"], "o", color=PRIMARY, ms=2.8)
    ax2.axhline(1, color="black", lw=0.6, ls="--")
    ax2.set_xlabel(f"Hạng theo số đơn chứa cả hai (top {len(top)})")
    ax2.set_ylabel("Lift")
    ax2.set_ylim(0, None)
    _panel(ax2, "B")
    _save(fig, "fig_support_vs_lift")


def main() -> None:
    orders = pd.read_csv(DATA / "orders_prior.csv", usecols=["order_id"],
                         dtype={"order_id": "int32"})
    order_ids = orders["order_id"].to_numpy()
    n_orders = int(order_ids.size)
    max_order = int(order_ids.max())

    products = pd.read_csv(DATA / "products.csv",
                           usecols=["product_id", "product_name", "aisle_id", "department_id"])
    depts = pd.read_csv(DATA / "departments.csv").set_index("department_id")["department"]

    print("Department co-occurrence ...")
    present, ids = department_presence(products, max_order)
    co = department_cooccurrence(present, order_ids)
    support, lift = support_lift(co, n_orders)
    share = np.diag(co) / n_orders * 100
    order = np.argsort(-share)
    names = [depts[ids[i]] for i in order]
    co_o, support_o, lift_o = (m[np.ix_(order, order)] for m in (co, support, lift))

    iu = np.triu_indices(len(names), k=1)
    pairs = pd.DataFrame(
        {"department_a": [names[i] for i in iu[0]], "department_b": [names[j] for j in iu[1]],
         "orders_both": co_o[iu], "support_pct": support_o[iu], "lift": lift_o[iu]}
    )

    print("Product co-occurrence ...")
    max_product = int(products["product_id"].max())
    counts = count_products(max_product)
    top_ids = (np.argsort(counts[1:])[::-1][:N_TOP] + 1).astype(np.int32)
    co_p, top_counts = cooccurrence(top_ids, max_product, max_order)
    table = pair_table(co_p, top_counts, top_ids, products, n_orders)
    eligible = table[table["support_pct"] >= MIN_SUPPORT * 100]
    top = table.nlargest(TOP_RANK, "orders_both")
    rho_all = spearmanr(table["support_pct"], table["lift"])
    rho_elig = spearmanr(eligible["support_pct"], eligible["lift"])

    def rec(df: pd.DataFrame) -> list[dict]:
        return [
            {k: (round(float(v), 4) if isinstance(v, float | np.floating) else
                 (int(v) if isinstance(v, np.integer) else v))
             for k, v in row.items()}
            for row in df.to_dict(orient="records")
        ]

    stats = {
        "source": ["data/order_products__prior.csv", "data/orders_prior.csv",
                   "data/products.csv", "data/departments.csv"],
        "seed": SEED,
        "orders": n_orders,
        "department_order_share_pct": {n: round(float(share[i]), 4)
                                       for n, i in zip(names, order)},
        "department_pairs": len(pairs),
        "department_top_pairs_by_support": rec(pairs.nlargest(10, "orders_both")),
        "department_top_pairs_by_lift": rec(pairs.nlargest(10, "lift")),
        "department_lift_range": [round(float(pairs["lift"].min()), 4),
                                  round(float(pairs["lift"].max()), 4)],
        "department_pairs_lift_gt_1": int((pairs["lift"] > 1).sum()),
        "product_pairs": {
            "products": N_TOP,
            "pairs": int(len(table)),
            "pairs_min_support": int(len(eligible)),
            "min_support_pct": MIN_SUPPORT * 100,
            "spearman_support_lift_all": [round(float(rho_all.statistic), 4),
                                          float(rho_all.pvalue)],
            "spearman_support_lift_min_support": [round(float(rho_elig.statistic), 4),
                                                  float(rho_elig.pvalue)],
            "top_rank_pairs": TOP_RANK,
            "top_rank_lift_min": round(float(top["lift"].min()), 4),
            "top_rank_lift_max": round(float(top["lift"].max()), 4),
            "top_rank_lift_gt_1": int((top["lift"] > 1).sum()),
            "top15_lift_min": round(float(top["lift"].head(15).min()), 4),
            "top15_lift_max": round(float(top["lift"].head(15).max()), 4),
            "lift_gt_1_all": int((table["lift"] > 1).sum()),
        },
    }
    (DOCS / "association_summary.json").write_text(
        json.dumps(stats, indent=2, ensure_ascii=False))
    print("  -> docs/association_summary.json")

    print("Rendering figures ...")
    fig_department_pairs(support_o, lift_o, names)
    fig_support_lift(eligible, top)
    print(json.dumps(stats["product_pairs"], indent=2))


if __name__ == "__main__":
    main()

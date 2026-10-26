"""Các cặp sản phẩm xuất hiện cùng nhau trong đơn prior.

Giới hạn ở 300 sản phẩm có số đơn cao nhất để tính ma trận đồng xuất hiện
đầy đủ. Với mỗi cặp:
  support    = số đơn chứa cả hai / tổng số đơn prior
  confidence = P(B | A) hoặc P(A | B)
  lift       = support(A, B) / (support(A) * support(B))

Output: docs/cooccurrence_summary.json, Figure 16.
Chạy: .venv/bin/python src/eda_cooccurrence.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import sparse

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

SEED = 42
CHUNK = 4_000_000
N_TOP = 300
MIN_SUPPORT = 0.0005  # 0,05% số đơn prior, dùng cho bảng xếp hạng lift


def _panel(ax: plt.Axes, letter: str) -> None:
    """Gắn panel label in đậm."""
    ax.set_title(letter, loc="left", fontweight="bold", fontsize=8, pad=4)


def _save(fig: plt.Figure, name: str) -> None:
    """Lưu PDF vector và PNG 300 dpi."""
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIG / f"{name}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {name}.pdf / {name}.png")


def _short(text: str, width: int = 42) -> str:
    """Rút gọn tên sản phẩm cho nhãn trục."""
    return text if len(text) <= width else text[: width - 1] + "…"


def count_products(max_product: int) -> np.ndarray:
    """Đếm số đơn chứa từng sản phẩm trong prior."""
    counts = np.zeros(max_product + 1, dtype=np.int64)
    for chunk in pd.read_csv(
        DATA / "order_products__prior.csv",
        usecols=["product_id"],
        dtype={"product_id": "int32"},
        chunksize=CHUNK,
    ):
        counts += np.bincount(
            chunk["product_id"].to_numpy(), minlength=max_product + 1
        )
    return counts


def cooccurrence(
    top_ids: np.ndarray,
    max_product: int,
    max_order: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Tính ma trận đồng xuất hiện và số đơn của từng sản phẩm top."""
    lookup = np.full(max_product + 1, -1, dtype=np.int16)
    lookup[top_ids] = np.arange(top_ids.size, dtype=np.int16)
    co = np.zeros((top_ids.size, top_ids.size), dtype=np.int64)
    counts = np.zeros(top_ids.size, dtype=np.int64)

    for chunk in pd.read_csv(
        DATA / "order_products__prior.csv",
        usecols=["order_id", "product_id"],
        dtype={"order_id": "int32", "product_id": "int32"},
        chunksize=CHUNK,
    ):
        oid = chunk["order_id"].to_numpy()
        pid = chunk["product_id"].to_numpy()
        idx = lookup[pid]
        mask = idx >= 0
        if not mask.any():
            continue

        oid = oid[mask]
        idx = idx[mask]
        counts += np.bincount(idx, minlength=top_ids.size)
        mat = sparse.coo_matrix(
            (np.ones(idx.size, dtype=np.int32), (oid, idx)),
            shape=(max_order + 1, top_ids.size),
        ).tocsr()
        co += np.asarray((mat.T @ mat).todense(), dtype=np.int64)

    return co, counts


def pair_table(
    co: np.ndarray,
    counts: np.ndarray,
    top_ids: np.ndarray,
    products: pd.DataFrame,
    n_orders: int,
) -> pd.DataFrame:
    """Tạo bảng cặp với support, confidence hai chiều và lift."""
    iu = np.triu_indices(top_ids.size, k=1)
    pair_count = co[iu]
    ci = counts[iu[0]]
    cj = counts[iu[1]]
    info = products.set_index("product_id")
    names = info["product_name"]
    aisles = info["aisle_id"]

    table = pd.DataFrame(
        {
            "product_a": names.loc[top_ids[iu[0]]].to_numpy(),
            "product_b": names.loc[top_ids[iu[1]]].to_numpy(),
            "aisle_a": aisles.loc[top_ids[iu[0]]].to_numpy(),
            "aisle_b": aisles.loc[top_ids[iu[1]]].to_numpy(),
            "orders_both": pair_count,
            "support_pct": pair_count / n_orders * 100,
            "confidence_a_to_b_pct": pair_count / ci * 100,
            "confidence_b_to_a_pct": pair_count / cj * 100,
            "lift": pair_count * n_orders / (ci * cj),
        }
    )
    return table


def select_diverse(
    table: pd.DataFrame,
    n: int = 15,
    max_per_product: int = 1,
    max_per_aisle: int = 3,
) -> pd.DataFrame:
    """Chọn top lift nhưng giới hạn lặp sản phẩm/aisle để figure dễ đọc."""
    selected = []
    product_deg: dict[str, int] = {}
    aisle_deg: dict[int, int] = {}
    for row in table.sort_values("lift", ascending=False).itertuples():
        if product_deg.get(row.product_a, 0) >= max_per_product:
            continue
        if product_deg.get(row.product_b, 0) >= max_per_product:
            continue
        pair_aisles = {row.aisle_a, row.aisle_b}
        if any(aisle_deg.get(a, 0) >= max_per_aisle for a in pair_aisles):
            continue
        selected.append(row)
        product_deg[row.product_a] = product_deg.get(row.product_a, 0) + 1
        product_deg[row.product_b] = product_deg.get(row.product_b, 0) + 1
        for a in pair_aisles:
            aisle_deg[a] = aisle_deg.get(a, 0) + 1
        if len(selected) == n:
            break
    return pd.DataFrame(selected)


def fig_pairs(top_count: pd.DataFrame, top_lift: pd.DataFrame) -> None:
    """Top cặp theo số đơn cùng xuất hiện và theo lift."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 4.8), constrained_layout=True)

    data = top_count.sort_values("orders_both")
    y = np.arange(len(data))
    ax1.barh(y, data["orders_both"] / 1e3, color=PRIMARY, height=0.72)
    ax1.set_yticks(y)
    ax1.set_yticklabels(
        [_short(f"{a} + {b}", 40) for a, b in zip(data["product_a"], data["product_b"])],
        fontsize=6,
    )
    ax1.set_xlabel("Số đơn chứa cả hai sản phẩm (nghìn)")
    ax1.set_xlim(0, data["orders_both"].max() / 1e3 * 1.2)
    for yi, v, s in zip(y, data["orders_both"] / 1e3, data["support_pct"]):
        ax1.text(v + data["orders_both"].max() / 1e3 * 0.015, yi, f"{v:.0f} ({s:.2f}%)",
                 va="center", fontsize=5.5)
    _panel(ax1, "A")

    data = top_lift.sort_values("lift")
    y = np.arange(len(data))
    ax2.barh(y, data["lift"], color=TERTIARY, height=0.72)
    ax2.set_yticks(y)
    ax2.set_yticklabels(
        [_short(f"{a} + {b}", 40) for a, b in zip(data["product_a"], data["product_b"])],
        fontsize=6,
    )
    ax2.set_xlabel("Lift")
    ax2.set_xlim(0, data["lift"].max() * 1.22)
    for yi, v, s in zip(y, data["lift"], data["support_pct"]):
        ax2.text(v + data["lift"].max() * 0.015, yi, f"{v:.2f} ({s:.2f}%)",
                 va="center", fontsize=5.5)
    _panel(ax2, "B")

    _save(fig, "fig_product_pairs")


def _records(df: pd.DataFrame, n: int) -> list[dict]:
    """Chuyển top n dòng sang list dict gọn cho JSON."""
    out = []
    for row in df.head(n).itertuples():
        out.append(
            {
                "product_a": row.product_a,
                "product_b": row.product_b,
                "orders_both": int(row.orders_both),
                "support_pct": round(float(row.support_pct), 4),
                "confidence_a_to_b_pct": round(float(row.confidence_a_to_b_pct), 4),
                "confidence_b_to_a_pct": round(float(row.confidence_b_to_a_pct), 4),
                "lift": round(float(row.lift), 4),
            }
        )
    return out


def main() -> None:
    print("Counting products ...")
    products = pd.read_csv(
        DATA / "products.csv",
        usecols=["product_id", "product_name", "aisle_id", "department_id"],
    )
    max_product = int(products["product_id"].max())
    counts = count_products(max_product)
    top_ids = np.argsort(counts[1:])[::-1][:N_TOP] + 1
    top_ids = top_ids.astype(np.int32)

    orders = pd.read_csv(
        DATA / "orders_prior.csv", usecols=["order_id"], dtype={"order_id": "int32"}
    )
    max_order = int(orders["order_id"].max())
    n_orders = int(orders.shape[0])

    print(f"Computing co-occurrence for {N_TOP} products ...")
    co, top_counts = cooccurrence(top_ids, max_product, max_order)
    diagonal = np.diag(co)
    if not np.array_equal(diagonal, top_counts):
        print(f"  warning: diagonal khác count ở {(diagonal != top_counts).sum()} sản phẩm")
    if not np.array_equal(np.sort(top_counts)[::-1], counts[top_ids]):
        print("  warning: count top không khớp lần đếm đầu")

    table = pair_table(co, top_counts, top_ids, products, n_orders)
    eligible = table[table["support_pct"] >= MIN_SUPPORT * 100]
    top_count = table.nlargest(15, "orders_both")
    top_lift = select_diverse(eligible, n=15, max_per_product=1, max_per_aisle=3)

    stats = {
        "definition": {
            "orders": "đơn prior; mỗi sản phẩm tối đa một dòng mỗi đơn",
            "n_orders": n_orders,
            "products_scope": f"{N_TOP} sản phẩm có số đơn cao nhất",
            "support": "số đơn chứa cả hai / tổng số đơn prior",
            "confidence_a_to_b": "P(B | A) = số đơn chứa cả hai / số đơn chứa A",
            "lift": "support(A,B) / (support(A) * support(B))",
            "min_support_pct_for_lift": MIN_SUPPORT * 100,
            "lift_selection": "top lift, mỗi sản phẩm tối đa 1 cặp và mỗi aisle tối đa 3 cặp",
        },
        "n_products": N_TOP,
        "n_pairs_evaluated": int(table.shape[0]),
        "n_pairs_min_support": int(eligible.shape[0]),
        "top_products": [
            {
                "product": products.set_index("product_id").loc[int(pid), "product_name"],
                "orders": int(counts[pid]),
                "share_pct": round(float(counts[pid] / n_orders * 100), 4),
            }
            for pid in top_ids[:15]
        ],
        "top_pairs_by_count": _records(top_count, 15),
        "top_pairs_by_lift": _records(top_lift, 15),
    }
    (DOCS / "cooccurrence_summary.json").write_text(
        json.dumps(stats, indent=2, ensure_ascii=False)
    )
    print("  -> docs/cooccurrence_summary.json")

    print("Rendering figure ...")
    fig_pairs(top_count, top_lift)
    print(json.dumps(stats["top_pairs_by_count"][:5], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

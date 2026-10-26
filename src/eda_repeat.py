"""Tần suất mua, recency và xác suất mua lại ở đơn kế tiếp.

Mẫu: 131.209 khách có đơn `train`. Với mỗi cặp (khách, sản phẩm) đã mua
trong `prior`, đo:
  - tần suất = số đơn prior chứa sản phẩm;
  - recency = số đơn giữa lần mua cuối trong prior và đơn train;
  - mua lại = sản phẩm có mặt trong đơn train (đơn ngay sau prior).

Cách này tránh dùng cờ `reordered` như một biến dự báo, vì cờ này chỉ cho
biết sản phẩm đã từng được mua trước đó.

Output: docs/repeat_summary.json, Figure 14–15.
Chạy: .venv/bin/python src/eda_repeat.py
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

SEED = 42
CHUNK = 4_000_000
PRODUCT_BASE = 100_000

FREQ_EDGES = [1, 2, 3, 4, 5, 10, 20, 101]
FREQ_LABELS = ["1", "2", "3", "4", "5–9", "10–19", "20+"]
REC_EDGES = [0, 1, 2, 3, 5, 10, 20, 101]
REC_LABELS = ["0", "1", "2", "3–4", "5–9", "10–19", "20+"]


def _panel(ax: plt.Axes, letter: str) -> None:
    """Gắn panel label in đậm."""
    ax.set_title(letter, loc="left", fontweight="bold", fontsize=8, pad=4)


def _save(fig: plt.Figure, name: str) -> None:
    """Lưu PDF vector và PNG 300 dpi."""
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIG / f"{name}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {name}.pdf / {name}.png")


def _bucket_table(
    values: np.ndarray,
    labels: np.ndarray,
    edges: list[int],
    names: list[str],
) -> list[dict]:
    """Tính n và tỉ lệ positive theo các khoảng giá trị."""
    idx = np.digitize(values, edges[1:-1], right=False)
    n = np.bincount(idx, minlength=len(names))
    pos = np.bincount(idx, weights=labels.astype(float), minlength=len(names))
    return [
        {
            "bucket": name,
            "n": int(n[i]),
            "positives": int(pos[i]),
            "rate_pct": round(float(pos[i] / n[i] * 100), 4) if n[i] else None,
        }
        for i, name in enumerate(names)
    ]


def load_orders() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
]:
    """Đọc orders và dựng bảng tra order/user/order_number."""
    prior = pd.read_csv(
        DATA / "orders_prior.csv",
        usecols=["order_id", "user_id", "order_number"],
        dtype={"order_id": "int32", "user_id": "int32", "order_number": "int16"},
    )
    train = pd.read_csv(
        DATA / "orders_train.csv",
        usecols=["order_id", "user_id", "order_number"],
        dtype={"order_id": "int32", "user_id": "int32", "order_number": "int16"},
    )
    max_order = int(max(prior["order_id"].max(), train["order_id"].max()))
    max_user = int(max(prior["user_id"].max(), train["user_id"].max()))

    user_of_order = np.zeros(max_order + 1, dtype=np.int32)
    onum_of_order = np.zeros(max_order + 1, dtype=np.int16)
    for orders in (prior, train):
        oid = orders["order_id"].to_numpy()
        user_of_order[oid] = orders["user_id"].to_numpy()
        onum_of_order[oid] = orders["order_number"].to_numpy()

    is_train_user = np.zeros(max_user + 1, dtype=bool)
    target_onum = np.zeros(max_user + 1, dtype=np.int16)
    train_uid = train["user_id"].to_numpy()
    is_train_user[train_uid] = True
    target_onum[train_uid] = train["order_number"].to_numpy()

    last_prior = prior.groupby("user_id")["order_number"].max()
    joined = train.set_index("user_id")["order_number"].to_frame("target").join(last_prior)
    if not (joined["target"] == joined["order_number"] + 1).all():
        raise ValueError("Đơn train không phải đơn ngay sau prior")

    return prior, train, user_of_order, onum_of_order, is_train_user, target_onum, joined


def scan_pairs(
    user_of_order: np.ndarray,
    onum_of_order: np.ndarray,
    is_train_user: np.ndarray,
) -> dict:
    """Quét prior, gom số lần mua và lần mua cuối cho từng cặp khách–sản phẩm."""
    keys_list: list[np.ndarray] = []
    count_list: list[np.ndarray] = []
    last_list: list[np.ndarray] = []

    for chunk in pd.read_csv(
        DATA / "order_products__prior.csv",
        usecols=["order_id", "product_id"],
        dtype={"order_id": "int32", "product_id": "int32"},
        chunksize=CHUNK,
    ):
        oid = chunk["order_id"].to_numpy()
        pid = chunk["product_id"].to_numpy()
        uid = user_of_order[oid]
        mask = is_train_user[uid]
        if not mask.any():
            continue

        uid = uid[mask]
        pid = pid[mask]
        onum = onum_of_order[oid[mask]]
        key = uid.astype(np.int64) * PRODUCT_BASE + pid

        order = np.argsort(key, kind="stable")
        key = key[order]
        onum = onum[order]
        starts = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
        keys_list.append(key[starts])
        count_list.append(np.diff(np.r_[starts, key.size]).astype(np.int32))
        last_list.append(np.maximum.reduceat(onum, starts).astype(np.int16))

    keys = np.concatenate(keys_list)
    freq = np.concatenate(count_list)
    last = np.concatenate(last_list)
    del keys_list, count_list, last_list

    order = np.argsort(keys, kind="stable")
    keys = keys[order]
    freq = freq[order]
    last = last[order]
    starts = np.flatnonzero(np.r_[True, keys[1:] != keys[:-1]])
    keys = keys[starts]
    freq = np.add.reduceat(freq, starts)
    last = np.maximum.reduceat(last, starts)

    return {"keys": keys, "freq": freq, "last": last}


def load_target_keys(user_of_order: np.ndarray) -> tuple[np.ndarray, int]:
    """Tập khoá (khách, sản phẩm) và tổng số dòng trong các đơn train."""
    items = pd.read_csv(
        DATA / "order_products__train.csv",
        usecols=["order_id", "product_id"],
        dtype={"order_id": "int32", "product_id": "int32"},
    )
    uid = user_of_order[items["order_id"].to_numpy()]
    key = uid.astype(np.int64) * PRODUCT_BASE + items["product_id"].to_numpy()
    return np.unique(key), int(items.shape[0])


def mark_target(keys: np.ndarray, target_keys: np.ndarray) -> np.ndarray:
    """Đánh dấu cặp (khách, sản phẩm) có mặt trong đơn train."""
    labels = np.zeros(keys.size, dtype=bool)
    for start in range(0, keys.size, 2_000_000):
        end = min(start + 2_000_000, keys.size)
        pos = np.searchsorted(target_keys, keys[start:end])
        pos = np.clip(pos, 0, target_keys.size - 1)
        labels[start:end] = target_keys[pos] == keys[start:end]
    return labels


def compute_stats(
    pairs: dict,
    labels: np.ndarray,
    target_onum: np.ndarray,
    max_product: int,
    products: pd.DataFrame,
    n_train_items: int,
) -> tuple[dict, pd.DataFrame]:
    """Tổng hợp phân phối tần suất, recency và xác suất mua lại."""
    keys = pairs["keys"]
    freq = pairs["freq"]
    last = pairs["last"]

    users = (keys // PRODUCT_BASE).astype(np.int32)
    recency = target_onum[users].astype(np.int32) - last.astype(np.int32) - 1
    if recency.min() < 0:
        raise ValueError("Recency âm: kiểm tra thứ tự đơn")

    n_pairs = int(keys.size)
    overall_rate = float(labels.mean() * 100)

    freq_bins = np.bincount(freq, minlength=101)
    freq_hist = []
    for k in range(1, 10):
        freq_hist.append({"purchases": str(k), "pairs": int(freq_bins[k]),
                          "share_pct": round(float(freq_bins[k] / n_pairs * 100), 4)})
    freq_hist.append({"purchases": "10+", "pairs": int(freq_bins[10:].sum()),
                      "share_pct": round(float(freq_bins[10:].sum() / n_pairs * 100), 4)})

    rec_bins = np.bincount(recency, minlength=101)
    rec_hist = []
    for k in range(0, 10):
        rec_hist.append({"orders_since_last": str(k), "pairs": int(rec_bins[k]),
                         "share_pct": round(float(rec_bins[k] / n_pairs * 100), 4)})
    rec_hist.append({"orders_since_last": "10+", "pairs": int(rec_bins[10:].sum()),
                     "share_pct": round(float(rec_bins[10:].sum() / n_pairs * 100), 4)})

    by_freq = _bucket_table(freq, labels, FREQ_EDGES, FREQ_LABELS)
    by_rec = _bucket_table(recency, labels, REC_EDGES, REC_LABELS)

    freq_group = np.where(freq == 1, 0, np.where(freq <= 4, 1, 2))
    cross = []
    for gi, gname in enumerate(["1", "2–4", "5+"]):
        sub = freq_group == gi
        rows = _bucket_table(recency[sub], labels[sub], REC_EDGES, REC_LABELS)
        cross.append({"prior_purchases": gname, "pairs": int(sub.sum()), "by_recency": rows})

    prod = (keys % PRODUCT_BASE).astype(np.int32)
    buyers = np.bincount(prod, minlength=max_product + 1)
    pos = np.bincount(prod, weights=labels.astype(float), minlength=max_product + 1)
    prod_table = pd.DataFrame(
        {
            "product_id": np.arange(max_product + 1, dtype=np.int32),
            "buyers": buyers,
            "repurchases": pos.astype(np.int64),
        }
    )
    prod_table = prod_table[prod_table["buyers"] > 0].merge(products, on="product_id", how="left")
    prod_table["next_rate"] = prod_table["repurchases"] / prod_table["buyers"]
    top_volume = prod_table.nlargest(15, "buyers")
    top_rate = prod_table[prod_table["buyers"] >= 500].nlargest(15, "next_rate")

    stats = {
        "definition": {
            "sample": "khách có đơn train; cặp (khách, sản phẩm) đã mua trong prior",
            "frequency": "số đơn prior chứa sản phẩm",
            "recency": "số đơn giữa lần mua cuối trong prior và đơn train",
            "repurchase": "sản phẩm có mặt trong đơn train (đơn ngay sau prior)",
        },
        "sample": {
            "train_users": int(np.unique(users).size),
            "pairs": n_pairs,
            "prior_purchases": int(freq.sum()),
            "repurchased_items": int(labels.sum()),
            "train_items": n_train_items,
            "repurchase_share_of_train_items_pct": round(
                float(labels.sum() / n_train_items * 100), 4
            ),
            "repurchases_per_order": round(float(labels.sum() / np.unique(users).size), 4),
            "overall_repurchase_rate_pct": round(overall_rate, 4),
        },
        "frequency": {
            "median": float(np.median(freq)),
            "q25": float(np.quantile(freq, 0.25)),
            "q75": float(np.quantile(freq, 0.75)),
            "share_ge2_pct": round(float((freq >= 2).mean() * 100), 4),
            "share_ge5_pct": round(float((freq >= 5).mean() * 100), 4),
            "histogram": freq_hist,
            "by_bucket": by_freq,
        },
        "recency": {
            "median_orders": float(np.median(recency)),
            "mean_orders": round(float(recency.mean()), 4),
            "q25_orders": float(np.quantile(recency, 0.25)),
            "q75_orders": float(np.quantile(recency, 0.75)),
            "share_zero_pct": round(float((recency == 0).mean() * 100), 4),
            "histogram": rec_hist,
            "by_bucket": by_rec,
            "by_frequency_group": cross,
        },
        "by_frequency": by_freq,
        "by_recency": by_rec,
        "top_products_by_volume": [
            {
                "product": row.product_name,
                "buyers": int(row.buyers),
                "next_order_rate_pct": round(float(row.next_rate * 100), 4),
            }
            for row in top_volume.itertuples()
        ],
        "top_products_by_next_rate": [
            {
                "product": row.product_name,
                "buyers": int(row.buyers),
                "next_order_rate_pct": round(float(row.next_rate * 100), 4),
            }
            for row in top_rate.itertuples()
        ],
    }
    return stats, prod_table


def fig_frequency(stats: dict) -> None:
    """Phân phối tần suất và xác suất mua lại theo tần suất."""
    hist = stats["frequency"]["histogram"]
    x = np.arange(len(hist))
    shares = np.array([row["share_pct"] for row in hist])
    buckets = stats["by_frequency"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.1), constrained_layout=True)

    ax1.bar(x, shares, color=PRIMARY, width=0.72)
    ax1.set_xticks(x)
    ax1.set_xticklabels([row["purchases"] for row in hist])
    ax1.set_xlabel("Số lần mua trong prior")
    ax1.set_ylabel("Tỉ lệ cặp khách–sản phẩm (%)")
    ax1.set_ylim(0, shares.max() * 1.22)
    for xi, v in zip(x, shares):
        ax1.text(xi, v + shares.max() * 0.02, f"{v:.1f}", ha="center", fontsize=5.5)
    _panel(ax1, "A")

    xs = np.arange(len(buckets))
    rates = np.array([b["rate_pct"] for b in buckets])
    ax2.plot(xs, rates, color=SECONDARY, marker="o", markersize=3, linewidth=1.0)
    ax2.set_xticks(xs)
    ax2.set_xticklabels([b["bucket"] for b in buckets])
    ax2.set_xlabel("Số lần đã mua trong prior")
    ax2.set_ylabel("Mua lại ở đơn kế tiếp (%)")
    ax2.set_ylim(0, rates.max() * 1.18)
    for xi, v in zip(xs, rates):
        ax2.text(xi, v + rates.max() * 0.025, f"{v:.1f}", ha="center", fontsize=5.5)
    _panel(ax2, "B")

    _save(fig, "fig_purchase_frequency_repurchase")


def fig_recency(stats: dict) -> None:
    """Phân phối recency và xác suất mua lại theo recency."""
    hist = stats["recency"]["histogram"]
    x = np.arange(len(hist))
    shares = np.array([row["share_pct"] for row in hist])
    cross = stats["recency"]["by_frequency_group"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.1), constrained_layout=True)

    ax1.bar(x, shares, color=PRIMARY, width=0.72)
    ax1.set_xticks(x)
    ax1.set_xticklabels([row["orders_since_last"] for row in hist])
    ax1.set_xlabel("Số đơn kể từ lần mua cuối")
    ax1.set_ylabel("Tỉ lệ cặp khách–sản phẩm (%)")
    ax1.set_ylim(0, shares.max() * 1.22)
    for xi, v in zip(x, shares):
        ax1.text(xi, v + shares.max() * 0.02, f"{v:.1f}", ha="center", fontsize=5.5)
    _panel(ax1, "A")

    styles = [
        ("1", PRIMARY, "o"),
        ("2–4", SECONDARY, "s"),
        ("5+", TERTIARY, "^"),
    ]
    for name, color, marker in styles:
        rows = next(g for g in cross if g["prior_purchases"] == name)["by_recency"]
        rates = np.array([r["rate_pct"] for r in rows])
        xs = np.arange(len(rows))
        ax2.plot(xs, rates, color=color, marker=marker, markersize=2.7, linewidth=1.0,
                 label=f"đã mua {name} lần")
    ax2.set_xticks(np.arange(len(REC_LABELS)))
    ax2.set_xticklabels(REC_LABELS)
    ax2.set_xlabel("Số đơn kể từ lần mua cuối")
    ax2.set_ylabel("Mua lại ở đơn kế tiếp (%)")
    top_rate = max(
        r["rate_pct"] for group in cross for r in group["by_recency"] if r["rate_pct"]
    )
    ax2.set_ylim(0, top_rate * 1.22)
    ax2.legend(frameon=False, loc="upper right")
    _panel(ax2, "B")

    _save(fig, "fig_recency_repurchase")


def main() -> None:
    print("Loading orders ...")
    prior, _, user_of_order, onum_of_order, is_train_user, target_onum, _ = load_orders()
    products = pd.read_csv(
        DATA / "products.csv",
        usecols=["product_id", "product_name", "aisle_id", "department_id"],
    )
    max_product = int(products["product_id"].max())

    print("Scanning prior pairs for train users ...")
    pairs = scan_pairs(user_of_order, onum_of_order, is_train_user)
    print(f"  {pairs['keys'].size:,} cặp khách–sản phẩm")

    print("Loading train target items ...")
    target_keys, n_train_items = load_target_keys(user_of_order)
    labels = mark_target(pairs["keys"], target_keys)
    print(f"  {labels.sum():,} cặp mua lại trong đơn train")

    stats, _ = compute_stats(
        pairs, labels, target_onum, max_product, products, n_train_items
    )
    stats["source"] = {
        "orders_prior": "data/orders_prior.csv",
        "orders_train": "data/orders_train.csv",
        "items_prior": "data/order_products__prior.csv",
        "items_train": "data/order_products__train.csv",
        "products": "data/products.csv",
    }
    (DOCS / "repeat_summary.json").write_text(
        json.dumps(stats, indent=2, ensure_ascii=False)
    )
    print("  -> docs/repeat_summary.json")

    print("Rendering figures ...")
    fig_frequency(stats)
    fig_recency(stats)
    print(json.dumps(stats["sample"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

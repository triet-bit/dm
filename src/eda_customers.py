"""EDA khách hàng: giỏ hàng theo thời điểm, hồ sơ khách, nhóm hành vi và tỉ lệ mua lại.

Đầu ra:
  1. Kích thước giỏ theo ngày trong tuần và giờ đặt hàng (Task 10).
  2. Số đơn, độ đa dạng, giỏ trung bình và tỉ lệ mua lại theo khách (Task 18–20).
  3. Nhóm hành vi theo phân vị tần suất + PCA 2D (Task 22).
  4. Tỉ lệ mua lại theo order_number và days_since_prior_order (Task 23, 26).

Nguồn: data/orders_prior.csv, data/order_products__prior.csv. Số liệu ghi vào
docs/customer_summary.json; figure xuất PDF + PNG 300 dpi vào docs/figures/.

Chạy: .venv/bin/python src/eda_customers.py
"""

from __future__ import annotations

import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LogNorm

from eda_products import (
    ACCENT,
    CHUNK,
    DATA,
    DOCS,
    NEUTRAL,
    PRIMARY,
    PRODUCT_BASE,
    SECONDARY,
    SEED,
    TERTIARY,
    _panel,
    _save,
)

MM = 1 / 25.4
DOW_LABELS = ["0", "1", "2", "3", "4", "5", "6"]
FEATURES = ["n_orders", "distinct_products", "mean_basket", "reorder_rate", "mean_gap"]
PCA_FEATURES = ["mean_gap", "mean_basket", "distinct_products", "reorder_rate"]
LOG_FEATURES = ["mean_gap", "mean_basket", "distinct_products"]
GROUP_LABELS = ["Khoảng cách ngắn", "Khoảng cách vừa", "Khoảng cách dài"]
SCATTER_N = 6_000


def load_orders() -> pd.DataFrame:
    """Đọc orders prior với kiểu dữ liệu gọn."""
    return pd.read_csv(
        DATA / "orders_prior.csv",
        usecols=["order_id", "user_id", "order_number", "order_dow", "order_hour_of_day",
                 "days_since_prior_order"],
        dtype={"order_id": "int32", "user_id": "int32", "order_number": "int16",
               "order_dow": "int8", "order_hour_of_day": "int8",
               "days_since_prior_order": "float32"},
    )


def scan_order_products(
    orders: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Trả về (số item theo đơn, số item mua lại theo đơn, khoá khách–sản phẩm duy nhất)."""
    max_order = int(orders["order_id"].max())
    user_of_order = np.zeros(max_order + 1, dtype=np.int32)
    user_of_order[orders["order_id"].to_numpy()] = orders["user_id"].to_numpy()
    size = np.zeros(max_order + 1, dtype=np.int64)
    reord = np.zeros(max_order + 1, dtype=np.int64)
    keys: list[np.ndarray] = []
    for chunk in pd.read_csv(
        DATA / "order_products__prior.csv",
        usecols=["order_id", "product_id", "reordered"],
        dtype={"order_id": "int32", "product_id": "int32", "reordered": "int8"},
        chunksize=CHUNK,
    ):
        oid = chunk["order_id"].to_numpy()
        size += np.bincount(oid, minlength=max_order + 1)
        reord += np.bincount(oid, weights=chunk["reordered"].to_numpy(),
                             minlength=max_order + 1).astype(np.int64)
        k = user_of_order[oid].astype(np.int64) * PRODUCT_BASE + chunk["product_id"].to_numpy()
        keys.append(np.unique(k))
    return size, reord, np.unique(np.concatenate(keys))


def customer_table(orders: pd.DataFrame, keys: np.ndarray) -> pd.DataFrame:
    """Tổng hợp 5 chỉ số hành vi cho mỗi khách (orders đã gắn cột size/reord)."""
    eligible = orders["order_number"] > 1
    g = orders.groupby("user_id")
    table = pd.DataFrame(
        {
            "n_orders": g.size(),
            "items": g["size"].sum(),
            "mean_gap": g["days_since_prior_order"].mean(),
        }
    )
    elig = orders[eligible].groupby("user_id")
    table["elig_items"] = elig["size"].sum()
    table["elig_reord"] = elig["reord"].sum()
    table["distinct_products"] = pd.Series(keys // PRODUCT_BASE).value_counts().sort_index()
    table["mean_basket"] = table["items"] / table["n_orders"]
    table["reorder_rate"] = table["elig_reord"] / table["elig_items"]
    return table[FEATURES]


def group_stats(orders: pd.DataFrame, column: str, n_groups: int) -> pd.DataFrame:
    """Median/IQR của kích thước giỏ theo một cột thời gian."""
    g = orders.groupby(column)["size"]
    return pd.DataFrame(
        {
            "orders": g.size(),
            "mean": g.mean(),
            "q25": g.quantile(0.25),
            "median": g.median(),
            "q75": g.quantile(0.75),
        }
    ).reindex(range(n_groups))


def reorder_by(orders: pd.DataFrame, column: str) -> pd.DataFrame:
    """Tỉ lệ mua lại gộp theo dòng và IQR của tỉ lệ từng đơn, theo một cột."""
    frame = orders.assign(rate=orders["reord"] / orders["size"])
    g = frame.groupby(column)
    return pd.DataFrame(
        {
            "orders": g.size(),
            "lines": g["size"].sum(),
            "pooled_rate": g["reord"].sum() / g["size"].sum(),
            "q25": g["rate"].quantile(0.25),
            "median": g["rate"].median(),
            "q75": g["rate"].quantile(0.75),
        }
    )


def standardize(table: pd.DataFrame) -> pd.DataFrame:
    """log1p cho ba đặc trưng đuôi phải rồi z-score cả bốn đặc trưng PCA."""
    z = table[PCA_FEATURES].copy()
    for col in LOG_FEATURES:
        z[col] = np.log1p(z[col])
    return (z - z.mean()) / z.std(ddof=0)


def pca(z: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """PCA bằng SVD: trả về điểm số, tải trọng (đặc trưng × 2) và tỉ lệ phương sai."""
    x = z.to_numpy()
    _, s, vt = np.linalg.svd(x, full_matrices=False)
    var = s**2 / (x.shape[0])
    scores = x @ vt[:2].T
    return scores, vt[:2].T, var / var.sum()


def frequency_groups(table: pd.DataFrame) -> pd.Series:
    """Chia khách thành 3 nhóm theo phân vị của số ngày trung bình giữa hai đơn."""
    return pd.qcut(table["mean_gap"], 3, labels=GROUP_LABELS)


def fig_basket_time(dow: pd.DataFrame, hour: pd.DataFrame) -> None:
    """Median và IQR kích thước giỏ theo ngày trong tuần và giờ đặt hàng."""
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(183 * MM, 65 * MM), gridspec_kw={"width_ratios": [1, 2]},
        constrained_layout=True, sharey=True,
    )
    for ax, data, letter in ((ax1, dow, "A"), (ax2, hour, "B")):
        x = data.index.to_numpy()
        ax.vlines(x, data["q25"], data["q75"], color=PRIMARY, lw=1.4)
        ax.plot(x, data["median"], "o", color=PRIMARY, ms=3, label="Median")
        ax.plot(x, data["mean"], "D", color=SECONDARY, ms=2.5, label="Mean")
        ax.set_ylim(0, None)
        _panel(ax, letter)
    ax1.set_xticks(range(7), DOW_LABELS)
    ax1.set_xlabel("Ngày trong tuần (mã 0–6)")
    ax1.set_ylabel("Số item trong một đơn")
    ax2.set_xticks(range(0, 24, 2))
    ax2.set_xlabel("Giờ trong ngày (0–23)")
    ax2.legend(frameon=False, loc="upper left", bbox_to_anchor=(1.0, 1.0))
    _save(fig, "fig_basket_by_time")


def fig_customer_profile(table: pd.DataFrame, stats: dict) -> None:
    """Số đơn–đa dạng, giỏ trung bình và tỉ lệ mua lại theo khách."""
    fig, axes = plt.subplots(1, 3, figsize=(183 * MM, 62 * MM), constrained_layout=True)
    ax1, ax2, ax3 = axes

    hb = ax1.hexbin(table["n_orders"], table["distinct_products"], gridsize=40,
                    xscale="linear", yscale="log", mincnt=1, cmap="Blues", linewidths=0,
                    norm=LogNorm())
    med = stats["diversity_by_orders"]
    ax1.plot([m["orders_mid"] for m in med], [m["median"] for m in med], color=SECONDARY,
             lw=1.2)
    ax1.set_xlabel("Số đơn prior của một khách")
    ax1.set_ylabel("Số sản phẩm khác nhau (thang log)")
    cb = fig.colorbar(hb, ax=ax1, location="bottom", pad=0.02, fraction=0.06)
    cb.set_label("Số khách (thang log)", fontsize=6)
    cb.ax.tick_params(labelsize=5.5)
    _panel(ax1, "A")

    for ax, col, color, xlabel, letter, upper in (
        (ax2, "mean_basket", PRIMARY, "Số item trung bình mỗi đơn", "B", 40),
        (ax3, "reorder_rate", TERTIARY, "Tỉ lệ mua lại của khách (%)", "C", 100),
    ):
        v = table[col].to_numpy() * (100 if col == "reorder_rate" else 1)
        ax.hist(np.clip(v, 0, upper), bins=np.linspace(0, upper, 51), color=color,
                weights=np.full(v.size, 100 / v.size))
        med_v = float(np.median(v))
        ax.axvline(med_v, color=NEUTRAL, ls="--", lw=0.8)
        ax.set_xlabel(xlabel)
        ax.set_ylabel("Tỉ lệ khách hàng (%)")
        _panel(ax, letter)
    _save(fig, "fig_customer_profile")


def fig_customer_segments(table: pd.DataFrame, z: pd.DataFrame, scores: np.ndarray,
                          loadings: np.ndarray, evr: np.ndarray, groups: pd.Series,
                          corr: pd.DataFrame, group_z: pd.DataFrame) -> None:
    """PCA 2D theo nhóm tần suất, ma trận Spearman và median z-score theo nhóm."""
    colors = [PRIMARY, TERTIARY, SECONDARY]
    names = {"mean_gap": "Ngày giữa hai đơn", "mean_basket": "Giỏ trung bình",
             "distinct_products": "Số sản phẩm khác nhau", "reorder_rate": "Tỉ lệ mua lại"}
    short = {"mean_gap": "Ngày giữa đơn", "mean_basket": "Giỏ", "distinct_products": "Đa dạng",
             "reorder_rate": "Mua lại"}
    fig = plt.figure(figsize=(183 * MM, 70 * MM), constrained_layout=True)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.25, 1, 1])
    ax1, ax2, ax3 = (fig.add_subplot(gs[0, i]) for i in range(3))

    rng = np.random.default_rng(SEED)
    idx = rng.choice(len(table), size=SCATTER_N, replace=False)
    grp = groups.to_numpy()
    for label, color in zip(GROUP_LABELS, colors):
        sel = idx[grp[idx] == label]
        ax1.scatter(scores[sel, 0], scores[sel, 1], s=1.5, color=color, alpha=0.4,
                    linewidths=0, label=label)
    scale = 2.6
    for k, feat in enumerate(PCA_FEATURES):
        ax1.annotate("", xy=(loadings[k, 0] * scale, loadings[k, 1] * scale), xytext=(0, 0),
                     arrowprops={"arrowstyle": "->", "lw": 0.8, "color": "black"})
        ax1.text(loadings[k, 0] * scale * 1.12, loadings[k, 1] * scale * 1.12, short[feat],
                 fontsize=5.5, ha="left" if loadings[k, 0] > 0 else "right", va="center",
                 bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.5, "alpha": 0.8})
    ax1.set_xlabel(f"PC1 ({evr[0] * 100:.1f}% phương sai)")
    ax1.set_ylabel(f"PC2 ({evr[1] * 100:.1f}% phương sai)")
    leg = ax1.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=1,
                     markerscale=4)
    for handle in leg.legend_handles:
        handle.set_alpha(1)
    _panel(ax1, "A")

    cols = PCA_FEATURES
    m = corr.loc[cols, cols].to_numpy()
    im = ax2.imshow(m, cmap="RdBu_r", vmin=-1, vmax=1)
    ax2.set_xticks(range(4), [names[c] for c in cols], rotation=45, ha="right")
    ax2.set_yticks(range(4), [names[c] for c in cols])
    for i in range(4):
        for j in range(4):
            ax2.text(j, i, f"{m[i, j]:.2f}", ha="center", va="center", fontsize=6,
                     color="white" if abs(m[i, j]) > 0.6 else "black")
    for sp in ax2.spines.values():
        sp.set_visible(False)
    fig.colorbar(im, ax=ax2, location="bottom", pad=0.02, fraction=0.05).set_label(
        "Spearman ρ", fontsize=6)
    _panel(ax2, "B")

    for gi, (label, color) in enumerate(zip(GROUP_LABELS, colors)):
        for k, feat in enumerate(cols):
            lo, med, hi = group_z.loc[label, feat]
            y = k + (gi - 1) * 0.22
            ax3.plot([lo, hi], [y, y], color=color, lw=1.2, solid_capstyle="butt")
            ax3.plot(med, y, "o", color=color, ms=2.6)
    ax3.axvline(0, color=NEUTRAL, lw=0.6)
    ax3.set_yticks(range(4), [names[c] for c in cols])
    ax3.invert_yaxis()
    ax3.set_xlabel("z-score (median, IQR)")
    _panel(ax3, "C")
    _save(fig, "fig_customer_segments")


def fig_reorder_rate(by_number: pd.DataFrame, by_gap: pd.DataFrame) -> None:
    """Tỉ lệ mua lại theo order_number và theo số ngày kể từ đơn trước."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(183 * MM, 65 * MM), constrained_layout=True,
                                   sharey=True)
    for ax, data, xlabel, letter in (
        (ax1, by_number, "Thứ tự đơn (order_number)", "A"),
        (ax2, by_gap, "Số ngày kể từ đơn trước", "B"),
    ):
        x = data.index.to_numpy()
        ax.fill_between(x, data["q25"] * 100, data["q75"] * 100, color=PRIMARY, alpha=0.2,
                        linewidth=0)
        ax.plot(x, data["pooled_rate"] * 100, color=PRIMARY, lw=1.2)
        ax.set_xlabel(xlabel)
        ax.set_ylim(0, 100)
        _panel(ax, letter)
    ax1.set_ylabel("Tỉ lệ dòng reordered = 1 (%)")
    ax2.axvline(30, color=ACCENT, lw=0.8, ls=":")
    _save(fig, "fig_reorder_rate")


def main() -> None:
    print("Loading orders ...")
    orders = load_orders()
    print("Scanning order_products__prior ...")
    size, reord, keys = scan_order_products(orders)
    orders["size"] = size[orders["order_id"].to_numpy()]
    orders["reord"] = reord[orders["order_id"].to_numpy()]
    n_no_items = int((orders["size"] == 0).sum())
    orders = orders[orders["size"] > 0].copy()

    dow = group_stats(orders, "order_dow", 7)
    hour = group_stats(orders, "order_hour_of_day", 24)
    table = customer_table(orders, keys)
    cust_na = int(table.isna().sum().sum())
    table = table.dropna()

    # Task 18: trung vị đa dạng theo nhóm số đơn
    bins = [3, 5, 8, 12, 20, 35, 60, 100]
    cut = pd.cut(table["n_orders"], bins)
    div = table.groupby(cut, observed=True)["distinct_products"].agg(
        ["size", "median", "mean"])
    div_rows = [
        {"orders_range": f"{iv.left + 1}-{iv.right}", "orders_mid": (iv.left + 1 + iv.right) / 2,
         "customers": int(r["size"]), "median": float(r["median"]), "mean": round(r["mean"], 4)}
        for iv, r in div.iterrows()
    ]
    rho_orders_div = float(table["n_orders"].corr(table["distinct_products"], method="spearman"))

    by_number = reorder_by(orders[orders["order_number"] > 1], "order_number")
    by_gap = reorder_by(
        orders[(orders["order_number"] > 1) & orders["days_since_prior_order"].notna()]
        .assign(gap=lambda d: d["days_since_prior_order"].astype(int)),
        "gap",
    )
    all_lines = int(orders["size"].sum())
    all_reord = int(orders["reord"].sum())
    elig = orders[orders["order_number"] > 1]

    z = standardize(table)
    scores, loadings, evr = pca(z)
    groups = frequency_groups(table)
    corr = table[PCA_FEATURES].corr(method="spearman")
    group_z = {}
    for label in GROUP_LABELS:
        sub = z[groups.to_numpy() == label]
        group_z[label] = {
            c: tuple(np.percentile(sub[c], [25, 50, 75])) for c in PCA_FEATURES
        }
    group_z_df = pd.DataFrame(group_z).T
    group_rows = []
    for label in GROUP_LABELS:
        sub = table[groups.to_numpy() == label]
        group_rows.append(
            {"group": label, "customers": int(len(sub)),
             "mean_gap_range": [round(float(sub["mean_gap"].min()), 4),
                                round(float(sub["mean_gap"].max()), 4)],
             **{f"median_{c}": round(float(sub[c].median()), 4) for c in FEATURES}}
        )

    def q(s: pd.Series) -> dict:
        return {"median": round(float(s.median()), 4), "q25": round(float(s.quantile(0.25)), 4),
                "q75": round(float(s.quantile(0.75)), 4), "mean": round(float(s.mean()), 4),
                "min": round(float(s.min()), 4), "max": round(float(s.max()), 4)}

    stats = {
        "source": ["data/orders_prior.csv", "data/order_products__prior.csv"],
        "seed": SEED,
        "orders": int(len(orders)),
        "orders_without_items": n_no_items,
        "users": int(len(table)),
        "users_with_nan_feature": cust_na,
        "basket_by_dow": dow.round(4).reset_index().to_dict(orient="records"),
        "basket_by_hour": hour.round(4).reset_index().to_dict(orient="records"),
        "customer": {c: q(table[c]) for c in FEATURES},
        "spearman_orders_vs_diversity": round(rho_orders_div, 4),
        "diversity_by_orders": div_rows,
        "reorder": {
            "all_lines": all_lines,
            "all_reordered": all_reord,
            "all_rate_pct": round(all_reord / all_lines * 100, 4),
            "eligible_lines": int(elig["size"].sum()),
            "eligible_reordered": int(elig["reord"].sum()),
            "eligible_rate_pct": round(elig["reord"].sum() / elig["size"].sum() * 100, 4),
            "by_order_number": by_number.round(4).reset_index().to_dict(orient="records"),
            "by_days_since_prior": by_gap.round(4).reset_index().to_dict(orient="records"),
        },
        "segments": {
            "features": PCA_FEATURES,
            "transform": "log1p cho " + ", ".join(LOG_FEATURES) + "; z-score cả bốn đặc trưng",
            "grouping": "tertile của mean_gap (số ngày trung bình giữa hai đơn prior)",
            "pca_explained_variance_pct": [round(float(v) * 100, 4) for v in evr],
            "loadings_pc1_pc2": {f: [round(float(v), 4) for v in loadings[i]]
                                 for i, f in enumerate(PCA_FEATURES)},
            "spearman": corr.loc[PCA_FEATURES, PCA_FEATURES].round(4).to_dict(),
            "scatter_sample": SCATTER_N,
            "groups": group_rows,
        },
    }
    (DOCS / "customer_summary.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False))
    print("  -> docs/customer_summary.json")

    print("Rendering figures ...")
    fig_basket_time(dow, hour)
    fig_customer_profile(table, stats)
    fig_customer_segments(table, z, scores, loadings, evr, groups, corr, group_z_df)
    fig_reorder_rate(by_number, by_gap)
    print(json.dumps(stats["reorder"]["all_rate_pct"]), json.dumps(stats["segments"]["groups"]))


if __name__ == "__main__":
    main()

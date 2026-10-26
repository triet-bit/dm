"""EDA danh mục: quy mô bảng, số thực thể, độ phổ biến theo department, sản phẩm vào giỏ đầu.

Bốn đầu ra:
  1. Số dòng của từng bảng CSV trong data/ (Task 1).
  2. Số sản phẩm, aisle, department và số sản phẩm mỗi department (Task 4).
  3. Phân phối độ phổ biến sản phẩm theo department (Task 15).
  4. Sản phẩm được thêm vào giỏ đầu tiên (Task 16).

Nguồn: data/*.csv. Số liệu ghi vào docs/catalog_summary.json; figure xuất PDF + PNG
300 dpi vào docs/figures/.

Chạy: .venv/bin/python src/eda_catalog.py
"""

from __future__ import annotations

import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from eda_products import (
    CHUNK,
    DATA,
    DOCS,
    NEUTRAL,
    PRIMARY,
    SECONDARY,
    SEED,
    TERTIARY,
    _panel,
    _save,
    _short,
)

TABLES = [
    "orders.csv",
    "order_products__prior.csv",
    "order_products__train.csv",
    "products.csv",
    "aisles.csv",
    "departments.csv",
]
MIN_LINES_FIRST = 5_000  # ngưỡng số dòng tối thiểu cho tỉ lệ vào giỏ đầu (như top reorder)
STRIP_PER_DEPT = 250  # số điểm thô vẽ cho mỗi department
MM = 1 / 25.4


def count_records(path_name: str) -> int:
    """Đếm số dòng dữ liệu (không tính header) của một CSV bằng cách đếm ký tự xuống dòng."""
    newlines = 0
    last = b"\n"
    with open(DATA / path_name, "rb") as handle:
        while block := handle.read(1 << 24):
            newlines += block.count(b"\n")
            last = block[-1:]
    return newlines - 1 + (0 if last == b"\n" else 1)


def scan_lines(n_products: int) -> tuple[np.ndarray, np.ndarray]:
    """Đếm số dòng của từng sản phẩm và số lần sản phẩm ở vị trí giỏ đầu tiên."""
    lines = np.zeros(n_products + 1, dtype=np.int64)
    first = np.zeros(n_products + 1, dtype=np.int64)
    for chunk in pd.read_csv(
        DATA / "order_products__prior.csv",
        usecols=["product_id", "add_to_cart_order"],
        dtype={"product_id": "int32", "add_to_cart_order": "int16"},
        chunksize=CHUNK,
    ):
        pid = chunk["product_id"].to_numpy()
        lines += np.bincount(pid, minlength=n_products + 1)
        is_first = chunk["add_to_cart_order"].to_numpy() == 1
        first += np.bincount(pid[is_first], minlength=n_products + 1)
    return lines, first


def top_share(values: np.ndarray, fraction: float = 0.1) -> float:
    """Tỉ lệ tổng giá trị thuộc `fraction` phần tử lớn nhất (ít nhất một phần tử)."""
    ordered = np.sort(values)[::-1]
    k = max(1, int(np.ceil(ordered.size * fraction)))
    return float(ordered[:k].sum() / ordered.sum())


def department_popularity(products: pd.DataFrame, lines: np.ndarray) -> pd.DataFrame:
    """Tổng hợp phân phối số dòng theo sản phẩm trong từng department."""
    frame = products[["product_id", "department"]].assign(
        lines=lines[products["product_id"].to_numpy()]
    )
    frame = frame[frame["lines"] > 0]
    rows = []
    for dept, group in frame.groupby("department"):
        v = group["lines"].to_numpy()
        rows.append(
            {
                "department": dept,
                "products": int(v.size),
                "lines": int(v.sum()),
                "median": float(np.median(v)),
                "q25": float(np.percentile(v, 25)),
                "q75": float(np.percentile(v, 75)),
                "max": int(v.max()),
                "top10pct_share": top_share(v),
            }
        )
    return pd.DataFrame(rows).sort_values("median", ascending=False).reset_index(drop=True)


def fig_overview(records: dict[str, int], entities: dict[str, int], per_dept: pd.Series) -> None:
    """Số dòng từng bảng, số thực thể, số sản phẩm mỗi department."""
    fig = plt.figure(figsize=(183 * MM, 105 * MM), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, width_ratios=[1, 1])
    ax1, ax2, ax3 = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[:, 1])

    names = list(records)[::-1]
    vals = [records[n] for n in names]
    ax1.barh(names, vals, color=PRIMARY, height=0.6)
    ax1.set_xscale("log")
    ax1.set_xlim(left=5)
    for i, v in enumerate(vals):
        ax1.text(v * 1.15, i, f"{v:,}".replace(",", "."), va="center", fontsize=6)
    ax1.set_xlim(5, max(vals) * 12)
    ax1.set_xlabel("Số dòng (thang log)")
    _panel(ax1, "A")

    ent = list(entities)[::-1]
    ev = [entities[e] for e in ent]
    ax2.barh(ent, ev, color=TERTIARY, height=0.5)
    ax2.set_xscale("log")
    for i, v in enumerate(ev):
        ax2.text(v * 1.15, i, f"{v:,}".replace(",", "."), va="center", fontsize=6)
    ax2.set_xlim(5, max(ev) * 8)
    ax2.set_xlabel("Số thực thể (thang log)")
    _panel(ax2, "B")

    data = per_dept.sort_values()
    ax3.barh(data.index, data.to_numpy(), color=PRIMARY, height=0.65)
    for i, v in enumerate(data.to_numpy()):
        ax3.text(v + 30, i, f"{v:,}".replace(",", "."), va="center", fontsize=5.5)
    ax3.set_xlim(0, data.max() * 1.15)
    ax3.set_xlabel("Số sản phẩm trong catalog")
    _panel(ax3, "C")
    _save(fig, "fig_dataset_overview")


def fig_department_popularity(
    products: pd.DataFrame, lines: np.ndarray, stats: pd.DataFrame
) -> None:
    """Phân phối số dòng theo sản phẩm trong từng department và độ tập trung top 10%."""
    rng = np.random.default_rng(SEED)
    order = stats["department"].tolist()[::-1]
    frame = products[["product_id", "department"]].assign(
        lines=lines[products["product_id"].to_numpy()]
    )
    frame = frame[frame["lines"] > 0]

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(183 * MM, 100 * MM), gridspec_kw={"width_ratios": [1.7, 1]},
        constrained_layout=True,
    )
    for i, dept in enumerate(order):
        v = frame.loc[frame["department"] == dept, "lines"].to_numpy()
        pts = rng.choice(v, size=min(STRIP_PER_DEPT, v.size), replace=False)
        ax1.scatter(pts, i + rng.uniform(-0.28, 0.28, pts.size), s=1.2, color=NEUTRAL,
                    alpha=0.35, linewidths=0)
        q25, med, q75 = np.percentile(v, [25, 50, 75])
        ax1.plot([q25, q75], [i, i], color=PRIMARY, lw=1.6, solid_capstyle="butt")
        ax1.plot(med, i, "o", color=SECONDARY, ms=3, zorder=3)
    ax1.set_xscale("log")
    ax1.set_yticks(range(len(order)), order)
    ax1.set_xlabel("Số dòng order-product của một sản phẩm (thang log)")
    _panel(ax1, "A")

    share = stats.set_index("department").loc[order, "top10pct_share"] * 100
    ax2.barh(range(len(order)), share.to_numpy(), color=TERTIARY, height=0.65)
    ax2.set_yticks(range(len(order)), [""] * len(order))
    ax2.set_xlim(0, 100)
    ax2.set_xlabel("Tỉ lệ dòng của 10% sản phẩm đứng đầu (%)")
    _panel(ax2, "B")
    _save(fig, "fig_department_popularity")


def fig_first_in_cart(top_count: pd.DataFrame, top_rate: pd.DataFrame) -> None:
    """Sản phẩm ở vị trí giỏ đầu tiên theo số lần và theo tỉ lệ."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(183 * MM, 80 * MM), constrained_layout=True)
    d1 = top_count.sort_values("first")
    ax1.barh([_short(n, 30) for n in d1["product_name"]], d1["first"] / 1e3,
             color=PRIMARY, height=0.65)
    ax1.set_xlabel("Số lần ở vị trí giỏ đầu tiên (nghìn)")
    _panel(ax1, "A")
    d2 = top_rate.sort_values("first_rate")
    ax2.barh([_short(n, 30) for n in d2["product_name"]], d2["first_rate"] * 100,
             color=SECONDARY, height=0.65)
    ax2.set_xlabel("Tỉ lệ dòng ở vị trí giỏ đầu tiên (%)")
    _panel(ax2, "B")
    _save(fig, "fig_first_in_cart")


def main() -> None:
    print("Counting records ...")
    records = {name: count_records(name) for name in TABLES}

    products = pd.read_csv(DATA / "products.csv")
    aisles = pd.read_csv(DATA / "aisles.csv")
    depts = pd.read_csv(DATA / "departments.csv")
    products = products.merge(depts, on="department_id")
    n_products = int(products["product_id"].max())

    print("Scanning order_products__prior ...")
    lines, first = scan_lines(n_products)
    total_lines = int(lines.sum())
    active = products[lines[products["product_id"].to_numpy()] > 0]

    entities = {
        "Products": int(products.shape[0]),
        "Aisles": int(aisles.shape[0]),
        "Departments": int(depts.shape[0]),
    }
    per_dept = products.groupby("department").size().sort_values()
    pop = department_popularity(products, lines)

    first_tbl = products.assign(
        first=first[products["product_id"].to_numpy()],
        lines=lines[products["product_id"].to_numpy()],
    )
    first_tbl["first_rate"] = first_tbl["first"] / first_tbl["lines"].where(first_tbl["lines"] > 0)
    top_count = first_tbl.nlargest(15, "first")
    top_rate = first_tbl[first_tbl["lines"] >= MIN_LINES_FIRST].nlargest(15, "first_rate")
    n_first = int(first.sum())

    stats = {
        "source": "data/*.csv; order_products__prior.csv cho Task 15–16",
        "records": records,
        "entities": entities,
        "products_with_prior_lines": int(active.shape[0]),
        "products_per_department": {k: int(v) for k, v in per_dept.items()},
        "department_popularity": pop.round(4).to_dict(orient="records"),
        "first_in_cart": {
            "lines": total_lines,
            "first_position_lines": n_first,
            "min_lines_for_rate": MIN_LINES_FIRST,
            "top_by_count": [
                {"product": r.product_name, "first": int(r.first), "lines": int(r.lines),
                 "first_rate_pct": round(float(r.first_rate * 100), 4)}
                for r in top_count.itertuples()
            ],
            "top_by_rate": [
                {"product": r.product_name, "first": int(r.first), "lines": int(r.lines),
                 "first_rate_pct": round(float(r.first_rate * 100), 4)}
                for r in top_rate.itertuples()
            ],
        },
    }
    (DOCS / "catalog_summary.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False))
    print("  -> docs/catalog_summary.json")

    print("Rendering figures ...")
    fig_overview(records, entities, per_dept)
    fig_department_popularity(products, lines, pop)
    fig_first_in_cart(top_count, top_rate)
    print(json.dumps(stats["records"], indent=2), entities)


if __name__ == "__main__":
    main()

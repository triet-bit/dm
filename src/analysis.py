"""EDA cho Instacart Market Basket Analysis.

Việc làm:
  1. Tách orders.csv thành 3 file theo eval_set (prior / train / test) và đếm số lượng.
  2. Kiểm tra tỉ lệ missing values trên từng cột của mọi file.
  3. Phân phối số đơn hàng trên mỗi khách hàng.

Việc vẽ figure nằm ở src/figures_paper.py và src/eda_behavior.py.

Chạy:  .venv/bin/python src/analysis.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
DOCS = Path(__file__).resolve().parent.parent / "docs"

CHUNK = 2_000_000  # cho các file lớn


# ---------------------------------------------------------------------------
# 1. Tách orders.csv theo eval_set
# ---------------------------------------------------------------------------
def split_orders() -> pd.DataFrame:
    orders = pd.read_csv(DATA / "orders.csv")
    print("== orders.csv dtypes ==")
    print(orders.dtypes)

    counts = orders["eval_set"].value_counts().reindex(["prior", "train", "test"])
    print("\n== Số lượng theo eval_set ==")
    print(counts)

    for name in ["prior", "train", "test"]:
        sub = orders[orders["eval_set"] == name]
        out = DATA / f"orders_{name}.csv"
        sub.to_csv(out, index=False)
        print(f"  -> ghi {out.name}: {len(sub):,} dòng")

    return orders


# ---------------------------------------------------------------------------
# 2. Missing values (đọc theo chunk để tiết kiệm RAM)
# ---------------------------------------------------------------------------
def missing_stats(path: Path) -> dict[str, float]:
    total = 0
    nulls: dict[str, int] = {}
    for chunk in pd.read_csv(path, chunksize=CHUNK):
        total += len(chunk)
        n = chunk.isna().sum()
        for col, v in n.items():
            nulls[col] = nulls.get(col, 0) + int(v)
    return {col: (v / total * 100 if total else 0.0) for col, v in nulls.items()}, total


def build_missing_table() -> pd.DataFrame:
    files = [
        "orders.csv",
        "order_products__prior.csv",
        "order_products__train.csv",
        "products.csv",
        "aisles.csv",
        "departments.csv",
    ]
    rows = []
    for f in files:
        pct, total = missing_stats(DATA / f)
        for col, p in pct.items():
            rows.append({"file": f, "column": col, "missing_pct": p, "rows": total})
    df = pd.DataFrame(rows)
    print("\n== Missing values (%) ==")
    print(df[df["missing_pct"] > 0].to_string(index=False))
    print("Tổng số cột có missing:", int((df["missing_pct"] > 0).sum()))
    return df


def orders_per_customer(orders: pd.DataFrame) -> pd.Series:
    opc = orders.groupby("user_id")["order_id"].count()
    print("\n== Số đơn / khách hàng ==")
    print(opc.describe())
    print("median:", opc.median(), "min:", opc.min(), "max:", opc.max())
    print("#users:", opc.shape[0])
    return opc


def main() -> None:
    orders = split_orders()
    counts = orders["eval_set"].value_counts().reindex(["prior", "train", "test"])

    miss = build_missing_table()
    opc = orders_per_customer(orders)

    summary = {
        "eval_set_counts": {k: int(v) for k, v in counts.items()},
        "missing_columns": miss[miss["missing_pct"] > 0].to_dict("records"),
        "orders_per_customer": {
            "users": int(opc.shape[0]),
            "min": int(opc.min()),
            "max": int(opc.max()),
            "mean": float(opc.mean()),
            "median": float(opc.median()),
            "q25": float(opc.quantile(0.25)),
            "q75": float(opc.quantile(0.75)),
        },
    }
    (DOCS / "summary.json").write_text(json.dumps(summary, indent=2))
    print("\n== summary.json ==")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

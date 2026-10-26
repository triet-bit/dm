"""Đối chiếu kết quả tự tính với số liệu tham chiếu trong docs/*.json.

Chạy: python learning/check.py <khoá> <giá trị> [--show]
Liệt kê khoá: python learning/check.py --list
Mặc định chỉ báo khớp/lệch; --show mới in giá trị tham chiếu.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"
REFS = {
    "t3_orders_per_customer_median": ("behavior_summary.json", "orders_per_customer.median"),
    "t5_peak_dow": ("behavior_summary.json", "order_timing.peak_dow"),
    "t6_peak_hour": ("behavior_summary.json", "order_timing.peak_hour"),
    "t8_gap_median": ("behavior_summary.json", "days_since_prior_order.median"),
    "t9_basket_median": ("behavior_summary.json", "basket_size.median"),
    "t9_basket_mean": ("behavior_summary.json", "basket_size.mean"),
    "t9_basket_share_le_5_pct": ("behavior_summary.json", "basket_size.share_le_5_pct"),
    "t17_diversity_median": ("customer_summary.json", "customer.distinct_products.median"),
    "t19_mean_basket_median": ("customer_summary.json", "customer.mean_basket.median"),
    "t20_reorder_rate_median": ("customer_summary.json", "customer.reorder_rate.median"),
    "t23_reorder_all_pct": ("customer_summary.json", "reorder.all_rate_pct"),
    "t23_reorder_eligible_pct": ("customer_summary.json", "reorder.eligible_rate_pct"),
}


def lookup(name: str) -> float:
    """Đọc giá trị tham chiếu theo đường dẫn chấm trong file JSON."""
    file, path = REFS[name]
    node = json.loads((DOCS / file).read_text())
    for part in path.split("."):
        node = node[part]
    return float(node)


def main(argv: list[str]) -> int:
    if argv[:1] == ["--list"]:
        print("\n".join(sorted(REFS)))
        return 0
    if len(argv) < 2 or argv[0] not in REFS:
        print(__doc__)
        return 2
    ref, mine = lookup(argv[0]), float(argv[1])
    ok = abs(ref - mine) <= max(1e-4, abs(ref) * 1e-3)
    print("khớp" if ok else "lệch")
    if "--show" in argv:
        print(f"tham chiếu = {ref}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""Tests cho các hàm tổng hợp trong src/eda_products.py."""

import numpy as np
import pandas as pd
import pytest

from eda_products import build_products, group_table, long_tail_stats


def test_long_tail_stats_known_counts() -> None:
    """Gini, tỉ lệ top và số sản phẩm cho 80% khớp ví dụ tính tay."""
    products = pd.DataFrame({"lines": [6, 1, 1, 1, 1]})

    stats, lorenz_x, lorenz_y = long_tail_stats(products)

    assert stats["products_with_purchases"] == 5
    assert stats["gini"] == pytest.approx(0.4)
    assert stats["top_1_pct_share_pct"] == pytest.approx(60.0)
    assert stats["top_20_pct_share_pct"] == pytest.approx(60.0)
    assert stats["products_for_80pct"] == 3
    assert lorenz_x[-1] == pytest.approx(100.0)
    assert lorenz_y[-1] == pytest.approx(100.0)


def test_group_table_line_weighted_rates() -> None:
    """Tỉ lệ theo nhóm là tổng reordered / tổng dòng hợp lệ."""
    products = pd.DataFrame(
        {
            "department_id": [1, 1, 2],
            "lines": [30, 10, 60],
            "eligible_lines": [20, 10, 50],
            "reordered": [10, 5, 25],
            "reordered_all": [12, 6, 30],
        }
    )
    names = pd.DataFrame({"department_id": [1, 2], "department": ["one", "two"]})

    agg = group_table(products, ["department_id"], names).set_index("department")

    assert agg.loc["one", "share_pct"] == pytest.approx(40.0)
    assert agg.loc["two", "share_pct"] == pytest.approx(60.0)
    assert agg.loc["one", "reorder_rate"] == pytest.approx(0.5)
    assert agg.loc["two", "reorder_rate"] == pytest.approx(0.5)
    assert agg.loc["one", "reorder_rate_all"] == pytest.approx(0.45)
    assert agg.loc["two", "reorder_rate_all"] == pytest.approx(0.5)


def test_build_products_drops_unpurchased_and_computes_rate() -> None:
    """Sản phẩm không có dòng bị loại; tỉ lệ dùng mẫu số eligible."""
    scan = {
        "lines": np.array([0, 10, 0, 5]),
        "eligible": np.array([0, 8, 0, 4]),
        "reordered": np.array([0, 4, 0, 3]),
        "reordered_all": np.array([0, 5, 0, 4]),
    }
    products = pd.DataFrame(
        {
            "product_id": [1, 2, 3],
            "product_name": ["a", "b", "c"],
            "aisle_id": [1, 1, 2],
            "department_id": [1, 1, 2],
        }
    )

    table = build_products(scan, products).set_index("product_id")

    assert table.index.tolist() == [1, 3]
    assert table.loc[1, "reorder_rate"] == pytest.approx(0.5)
    assert table.loc[3, "reorder_rate"] == pytest.approx(0.75)
    assert table.loc[1, "share_pct"] == pytest.approx(10 / 15 * 100)

"""Tests cho các hàm co-occurrence trong src/eda_cooccurrence.py."""

import numpy as np
import pandas as pd
import pytest

from eda_cooccurrence import pair_table, select_diverse


def test_pair_table_support_confidence_lift() -> None:
    """Support, confidence hai chiều và lift khớp ví dụ tính tay."""
    products = pd.DataFrame(
        {
            "product_id": [1, 2],
            "product_name": ["A", "B"],
            "aisle_id": [10, 20],
            "department_id": [1, 2],
        }
    )
    co = np.array([[10, 4], [4, 8]], dtype=np.int64)
    counts = np.array([10, 8], dtype=np.int64)

    table = pair_table(co, counts, np.array([1, 2], dtype=np.int32), products, 100)

    row = table.iloc[0]
    assert row["orders_both"] == 4
    assert row["support_pct"] == pytest.approx(4.0)
    assert row["confidence_a_to_b_pct"] == pytest.approx(40.0)
    assert row["confidence_b_to_a_pct"] == pytest.approx(50.0)
    assert row["lift"] == pytest.approx(5.0)


def test_select_diverse_limits_product_and_aisle_reuse() -> None:
    """Mỗi sản phẩm tối đa 1 cặp và mỗi aisle tối đa 1 cặp."""
    table = pd.DataFrame(
        {
            "product_a": ["A", "A", "C", "E", "G"],
            "product_b": ["B", "C", "D", "F", "H"],
            "aisle_a": [1, 1, 2, 1, 3],
            "aisle_b": [1, 2, 2, 3, 4],
            "lift": [10.0, 9.0, 8.0, 7.0, 6.0],
        }
    )

    selected = select_diverse(table, n=5, max_per_product=1, max_per_aisle=1)

    assert selected["product_a"].tolist() == ["A", "C", "G"]
    assert selected["product_b"].tolist() == ["B", "D", "H"]

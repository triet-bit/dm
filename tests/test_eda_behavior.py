"""Tests cho các hàm tính biến động giỏ trong src/eda_behavior.py."""

import numpy as np
import pandas as pd
import pytest

from eda_behavior import basket_pairs, lag1_correlation


def test_basket_pairs_keeps_consecutive_orders_and_skips_missing_items() -> None:
    """Chỉ tạo cặp cho đơn liên tiếp và bỏ đơn không có item."""
    orders = pd.DataFrame(
        {
            "order_id": [10, 11, 12, 20, 21, 30],
            "user_id": [1, 1, 1, 2, 2, 3],
            "order_number": [1, 2, 3, 1, 2, 1],
        }
    )
    basket = pd.Series(
        [3, 5, 4, 2, 2],
        index=pd.Index([10, 11, 12, 20, 21], name="order_id"),
    )

    pairs, missing = basket_pairs(orders, basket)

    assert missing == 1
    assert len(pairs) == 3
    assert pairs[pairs["user_id"] == 1]["change"].tolist() == [2, -1]
    assert pairs[pairs["user_id"] == 2]["change"].tolist() == [0]
    assert 30 not in pairs["order_id"].to_numpy()


def test_lag1_correlation_perfect_positive() -> None:
    """Chuỗi tăng đều có tương quan lag-1 bằng 1."""
    pairs = pd.DataFrame({"basket_size": [1, 2, 3, 4], "next_size": [2, 3, 4, 5]})
    assert lag1_correlation(pairs) == pytest.approx(1.0)


def test_lag1_correlation_is_symmetric_shift() -> None:
    """Tương quan không đổi khi đảo chiều hai chuỗi."""
    rng = np.random.default_rng(42)
    x = rng.integers(1, 20, size=1000)
    forward = lag1_correlation(pd.DataFrame({"basket_size": x[:-1], "next_size": x[1:]}))
    backward = lag1_correlation(pd.DataFrame({"basket_size": x[1:], "next_size": x[:-1]}))
    assert forward == pytest.approx(backward)

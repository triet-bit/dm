"""Tests cho các hàm tổng hợp tần suất/recency trong src/eda_repeat.py."""

import numpy as np
import pytest

from eda_repeat import FREQ_EDGES, FREQ_LABELS, _bucket_table, mark_target


def test_bucket_table_frequency_counts_and_rates() -> None:
    """Đếm đúng số cặp và tỉ lệ positive trong từng khoảng tần suất."""
    values = np.array([1, 1, 2, 2, 2, 5, 10, 20])
    labels = np.array([0, 1, 0, 1, 0, 1, 1, 0], dtype=bool)

    rows = _bucket_table(values, labels, FREQ_EDGES, FREQ_LABELS)

    assert [r["n"] for r in rows] == [2, 3, 0, 0, 1, 1, 1]
    assert rows[0]["rate_pct"] == pytest.approx(50.0)
    assert rows[1]["rate_pct"] == pytest.approx(33.3333, abs=1e-4)
    assert rows[4]["rate_pct"] == pytest.approx(100.0)
    assert rows[6]["rate_pct"] == pytest.approx(0.0)


def test_mark_target_marks_pairs_present_in_next_order() -> None:
    """Chỉ các khoá có trong tập target mới được đánh dấu."""
    keys = np.array([1, 2, 3, 4], dtype=np.int64)
    target = np.array([2, 4, 9], dtype=np.int64)

    labels = mark_target(keys, target)

    assert labels.tolist() == [False, True, False, True]

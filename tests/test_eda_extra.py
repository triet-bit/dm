"""Tests cho các hàm tổng hợp trong eda_catalog, eda_customers và eda_association."""

import numpy as np
import pandas as pd
import pytest

from eda_association import department_cooccurrence, support_lift
from eda_catalog import top_share
from eda_customers import frequency_groups, pca, reorder_by, standardize


def test_top_share_uses_at_least_one_item() -> None:
    """Top 10% của 4 phần tử là 1 phần tử lớn nhất."""
    assert top_share(np.array([6, 2, 1, 1])) == pytest.approx(0.6)


def test_department_cooccurrence_support_and_lift() -> None:
    """Support và lift khớp ví dụ 4 đơn tính tay."""
    present = np.array(
        [[False, True, True, True, False], [False, True, True, False, True]], dtype=bool
    )
    co = department_cooccurrence(present, np.array([1, 2, 3, 4]))
    assert co.tolist() == [[3, 2], [2, 3]]
    support, lift = support_lift(co, 4)
    assert support[0, 1] == pytest.approx(50.0)
    assert lift[0, 1] == pytest.approx(2 * 4 / (3 * 3))


def test_reorder_by_pooled_rate() -> None:
    """Tỉ lệ gộp theo dòng khác trung bình tỉ lệ từng đơn."""
    orders = pd.DataFrame({"k": [1, 1, 2], "size": [10, 2, 4], "reord": [5, 2, 0]})
    out = reorder_by(orders, "k")
    assert out.loc[1, "pooled_rate"] == pytest.approx(7 / 12)
    assert out.loc[2, "lines"] == 4


def test_standardize_and_pca_shapes() -> None:
    """z-score có trung bình 0 và PCA trả đủ 2 thành phần, phương sai tổng bằng 1."""
    rng = np.random.default_rng(0)
    table = pd.DataFrame(
        {
            "mean_gap": rng.uniform(1, 30, 200),
            "mean_basket": rng.uniform(1, 20, 200),
            "distinct_products": rng.integers(5, 300, 200),
            "reorder_rate": rng.uniform(0, 1, 200),
        }
    )
    z = standardize(table)
    assert z.mean().abs().max() < 1e-9
    scores, loadings, evr = pca(z)
    assert scores.shape == (200, 2) and loadings.shape == (4, 2)
    assert evr.sum() == pytest.approx(1.0)


def test_frequency_groups_are_balanced() -> None:
    """Ba nhóm phân vị có kích thước gần bằng nhau."""
    table = pd.DataFrame({"mean_gap": np.arange(300, dtype=float)})
    assert frequency_groups(table).value_counts().tolist() == [100, 100, 100]

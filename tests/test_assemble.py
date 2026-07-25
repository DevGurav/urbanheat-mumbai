"""The neighbourhood aggregation and the validation gate — the two bits of assembly logic
that would fail silently. Pure logic, no data needed."""

import numpy as np
import pandas as pd
import pytest

from data_pipeline.assemble import RANGES, _validate, neighbourhood_mean


def test_neighbourhood_mean_center_and_corner():
    # 3×3 lattice, value = 0..8 in row-major order.
    rows, cols, vals = [], [], []
    value = 0
    for r in range(3):
        for c in range(3):
            rows.append(r)
            cols.append(c)
            vals.append(float(value))
            value += 1
    df = pd.DataFrame({"grid_row": rows, "grid_col": cols, "x": vals})
    nm = neighbourhood_mean(df, "x")

    # Centre (row1,col1) = index 4; its 8 neighbours are every other cell → mean 4.0.
    assert nm.iloc[4] == pytest.approx(4.0)
    # Corner (0,0) = index 0; neighbours are (0,1)=1, (1,0)=3, (1,1)=4 → mean 8/3.
    assert nm.iloc[0] == pytest.approx((1 + 3 + 4) / 3)


def test_neighbourhood_mean_isolated_falls_back_to_own_value():
    df = pd.DataFrame({"grid_row": [0, 100], "grid_col": [0, 100], "x": [5.0, 9.0]})
    nm = neighbourhood_mean(df, "x")
    assert nm.tolist() == [5.0, 9.0]  # no neighbours → own value, never null


def _valid_features(n: int = 4) -> pd.DataFrame:
    """A minimal feature frame with every required/range-checked column at a valid value."""
    data = {"cell_id": list(range(n)), "ward_code": ["A"] * n}
    for col, (lo, hi) in RANGES.items():
        data[col] = [(lo + hi) / 2.0] * n
    return pd.DataFrame(data)


def test_validate_passes_on_a_valid_frame():
    df = _valid_features()
    _validate(df, df)  # must not raise


def test_validate_rejects_a_null_in_a_required_column():
    df = _valid_features()
    df.loc[0, "lst_mean"] = np.nan
    with pytest.raises(ValueError, match="null"):
        _validate(df, df)


def test_validate_rejects_an_out_of_range_value():
    df = _valid_features()
    df.loc[0, "albedo"] = 0.99  # albedo range is (0, 0.5)
    with pytest.raises(ValueError, match="range"):
        _validate(df, df)


def test_validate_rejects_duplicate_cell_ids():
    df = _valid_features()
    df.loc[1, "cell_id"] = df.loc[0, "cell_id"]
    with pytest.raises(ValueError, match="duplicate"):
        _validate(df, df)

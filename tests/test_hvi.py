"""The HVI must stay in [0, 1], rank correctly, and respond to its weights. Pure logic on a
tiny frame, plus a data-backed range check."""

import pandas as pd

from data_pipeline.ml.hvi import compute_hvi


def _land() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "cell_id": [1, 2, 3, 4],
            "ward_code": ["A", "A", "B", "B"],
            "lst_mean": [30.0, 40.0, 35.0, 50.0],
            "pop_density": [1000.0, 50000.0, 20000.0, 5000.0],
            "ndvi_mean": [0.60, 0.10, 0.30, 0.05],
        }
    )


def test_hvi_and_components_are_unit_range():
    hvi = compute_hvi(_land())
    for col in ["hvi", "hvi_heat", "hvi_exposure", "hvi_lack_green"]:
        assert hvi[col].between(0, 1).all(), col


def test_highest_hvi_is_rank_one():
    hvi = compute_hvi(_land())
    assert hvi["hotspot_rank"].min() == 1
    assert hvi.loc[hvi["hvi"].idxmax(), "hotspot_rank"] == 1


def test_weights_change_the_index():
    land = _land()
    heat_only = compute_hvi(land, {"heat": 1.0, "exposure": 0.0, "lack_green": 0.0})
    exp_only = compute_hvi(land, {"heat": 0.0, "exposure": 1.0, "lack_green": 0.0})
    assert not heat_only["hvi"].equals(exp_only["hvi"])


def test_hvi_on_real_features(features):
    land = features[features["land_fraction"] >= 0.5]
    hvi = compute_hvi(land)
    assert len(hvi) == len(land)
    assert hvi["hvi"].between(0, 1).all()

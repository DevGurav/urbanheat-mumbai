"""The scenario levers must move LST the physically-correct way and stay inside the envelope.
Pure logic with a stub model — no trained model or project data needed."""

import pandas as pd

from data_pipeline.ml.scenario import (
    COOL_ROOF_C_PER_BUILT,
    _clamp,
    cool_roof_delta,
    greening_clamped_mask,
    greening_delta,
)


class _CoolingModel:
    """Stand-in whose prediction falls as NDVI rises — so greening must cool."""

    def predict(self, X):
        return -10.0 * X["ndvi_mean"].to_numpy()


def test_cool_roof_is_cooling_and_scales_with_built_fraction():
    land = pd.DataFrame({"built_fraction": [0.0, 0.5, 1.0]})
    delta = cool_roof_delta(land)
    assert (delta <= 0).all()
    assert delta.iloc[0] == 0.0  # nothing built → nothing to cool
    assert delta.iloc[2] < delta.iloc[1]  # more roof → more cooling
    assert delta.iloc[2] == -COOL_ROOF_C_PER_BUILT  # fully built, full coverage


def test_clamp_holds_values_inside_the_envelope():
    clamped = _clamp(pd.DataFrame({"a": [5.0, -5.0]}), {"a": (0.0, 1.0)})
    assert clamped["a"].max() <= 1.0
    assert clamped["a"].min() >= 0.0


def test_greening_cools_under_a_cooling_model():
    land = pd.DataFrame(
        {
            "ndvi_mean": [0.10, 0.20, 0.35],
            "ndvi_neigh_mean": [0.10, 0.20, 0.30],
            "built_fraction": [0.6, 0.5, 0.4],
        }
    )
    features = ["ndvi_mean", "ndvi_neigh_mean", "built_fraction"]
    envelope = dict.fromkeys(features, (0.0, 1.0))
    delta = greening_delta(land, _CoolingModel(), features, envelope, ndvi_target=0.4)
    assert (delta <= 1e-9).all()  # cooling everywhere
    assert delta.iloc[0] < delta.iloc[2]  # the greyest cell (biggest NDVI rise) cools most


def test_greening_clamped_mask_flags_only_out_of_envelope_cells():
    # Both cells rise to ndvi_mean 0.40, but their smaller NDVI rise (target - start) means a
    # smaller neighbourhood rise too: cell 0's neighbourhood lands at 0.25 (0.10 + 0.5*0.30),
    # cell 1's at 0.375 (0.35 + 0.5*0.05) — only cell 1 pierces the 0.3 envelope ceiling below.
    land = pd.DataFrame({"ndvi_mean": [0.10, 0.35], "ndvi_neigh_mean": [0.10, 0.35]})
    features = ["ndvi_mean", "ndvi_neigh_mean"]
    envelope = {"ndvi_mean": (0.0, 1.0), "ndvi_neigh_mean": (0.0, 0.3)}
    mask = greening_clamped_mask(land, features, envelope, ndvi_target=0.4)
    assert mask.tolist() == [False, True]

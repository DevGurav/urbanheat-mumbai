"""The physics gate must fire on a load-bearing driver with the wrong sign, and must NOT fire
on a collinear/low-importance feature whose SHAP sign is credit-shared. Pure logic."""

from data_pipeline.ml.explain import GATED, PHYSICS_PRIOR, physics_violations


def _all_correct() -> dict[str, str]:
    return dict(PHYSICS_PRIOR)  # every feature at its physical prior


def test_gate_passes_when_load_bearing_signs_are_right():
    assert physics_violations(_all_correct()) == []


def test_gate_fires_on_a_load_bearing_violation():
    directions = _all_correct()
    directions["ndbi_mean"] = "cool"  # built-up must warm — this is a real failure
    assert any("ndbi_mean" in v for v in physics_violations(directions))


def test_gate_ignores_a_non_gated_collinear_flip():
    directions = _all_correct()
    # building_density is collinear with built_fraction — its sign is credit-shared, not gated.
    assert "building_density" not in GATED
    directions["building_density"] = "cool"
    assert physics_violations(directions) == []


def test_every_gated_feature_has_a_prior():
    assert GATED <= set(PHYSICS_PRIOR)

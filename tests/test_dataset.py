"""The modelling dataset must honour ADR-0008: no leakage or location column reaches X, and
the training filter and alignment hold. Data-backed — skips if features.parquet isn't built."""

from data_pipeline.ml.dataset import EXCLUDED, TARGET, build_dataset

MUST_NOT_BE_FEATURES = [
    "lst_mean",
    "lst_p90",
    "lst_obs_count",
    "wc_pixels",  # target + leakage
    "ward_code",
    "centroid_lat",
    "centroid_lon",  # absolute location
    "population",  # perfectly collinear with pop_density
    "cell_id",
    "grid_row",
    "grid_col",
    "geometry",  # identity
]


def test_no_excluded_column_reaches_x(features):
    data = build_dataset(frame=features)
    assert not (set(data.feature_names) & EXCLUDED)
    for col in MUST_NOT_BE_FEATURES:
        assert col not in data.feature_names, f"{col} must not be a feature"


def test_legitimate_features_are_kept(features):
    data = build_dataset(frame=features)
    # land_fraction is a geographic property (kept); the physical drivers must be present.
    for col in ["land_fraction", "ndbi_mean", "ndvi_mean", "albedo", "pop_density", "dist_coast"]:
        assert col in data.feature_names


def test_feature_count_is_30(features):
    # Schema lock: changing the feature set is a deliberate edit that updates this.
    assert len(build_dataset(frame=features).feature_names) == 30


def test_filter_and_alignment(features):
    data = build_dataset(frame=features)
    assert len(data.X) == len(data.y) == len(data.groups)
    assert len(data.X) == int((features["land_fraction"] >= 0.5).sum())
    assert data.X.notna().all().all()
    assert TARGET not in data.feature_names

"""Data-backed invariants on the assembled feature table. Skips if it hasn't been built.

These are the checks that would have caught the reducer-name traps (a mis-named reducer
output produces an all-null column) and any schema drift before the model sees it."""

WORLDCOVER_FRACTIONS = [
    "tree_fraction",
    "shrub_fraction",
    "grass_fraction",
    "crop_fraction",
    "built_fraction",
    "bare_fraction",
    "water_fraction",
    "wetland_fraction",
    "mangrove_fraction",
]

# One key column per source — all-null here means that source's reduction silently failed.
SOURCE_KEYS = [
    "lst_mean",
    "ndvi_mean",
    "ndbi_mean",
    "built_fraction",
    "population",
    "elevation_mean",
    "dist_coast",
    "building_density",
    "albedo",
    "air_temp_mean",
]

UNIT_RANGE = [
    *WORLDCOVER_FRACTIONS,
    "albedo",
    "building_density",
    "impervious_fraction",
    "land_fraction",
]


def test_row_count_is_the_full_grid(features):
    assert len(features) == 11944


def test_schema_is_42_columns(features):
    # A schema lock: adding/removing a feature is a deliberate change that updates this.
    assert features.shape[1] == 42


def test_cell_id_is_unique(features):
    assert features["cell_id"].is_unique


def test_no_source_produced_an_all_null_column(features):
    for col in SOURCE_KEYS:
        assert features[col].notna().all(), f"{col} has nulls — a reducer output was mis-named"


def test_p90_is_at_least_the_median(features):
    # lst_p90 is a temporal percentile ≥ the temporal median, per cell.
    assert (features["lst_p90"] >= features["lst_mean"] - 1e-6).all()


def test_worldcover_fractions_sum_to_one(features):
    total = features[WORLDCOVER_FRACTIONS].sum(axis=1)
    assert ((total > 0.98) & (total < 1.02)).all()


def test_unit_range_columns_stay_in_unit_range(features):
    for col in UNIT_RANGE:
        assert features[col].min() >= -1e-6, f"{col} below 0"
        assert features[col].max() <= 1 + 1e-6, f"{col} above 1"

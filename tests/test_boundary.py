"""The ward gate is the direct descendant of the Phase 0 boundary bug — a wrong or partial
ward set must fail loudly, by exact-set membership, not a count."""

import geopandas as gpd
import pytest
from shapely.geometry import box

from data_pipeline.boundary import EXPECTED_WARDS, WardValidationError, validate


def _wards(codes, crs=4326) -> gpd.GeoDataFrame:
    """Tiny non-overlapping boxes, one per ward code."""
    geoms = [box(i * 0.01, 0, i * 0.01 + 0.008, 0.008) for i in range(len(codes))]
    return gpd.GeoDataFrame({"ward_code": list(codes)}, geometry=geoms, crs=crs)


def test_missing_a_ward_is_rejected():
    codes = sorted(EXPECTED_WARDS)[:-1]  # 23 of 24
    with pytest.raises(WardValidationError, match="ward codes"):
        validate(_wards(codes))


def test_an_unexpected_ward_is_rejected():
    codes = [*sorted(EXPECTED_WARDS)[:-1], "Z"]  # drop one real code, add a bogus one
    with pytest.raises(WardValidationError, match="ward codes"):
        validate(_wards(codes))


def test_wrong_crs_is_rejected():
    with pytest.raises(WardValidationError, match="EPSG"):
        validate(_wards(sorted(EXPECTED_WARDS), crs=3857))


def test_real_wards_pass_validation(wards_gdf):
    """Data-backed: the actual DataMeet boundary must satisfy the full gate."""
    stats = validate(wards_gdf)
    assert stats["wards"] == 24
    assert 380 < stats["total_area_km2"] < 700

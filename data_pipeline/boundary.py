"""BMC administrative ward boundaries — the geometry everything else joins to.

Source: DataMeet `Municipal_Spatial_Data`, `Mumbai/BMC_Wards.geojson`, CC BY 4.0
(`docs/data-dictionary.md` §1). Already EPSG:4326, 24 features, one per administrative ward.

Run standalone with:

    uv run python -m data_pipeline.boundary
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

import geopandas as gpd

from data_pipeline.config import get_settings

WARDS_URL = (
    "https://raw.githubusercontent.com/datameet/Municipal_Spatial_Data"
    "/master/Mumbai/BMC_Wards.geojson"
)

# The 24 BMC administrative wards. This exact set is the primary validation gate.
#
# Checking the *set* rather than the count is deliberate. Phase 0's boundary bug passed a
# `count != 0` check while silently matching only one of two districts (docs/devlog.md,
# 2026-07-19). A wrong or truncated dataset cannot accidentally reproduce all 24 of these
# codes, so an exact set comparison is the strongest cheap check available.
# Grouped by letter so the E/W and N/S splits are checkable against a BMC ward map by eye.
# fmt: off
EXPECTED_WARDS = frozenset({
    "A", "B", "C", "D", "E",
    "F/N", "F/S",
    "G/N", "G/S",
    "H/E", "H/W",
    "K/E", "K/W",
    "L",
    "M/E", "M/W",
    "N",
    "P/N", "P/S",
    "R/C", "R/N", "R/S",
    "S", "T",
})
# fmt: on

STORAGE_CRS = 4326  # EPSG:4326 for storage and API responses (docs/conventions.md)
AREA_CRS = 32643  # EPSG:32643, UTM 43N, for area and distance maths

# The ward union measures ~458 km². The widely quoted "603 km²" for Greater Mumbai is the
# two *districts* (Mumbai City 157 + Mumbai Suburban 446), which include harbour, creek and
# tidal area that a municipal ward map excludes. FAO GAUL independently gives 487 km² for
# the same city. The bounds below are wide enough to admit either convention and narrow
# enough to catch a genuinely wrong dataset.
MIN_AREA_KM2 = 380.0
MAX_AREA_KM2 = 700.0


class WardValidationError(RuntimeError):
    """Raised when the ward dataset is not what the pipeline requires."""


def download(*, force: bool = False) -> Path:
    """Cache the source GeoJSON under `data/raw/`. Returns the local path."""
    settings = get_settings()
    settings.ensure_dirs()
    dest = settings.raw_dir / "BMC_Wards.geojson"

    if dest.exists() and not force:
        print(f"[boundary] using cached {dest.name} ({dest.stat().st_size / 1024:,.0f} KB)")
        return dest

    print(f"[boundary] downloading {WARDS_URL}")
    urllib.request.urlretrieve(WARDS_URL, dest)
    print(f"[boundary] saved {dest} ({dest.stat().st_size / 1024:,.0f} KB)")
    return dest


def validate(gdf: gpd.GeoDataFrame) -> dict[str, int | float | str]:
    """Fail loudly on anything that would corrupt the grid. Returns diagnostics.

    Every check here is exact or topological. The area check is deliberately a wide band
    rather than a target, because no two boundary sources agree on Mumbai's area — see the
    note on MIN_AREA_KM2 above.
    """
    if gdf.crs is None or gdf.crs.to_epsg() != STORAGE_CRS:
        raise WardValidationError(f"expected EPSG:{STORAGE_CRS}, got {gdf.crs}")

    found = set(gdf["ward_code"])
    if found != set(EXPECTED_WARDS):
        missing = sorted(EXPECTED_WARDS - found)
        unexpected = sorted(found - EXPECTED_WARDS)
        raise WardValidationError(
            f"ward codes do not match BMC's 24 administrative wards. "
            f"missing={missing} unexpected={unexpected}"
        )

    if (n_null := int(gdf.geometry.isna().sum())) > 0:
        raise WardValidationError(f"{n_null} null geometries")
    if (n_invalid := int((~gdf.geometry.is_valid).sum())) > 0:
        raise WardValidationError(f"{n_invalid} invalid geometries")

    projected = gdf.to_crs(AREA_CRS)
    per_ward = projected.geometry.area / 1e6
    total = float(per_ward.sum())

    # Wards must tile, not overlap. If they overlapped, a cell could be assigned to two
    # wards and every ward-level aggregate downstream would double-count it.
    union_area = float(projected.geometry.union_all().area / 1e6)
    overlap = total - union_area
    if overlap > 0.5:  # km², tolerance for coordinate noise on shared edges
        raise WardValidationError(f"wards overlap by {overlap:,.2f} km² — they must tile")

    if not MIN_AREA_KM2 <= total <= MAX_AREA_KM2:
        raise WardValidationError(
            f"total area {total:,.1f} km² outside [{MIN_AREA_KM2}, {MAX_AREA_KM2}] — "
            "this is not Greater Mumbai"
        )

    return {
        "wards": len(gdf),
        "total_area_km2": total,
        "union_area_km2": union_area,
        # Codes are looked up rather than hardcoded next to the numbers: a label asserting
        # "C ward" beside a computed minimum becomes a lie the moment the data changes.
        "smallest_ward": str(gdf.loc[per_ward.idxmin(), "ward_code"]),
        "smallest_ward_km2": float(per_ward.min()),
        "largest_ward": str(gdf.loc[per_ward.idxmax(), "ward_code"]),
        "largest_ward_km2": float(per_ward.max()),
    }


def build(*, force_download: bool = False) -> Path:
    """Fetch, validate and write `data/processed/wards.geojson`."""
    settings = get_settings()
    source = download(force=force_download)

    gdf = gpd.read_file(source)

    # `name` in the source is the BMC ward code ("A", "R/C"), not a place name. Renaming it
    # to ward_code keeps that honest — data-dictionary reserves `ward_name` for the official
    # ward names, which need a citable source before they are used anywhere user-facing.
    gdf = gdf.rename(columns={"name": "ward_code"})[["ward_code", "geometry"]]

    stats = validate(gdf)

    # Carried through so downstream stages never recompute a projection to get an area.
    gdf["area_km2"] = (gdf.to_crs(AREA_CRS).geometry.area / 1e6).round(4)
    gdf = gdf.sort_values("ward_code").reset_index(drop=True)

    dest = settings.processed_dir / "wards.geojson"
    # 6 decimal places ≈ 0.11 m, the precision RFC 7946 recommends and roughly 2000× finer
    # than the 200 m grid (ADR-0007). Writing float64's full ~15 digits stores noise: it
    # quadruples the file for precision neither the source survey nor this project has.
    # No vertices are removed — this is not simplification.
    gdf.to_file(dest, driver="GeoJSON", COORDINATE_PRECISION=6)

    print(f"[boundary] {stats['wards']} wards validated")
    print(f"[boundary]   total area {stats['total_area_km2']:>8,.1f} km²")
    print(
        f"[boundary]   smallest   {stats['smallest_ward_km2']:>8,.2f} km²"
        f"  ({stats['smallest_ward']})"
    )
    print(
        f"[boundary]   largest    {stats['largest_ward_km2']:>8,.2f} km²  ({stats['largest_ward']})"
    )
    print(f"[boundary] wrote {dest}")
    return dest


if __name__ == "__main__":
    build()

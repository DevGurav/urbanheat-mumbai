"""Open-Meteo weather covariates, one row per grid cell.

Produces `data/interim/weather.parquet`: `air_temp_mean`, `humidity_mean`, `wind_speed_mean`
— dry-season (Mar–May) multi-year means from the Open-Meteo ERA5 archive (keyless).

⚠️ These are **city-scale context, not within-city drivers**. ERA5 is ~11 km, so across a
458 km² city the values barely move — measured spread is ~0.6 °C air temperature against
LST's ~20 °C. The stage therefore queries a coarse point grid (not per cell) and assigns each
cell its nearest point. Phase 2 decides empirically whether these survive feature selection
(`data-dictionary.md` §weather); this stage's job is to produce them honestly and quantify how
little they vary.

Run standalone with:

    uv run python -m data_pipeline.sources.weather                 # cached points + build
    uv run python -m data_pipeline.sources.weather --force-download # re-query Open-Meteo
"""

from __future__ import annotations

import argparse
import statistics as st
import time

import geopandas as gpd
import numpy as np
import pandas as pd
import requests

from data_pipeline.config import get_settings

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
START_DATE, END_DATE = "2019-03-01", "2026-05-31"  # matches the LST window; filtered to Mar–May
DRY_MONTHS = (3, 4, 5)

# ERA5 is ~11 km (~0.1°), so a 0.1° point grid (~15 points over the city) already samples
# every distinct grid cell — finer just re-hits the same value and inflates the API cost,
# which the archive rate-limits by locations × days.
POINT_STEP_DEG = 0.1

# Open-Meteo accepts many locations per request (comma-separated coords); the whole point
# grid fits in one batch at this spacing.
BATCH_SIZE = 25

# Open-Meteo daily variable → our column name. wind requested in m/s (default is km/h).
VARIABLES = {
    "temperature_2m_mean": "air_temp_mean",
    "relative_humidity_2m_mean": "humidity_mean",
    "wind_speed_10m_mean": "wind_speed_mean",
}


def _query_points(grid: gpd.GeoDataFrame) -> list[tuple[float, float]]:
    """A regular lon/lat grid over the study bounds, at ERA5-ish spacing."""
    minx, miny, maxx, maxy = grid.to_crs(4326).total_bounds
    lons = np.arange(minx, maxx + POINT_STEP_DEG, POINT_STEP_DEG)
    lats = np.arange(miny, maxy + POINT_STEP_DEG, POINT_STEP_DEG)
    return [(round(float(lon), 4), round(float(lat), 4)) for lat in lats for lon in lons]


def _dry_season_means(daily: dict) -> dict[str, float]:
    """Reduce one location's daily series to its Mar–May multi-year mean per variable."""
    days = daily["time"]
    means = {}
    for src, dst in VARIABLES.items():
        vals = [
            v
            for day, v in zip(days, daily[src], strict=True)
            if v is not None and int(day[5:7]) in DRY_MONTHS
        ]
        means[dst] = st.mean(vals)
    return means


def _fetch_batch(points: list[tuple[float, float]], *, retries: int = 4) -> list[dict[str, float]]:
    """Fetch a batch of points in one request (comma-separated coords), with backoff on 429."""
    lats = ",".join(str(lat) for _, lat in points)
    lons = ",".join(str(lon) for lon, _ in points)
    params = {
        "latitude": lats,
        "longitude": lons,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "daily": ",".join(VARIABLES),
        "wind_speed_unit": "ms",
        "timezone": "Asia/Kolkata",
    }
    for attempt in range(retries):
        resp = requests.get(ARCHIVE_URL, params=params, timeout=120)
        if resp.status_code == 429:
            wait = 20 * (attempt + 1)
            print(f"[weather]   rate-limited, waiting {wait}s…", flush=True)
            time.sleep(wait)
            continue
        resp.raise_for_status()
        data = resp.json()
        # Multiple locations → a JSON array; a single location → a lone object.
        results = data if isinstance(data, list) else [data]
        return [_dry_season_means(r["daily"]) for r in results]
    raise RuntimeError("Open-Meteo kept returning 429 after retries")


def download(settings, grid: gpd.GeoDataFrame, *, force: bool = False) -> pd.DataFrame:
    """Fetch the point grid's dry-season means; cache to `data/raw/`."""
    settings.ensure_dirs()
    cache = settings.raw_dir / "openmeteo_points.parquet"
    if cache.exists() and not force:
        print(f"[weather] using cached Open-Meteo points ({cache.name})")
        return pd.read_parquet(cache)

    points = _query_points(grid)
    yrs = f"{START_DATE[:4]}–{END_DATE[:4]}"
    print(f"[weather] querying Open-Meteo at {len(points)} points, Mar–May {yrs}")
    rows = []
    for start in range(0, len(points), BATCH_SIZE):
        batch = points[start : start + BATCH_SIZE]
        means = _fetch_batch(batch)
        for (lon, lat), m in zip(batch, means, strict=True):
            rows.append({"lon": lon, "lat": lat, **m})
        print(f"[weather]   {len(rows)}/{len(points)} points", flush=True)
        if start + BATCH_SIZE < len(points):
            time.sleep(2)  # be polite between batches

    df = pd.DataFrame(rows)
    df.to_parquet(cache, index=False)
    print(f"[weather] cached {len(df)} points to {cache}")
    return df


def build(*, force_download: bool = False, write: bool = True) -> pd.DataFrame:
    """Assign each grid cell the weather of its nearest Open-Meteo point."""
    settings = get_settings()
    grid = gpd.read_parquet(settings.interim_dir / "grid.parquet")
    points_df = download(settings, grid, force=force_download)

    # Nearest-point assignment, done in metres (UTM) so "nearest" is true distance and the
    # centroids are computed in a projected CRS (not degrees).
    points = gpd.GeoDataFrame(
        points_df,
        geometry=gpd.points_from_xy(points_df["lon"], points_df["lat"]),
        crs=4326,
    ).to_crs(32643)
    grid_utm = grid.to_crs(32643)
    centroids = gpd.GeoDataFrame(
        {"cell_id": grid["cell_id"]}, geometry=grid_utm.geometry.centroid, crs=32643
    )

    cols = list(VARIABLES.values())
    joined = gpd.sjoin_nearest(centroids, points[["geometry", *cols]], how="left")
    # sjoin_nearest can duplicate a cell on ties; keep the first match per cell.
    joined = joined.drop_duplicates(subset="cell_id")

    weather = grid[["cell_id"]].merge(joined[["cell_id", *cols]], on="cell_id", how="left")
    _report(weather, grid, points_df)

    if write:
        dest = settings.interim_dir / "weather.parquet"
        weather.to_parquet(dest, index=False)
        print(f"[weather] wrote {dest}")

    return weather


def _report(weather: pd.DataFrame, grid: gpd.GeoDataFrame, points: pd.DataFrame) -> None:
    """Print the checks — and quantify how little weather varies (the point of the stage)."""
    if len(weather) != len(grid):
        raise ValueError(f"row count {len(weather):,} != grid {len(grid):,}")
    cols = list(VARIABLES.values())
    if weather[cols].isna().any().any():
        raise ValueError("some cells have no weather — nearest-point assignment failed")

    print(f"[weather] {len(weather):,} cells from {len(points)} Open-Meteo points")
    units = {"air_temp_mean": "°C", "humidity_mean": "%", "wind_speed_mean": "m/s"}
    for c in cols:
        spread = weather[c].max() - weather[c].min()
        print(
            f"[weather]   {c:16} mean {weather[c].mean():6.2f}  "
            f"city spread {spread:5.2f} {units[c]}"
        )
    print("[weather]   (near-constant by design — city-scale context, not a within-city driver)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force-download", action="store_true", help="re-query Open-Meteo, ignoring the cache"
    )
    args = parser.parse_args()
    build(force_download=args.force_download)

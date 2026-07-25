"""OpenStreetMap building, road and park features per grid cell.

Produces `data/interim/osm.parquet`: `building_count`, `building_density`, `road_density`,
`dist_park`. Unlike the Earth Engine sources this downloads vector geometry from Overpass
(via OSMnx) and does the cell aggregation locally, so raw downloads are cached under
`data/raw/` — Overpass is a shared free service and should not be re-queried on every run.

⚠️ OSM building coverage in Indian cities is incomplete and uneven (informal settlements are
under-mapped), so `building_count`/`building_density` are **relative** indicators, not a true
footprint census. The stage validates them against WorldCover `built_fraction`; roads and
park proximity are better mapped.

Run standalone with:

    uv run python -m data_pipeline.sources.osm                 # download (cached) + build
    uv run python -m data_pipeline.sources.osm --force-download # re-fetch from Overpass
"""

from __future__ import annotations

import argparse

import geopandas as gpd
import osmnx as ox
import pandas as pd

from data_pipeline.config import get_settings

UTM_CRS = 32643  # metres, for area/length/distance
CELL_AREA_M2 = 200 * 200

BUILDING_TAGS = {"building": True}
PARK_TAGS = {
    "leisure": ["park", "garden", "nature_reserve"],
    "landuse": ["forest", "recreation_ground", "grass"],
}
# Drivable roads only — the main paved (impervious) network. "all" would pull footways and
# service alleys, multiplying the data for little heat signal.
ROAD_NETWORK = "drive"


def _study_polygon(settings) -> object:
    wards = gpd.read_file(settings.processed_dir / "wards.geojson")
    return wards.geometry.union_all()


def download(settings, *, force: bool = False) -> tuple:
    """Fetch buildings, roads and parks for the whole study area; cache to `data/raw/`."""
    settings.ensure_dirs()
    raw = settings.raw_dir
    paths = {
        "buildings": raw / "osm_buildings.gpkg",
        "roads": raw / "osm_roads.gpkg",
        "parks": raw / "osm_parks.gpkg",
    }
    if not force and all(p.exists() for p in paths.values()):
        print("[osm] using cached Overpass downloads in data/raw/")
        return paths["buildings"], paths["roads"], paths["parks"]

    poly = _study_polygon(settings)

    print("[osm] downloading buildings from Overpass…")
    b = ox.features_from_polygon(poly, BUILDING_TAGS)
    b = b[b.geometry.type.isin(["Polygon", "MultiPolygon"])][["geometry"]].reset_index(drop=True)
    b.to_file(paths["buildings"], driver="GPKG")
    print(f"[osm]   {len(b):,} building footprints")

    print("[osm] downloading road network from Overpass…")
    graph = ox.graph_from_polygon(poly, network_type=ROAD_NETWORK, retain_all=True)
    edges = ox.graph_to_gdfs(graph, nodes=False)[["geometry"]].reset_index(drop=True)
    edges.to_file(paths["roads"], driver="GPKG")
    print(f"[osm]   {len(edges):,} road segments")

    print("[osm] downloading parks/green from Overpass…")
    p = ox.features_from_polygon(poly, PARK_TAGS)
    p = p[p.geometry.type.isin(["Polygon", "MultiPolygon"])][["geometry"]].reset_index(drop=True)
    p.to_file(paths["parks"], driver="GPKG")
    print(f"[osm]   {len(p):,} park/green polygons")

    return paths["buildings"], paths["roads"], paths["parks"]


def build(*, force_download: bool = False, write: bool = True) -> pd.DataFrame:
    """Aggregate OSM buildings, roads and parks to one row per grid cell."""
    settings = get_settings()
    grid = gpd.read_parquet(settings.interim_dir / "grid.parquet").to_crs(UTM_CRS)
    b_path, r_path, p_path = download(settings, force=force_download)

    buildings = gpd.read_file(b_path).to_crs(UTM_CRS)
    roads = gpd.read_file(r_path).to_crs(UTM_CRS)
    parks = gpd.read_file(p_path).to_crs(UTM_CRS)
    cells = grid[["cell_id", "geometry"]]

    # --- buildings: assign each to the cell containing its representative point, so a
    # building straddling a border counts once. footprint area summed per cell. ---
    buildings["footprint_m2"] = buildings.geometry.area
    pts = buildings.set_geometry(buildings.geometry.representative_point())
    joined = gpd.sjoin(pts, cells, predicate="within")
    per_cell = joined.groupby("cell_id")["footprint_m2"].agg(["size", "sum"])
    per_cell.columns = ["building_count", "footprint_m2"]

    # --- roads: split each segment at cell borders, sum clipped length per cell. ---
    clipped = gpd.overlay(roads, cells, how="intersection", keep_geom_type=True)
    clipped["len_m"] = clipped.geometry.length
    road_len = clipped.groupby("cell_id")["len_m"].sum()

    # --- dist_park: metres from the cell centroid to the nearest park polygon. ---
    centroids = cells.set_geometry(cells.geometry.centroid)[["cell_id", "geometry"]]
    near = gpd.sjoin_nearest(centroids, parks[["geometry"]], distance_col="dist_park")
    dist_park = near.groupby("cell_id")["dist_park"].min()

    osm = grid[["cell_id"]].copy()
    osm = osm.merge(per_cell, on="cell_id", how="left")
    osm = osm.merge(road_len.rename("road_len_m"), on="cell_id", how="left")
    osm = osm.merge(dist_park.rename("dist_park"), on="cell_id", how="left")

    osm["building_count"] = osm["building_count"].fillna(0).astype(int)
    osm["building_density"] = (osm["footprint_m2"].fillna(0) / CELL_AREA_M2).clip(upper=1.0)
    osm["road_density"] = osm["road_len_m"].fillna(0) / CELL_AREA_M2
    osm = osm.drop(columns=["footprint_m2", "road_len_m"])

    _report(osm, grid)

    if write:
        dest = settings.interim_dir / "osm.parquet"
        osm.to_parquet(dest, index=False)
        print(f"[osm] wrote {dest}")

    return osm


def _report(osm: pd.DataFrame, grid: gpd.GeoDataFrame) -> None:
    """Print the checks that would catch a silently wrong join."""
    if len(osm) != len(grid):
        raise ValueError(f"row count {len(osm):,} != grid {len(grid):,}")
    if osm["cell_id"].duplicated().any():
        raise ValueError("duplicate cell_id in the OSM aggregation")

    n_bldg = int((osm["building_count"] > 0).sum())
    n_road = int((osm["road_density"] > 0).sum())
    bc, bd = osm["building_count"], osm["building_density"]
    rd, dp = osm["road_density"], osm["dist_park"]
    print(f"[osm] {len(osm):,} cells: {n_bldg:,} with buildings, {n_road:,} with roads")
    print(f"[osm]   building_count   total {bc.sum():,}  max {bc.max():,}")
    print(f"[osm]   building_density median {bd.median():.3f}  max {bd.max():.3f}")
    print(f"[osm]   road_density     median {rd.median():.4f}  max {rd.max():.4f} m/m²")
    print(f"[osm]   dist_park        median {dp.median():,.0f}  max {dp.max():,.0f} m")

    if osm["dist_park"].isna().any():
        raise ValueError("some cells have no dist_park — the parks layer is empty or unmatched")
    if osm["building_density"].max() > 1.0:
        raise ValueError("building_density exceeds 1 — footprint area is being over-counted")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force-download", action="store_true", help="re-fetch from Overpass, ignoring the cache"
    )
    args = parser.parse_args()
    build(force_download=args.force_download)

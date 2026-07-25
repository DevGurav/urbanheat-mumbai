"""Pipeline entry point.

    uv run python -m data_pipeline.run --stage all
    uv run python -m data_pipeline.run --stage landsat --force

Stages run in dependency order and are **skipped when their output already exists**, so a
failure part-way through does not force a rebuild of everything before it. That matters
because the Earth Engine stages spend a finite monthly compute quota (ADR-0001) — re-running
them for free is not an option, and `--force` is the deliberate way to ask for it.
"""

from __future__ import annotations

import argparse
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from data_pipeline.config import get_settings


@dataclass(frozen=True)
class Stage:
    name: str
    run: Callable[[], object]
    output: str  # path relative to data_dir, used as the completion marker
    spends_quota: bool = False


def _stages() -> list[Stage]:
    # Imported lazily: `--stage boundary` should not need Earth Engine to be reachable.
    from data_pipeline import assemble, boundary, grid
    from data_pipeline.sources import (
        albedo,
        landsat,
        osm,
        sentinel2,
        terrain,
        weather,
        worldcover,
        worldpop,
    )

    return [
        Stage("boundary", boundary.build, "processed/wards.geojson"),
        Stage("grid", grid.build, "interim/grid.parquet"),
        Stage("landsat", landsat.build, "interim/lst.parquet", spends_quota=True),
        Stage("albedo", albedo.build, "interim/albedo.parquet", spends_quota=True),
        Stage("sentinel2", sentinel2.build, "interim/sentinel2.parquet", spends_quota=True),
        Stage("worldcover", worldcover.build, "interim/worldcover.parquet", spends_quota=True),
        Stage("worldpop", worldpop.build, "interim/worldpop.parquet", spends_quota=True),
        Stage("terrain", terrain.build, "interim/terrain.parquet", spends_quota=True),
        # Not Earth Engine — downloads from Overpass (OSMnx), cached in data/raw/.
        Stage("osm", osm.build, "interim/osm.parquet"),
        # Not Earth Engine — Open-Meteo archive (keyless HTTP), cached in data/raw/.
        Stage("weather", weather.build, "interim/weather.parquet"),
        # Final join of every source into the feature table the API and models read.
        Stage("assemble", assemble.build, "processed/features.parquet"),
    ]


def main(argv: list[str] | None = None) -> int:
    stages = _stages()
    names = [s.name for s in stages]

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", default="all", choices=["all", *names])
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-run even if the output exists; on Earth Engine stages this spends quota",
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    settings.ensure_dirs()
    selected = stages if args.stage == "all" else [s for s in stages if s.name == args.stage]

    for stage in selected:
        output = Path(settings.data_dir) / stage.output
        if output.exists() and not args.force:
            print(f"[run] {stage.name}: skipped, {stage.output} exists (--force to rebuild)")
            continue

        note = " (spends Earth Engine quota)" if stage.spends_quota else ""
        print(f"[run] {stage.name}: running{note}")
        started = time.time()
        stage.run()
        print(f"[run] {stage.name}: done in {time.time() - started:,.0f}s")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

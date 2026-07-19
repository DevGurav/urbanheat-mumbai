"""UrbanHeat data pipeline.

Builds `data/processed/features.parquet` — one row per ~200 m cell of Greater Mumbai
(ADR-0007) — from Earth Engine, OpenStreetMap and Open-Meteo sources.

Stages are run through `python -m data_pipeline.run --stage <name>` and cache their
intermediate output under `data/interim/`, so a failed stage does not force a full rebuild.
Nothing here writes to `data/processed/` except the final assembly step.
"""

__version__ = "0.1.0"

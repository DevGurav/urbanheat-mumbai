"""UrbanHeat AI backend — a FastAPI over the trained model, HVI and scenario engine.

Reads the Phase 1–2 artifacts (`features.parquet`, `hvi.parquet`, `wards.geojson`,
`model.joblib`, `shap_values.parquet`) into memory once at startup and serves them — no
database (ADR-0004), no Redis (ADR-0003). Contracts live in `docs/api-reference.md`.
"""

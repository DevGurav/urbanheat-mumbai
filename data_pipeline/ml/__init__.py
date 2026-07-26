"""Phase 2 modelling — predict and explain surface temperature.

`dataset.py` turns `features.parquet` into X / y / CV groups under the ADR-0008 policy;
`cv.py` is the ward-grouped spatial cross-validation; `train.py` runs the model ladder.
Everything runs locally on the ~12k-row table — no Earth Engine, no GPU (ADR-0006).
"""

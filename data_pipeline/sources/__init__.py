"""One module per data source, each reducing to a table keyed on `cell_id`.

Every module here exposes `build()` and writes `data/interim/<source>.parquet`. The assembly
stage joins them; nothing in this package writes to `data/processed/`.
"""

# Backend image — Phase 6 Deployment (PROGRESS.md, ADR-0004).
#
# Built and pushed by the author, locally, not by Render or a CI runner (runbook.md's
# Deployment section). The reason is `COPY`s below: `data/processed/*`, `models/*`, and
# `backend/rag/chroma_db/` are all gitignored (ADR-0004 — regenerable build outputs, not
# committed) and only exist on whichever machine actually ran the pipeline. Render's
# build-from-source and GitHub Actions both lack Earth Engine credentials and the compute
# quota to regenerate them, so this image bakes in whatever the author has locally validated,
# exactly as ADR-0004 already frames "regenerate" as a deliberate local action.
#
# Installs pyproject.toml's base `dependencies` only, not the `pipeline` extra —
# earthengine-api/geemap/osmnx/lightgbm/shap etc. are confirmed unused by backend/main.py's
# import graph (pyproject.toml's own comment has the detail), and Render's free tier caps
# memory at 512MB.

FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1

# Dependency layer first, separate from application code — rebuilding after a source change
# doesn't re-resolve or re-download packages, only after pyproject.toml/uv.lock change.
#
# --mount=type=cache keeps uv's download cache in a BuildKit cache mount, not the image layer
# itself — without it, every downloaded wheel (torch-cpu, pyarrow, chromadb, ...) sits in the
# layer twice: once installed into .venv, once still in the cache. Caught by `docker history`
# showing this single layer at 3.94GB against a 2.1GB actual .venv — nearly 2GB of pure cache
# bloat with no reason to ship to Render.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# hatchling (build-system) reads pyproject.toml's `readme = "README.md"` when building the
# local `urbanheat` package itself in the final `uv sync` below — without it, that step fails
# with an opaque "Build failures usually indicate..." hint and no actual reason shown.
COPY README.md ./
COPY backend/ backend/
# backend/rag/chroma_db/ (also gitignored — the built RAG index) rides along in the line
# above; .dockerignore does not exclude it, unlike .gitignore.
COPY data_pipeline/ data_pipeline/

# The gitignored artifacts (backend/store.py's exact read set — grepped, not guessed).
# alerts_state.json / alerts.jsonl are deliberately NOT copied: local dedupe history has no
# business seeding a fresh deployment (backend/agents/alerts.py starts clean when absent).
COPY data/processed/features.parquet data/processed/hvi.parquet data/processed/wards.geojson data/processed/
COPY models/model.joblib models/model_meta.json models/shap_values.parquet models/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Pre-warm the RAG embedding model into the image at build time, on a reliable network, once
# — rather than every container boot re-downloading it from HuggingFace at request time.
# Caught via the smoke-test container's own startup log: ~34s spent on HF Hub HTTP calls
# before "agent supervisor ready", stacking on top of Render's own free-tier cold start.
# HF_HUB_OFFLINE=1 at runtime then trusts this baked-in cache and skips the network
# entirely — deterministic startup, not dependent on HuggingFace being reachable on boot.
ENV HF_HOME=/app/.cache/huggingface
RUN --mount=type=cache,target=/root/.cache/uv \
    uv run --no-sync python -c \
    "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"
ENV HF_HUB_OFFLINE=1

EXPOSE 8000
# --no-sync: the venv above is already exactly what --frozen --no-dev built; a plain
# `uv run` re-syncs against pyproject.toml at every container start with none of those flags,
# which pulled in `ruff` (a dev-only tool) over the network on every boot — caught by
# reading the smoke-test container's own startup log, not assumed.
CMD ["uv", "run", "--no-sync", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

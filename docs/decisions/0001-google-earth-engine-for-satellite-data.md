# ADR-0001 — Google Earth Engine for satellite data

**Status:** Accepted
**Date:** 2026-07-17
**Phase:** 0

## Context

The model needs, for every ~200 m cell of Mumbai: surface temperature, vegetation index,
built-up index, land cover, population and elevation — as multi-year, cloud-filtered,
dry-season composites. Raw imagery for this is large: a single Landsat scene is ~1 GB, and
compositing several years across a metro area means hundreds of gigabytes of intermediate
raster. The development machine has ~10 GB of free disk, 8–16 GB RAM, no GPU, and a
consumer internet connection. Budget is ₹0.

## Options considered

### A — Download scenes from USGS EarthExplorer / Copernicus Open Access Hub, process locally with `rasterio`/`xarray`

**Pros** No account approval wait; total control; works offline once downloaded; no
external quota.
**Cons** Hundreds of GB of downloads over a home connection; disk budget blown by an order
of magnitude; cloud masking, atmospheric correction and co-registration all become our
problem; every re-run costs hours. This alone could consume the project's first month.

### B — Google Earth Engine (Python API)

**Pros** Petabyte catalog already analysis-ready — Landsat 8/9 Collection-2 Level-2 arrives
atmospherically corrected with QA bands; compositing and cloud masking run server-side on
Google's cluster; we download only the reduced ~20k-row table (a few MB); Sentinel-2, ESA
WorldCover, WorldPop and SRTM live in the same catalog with one join model; free for
students and noncommercial use.
**Cons** Requires noncommercial registration approval; monthly compute-unit quota; a
proprietary lazy-evaluation API with a real learning curve (`getInfo()` misuse will burn
quota fast); vendor lock-in for the pipeline; needs internet to run at all.

### C — Microsoft Planetary Computer (STAC + Dask)

**Pros** Open standards (STAC), no proprietary API, generous free hub.
**Cons** Free compute hub availability has been unreliable; more assembly required for
cloud masking and compositing; smaller body of UHI-specific example code to learn from;
still needs an account.

## Decision

**Google Earth Engine.**

The deciding factor is where the compute happens. Options A and C put terabyte-scale raster
work on a laptop or an unreliable hub; B keeps it in Google's cloud and hands us a table
small enough to open in pandas. Given a ₹0 budget, no GPU and a six-month schedule shared
with five other phases, the data-engineering work that B eliminates is the difference
between finishing and not. The noncommercial tier's student eligibility makes it free, and
the surrounding literature and tutorials for UHI/LST work are overwhelmingly GEE-based —
which matters for a sole developer who must defend the methodology.

## Consequences

**Positive**
- Feature extraction becomes a scripting problem, not an infrastructure problem.
- All predictor datasets are pre-aligned in one catalog; joins are cheap.
- Multi-year composites become feasible, which makes trend analysis possible at all.
- Re-running the pipeline for a new city is a boundary swap.

**Negative**
- Hard dependency on account approval — this is Phase 0's only blocking item, so it is
  started on day 1.
- The pipeline cannot run offline; a network outage stalls Phase 1 work.
- Compute quota is finite: exports must be aggregates, and `getInfo()` must never be
  called in a per-cell loop. This is written into `docs/conventions.md` as a standing rule.
- Lock-in: porting to another provider means rewriting `data-pipeline/`. Accepted — the
  pipeline is one bounded layer, and its output (`features.parquet`) is a plain,
  portable artifact that everything downstream depends on instead.

**Revisit if** registration is rejected, or the monthly quota proves too small for
multi-year compositing — in which case fall back to option C for the imagery while keeping
the same output contract.

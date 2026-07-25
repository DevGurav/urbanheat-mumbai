# Devlog

Engineering journal — one entry per working session, newest first. Written for the future
author: what moved, what broke, what was decided, what to pick up next.

**Why keep this.** By Phase 7 the report needs a narrative — what was tried, what failed,
why the design is what it is. That narrative is impossible to reconstruct from a git log
six months later. Dead ends recorded here are worth as much as successes; a viva panel asks
"what didn't work?" and a real answer is a strong one.

**Entry template**

```markdown
## YYYY-MM-DD — Phase N — Title

**Done**
**Decided**
**Broke / learned**
**Next**
```

---

## 2026-07-20 — Phase 1 — WorldPop population, and the HVI signal is real

**Done**
- `sources/worldpop.py` → `data/interim/worldpop.parquet`: `population` (persons) and
  `pop_density` (persons/km²) over 11,944 cells. WorldPop `GP/100m/pop`, year 2020, 81 s.
  Registered as a `run.py` stage.

**Decided**
- **Year 2020**, the latest the collection offers (it ends at 2020) — one year inside the
  2019–2026 LST window. Closes the alignment question data-dictionary §5 had left open.
- **Sum reducer at native 100 m.** WorldPop stores a *person count* per pixel, so the cell
  value is a sum, not a mean, and a count must be summed at native resolution — reducing at a
  coarser scale would mis-count. `pop_density` divides by the full 0.04 km² cell.

**Broke / learned**
- **`Reducer.sum()` names its output `sum`, not after the band** — the same trap as
  WorldCover's `histogram`. First run read a `population` property, got 0 everywhere, and the
  total-population reconciliation guard fired: "total 0 is not near Mumbai's ~12 M". That guard
  is the whole point of the stage — a population layer that silently zeroed would be invisible
  without it. There is now a clear pattern worth internalising: **non-default reducers name
  their output after the reducer, and the shared helper must be told that name.**
- **The reconciliation is the strongest check in the pipeline so far.** Total over the grid is
  **11.7 M** against BMC's ~12.4 M census. That single number confirms units, year and mosaic
  in one shot — worth more than any range assertion.

**Results — the HVI premise holds**
- `pop_density` vs `built_fraction` **+0.74**, vs tree/water −0.31/−0.33: people live in the
  built-up cells, not the parks or the creeks, exactly as they should.
- **`pop_density` vs `lst_mean` +0.56** — population and surface heat co-locate. This is the
  finding the Heat Vulnerability Index rests on: the people are where the heat is. Without this
  correlation the HVI would be averaging two unrelated things.
- The densest cells resolve to Dharavi (G/N) and Parel (F/S) at ~65,000/km², Mumbai's known
  dense cores. 225 cells are in the top decile of *both* density and LST, clustered in Kurla,
  Ghatkopar, Parel and Dharavi — the HVI's future hotspot list, visible already in the raw data.

**Next**
- SRTM elevation + slope, then distance-to-coast/water/park. These are the terrain and
  context features; distance-to-coast is expected to matter a lot in Mumbai (sea breeze).
- Still no `pytest`; the reducer-name traps (`sum`, `histogram`) would each be a one-line
  regression test worth having before there are eight source modules to keep straight.

---

## 2026-07-20 — Phase 1 — ESA WorldCover land-cover fractions

**Done**
- `sources/worldcover.py` → `data/interim/worldcover.parquet`: nine per-class fractions per
  cell plus `wc_pixels`, over 11,944 cells, 0 empty. Single static 10 m mosaic, so the full
  grid ran in 78 s. Registered as a `run.py` stage.

**Decided**
- **Widened the class list from the planned tree/grass/built.** Inspection over four
  representative cells showed the plan missed what Mumbai actually is: the greenest cell is
  100% **mangrove** (class 95), and the hottest is 71% **cropland** (class 40). Kept all nine
  occurring classes — city composition came out built 39%, tree 34%, mangrove 10%, water 8%,
  crop 4%. Mangrove alone is 10% of the city with a −0.46 LST correlation; lumping it into
  "tree" would have hidden a major distinct cooler.
- **Frequency-histogram reducer, fractions as share of the whole cell.** The sea is class 80,
  not masked, so every cell has ~425 classified pixels and the fractions sum to 1 (asserted).
  Reduced at native 10 m — categorical class codes must be counted at native scale, never
  resampled to a coarser one.

**Broke / learned**
- **`reduceRegions` names a frequency-histogram output `histogram`, not after the band.** My
  first pass read a `Map` property and every cell came back empty; the reducer, not the band,
  names the property. Caught immediately by the "every cell empty" guard, which is exactly the
  failure that guard exists for. Fixed to read `histogram`.
- **"Cropland" in Mumbai is dry bare ground, not farmland.** Crop-dominated cells are the
  *hottest* land in the city (42.6 °C mean, above built's 41.9; 12 of the 20 hottest are
  crop). WorldCover labels the Deonar dump, fallow and dry-season bare land as cropland.
  Recorded as a caveat — using `crop_fraction` as "agriculture" would be wrong.
- **The water-disambiguation feature works, decisively.** The 285 low-NDVI *cool* cells that
  NDVI alone could not explain (the Sentinel-2 entry flagged them) have mean `water_fraction`
  0.96 vs 0.03 elsewhere. They are inland water and creeks. The reason for keeping the water
  class is now evidence, not a hunch.
- **Two independent datasets corroborate.** WorldCover fractions agree with the Sentinel-2
  indices — built↔NDBI +0.46, tree↔NDVI +0.53, water↔NDWI +0.57 — which is the cross-check
  that matters more than any single number: two different instruments telling the same story.

**Next**
- WorldPop population density per cell — the human-exposure layer, and the first that is not
  about the physical surface.
- Still no `pytest`; the WorldCover class-sum invariant and the cross-dataset checks ran as
  scratch scripts.

---

## 2026-07-20 — Phase 1 — Sentinel-2 indices, and the premise holds in the data

**Done**
- Refactored the chunked `reduceRegions` machinery out of `landsat.py` into
  `sources/_reduce.py` (shared reducer + study-region helper). Landsat now calls it —
  verified byte-identical, 0.000e+00 diff over 500 cells, so no quota re-spent.
- `sources/sentinel2.py` → `data/interim/sentinel2.parquet`: `ndvi_mean`, `ndvi_p10`,
  `ndbi_mean`, `ndwi_mean` over 11,944 cells, 542 dry-season scenes, 0 nulls. ~10.6 min.
- Registered `sentinel2` as a `run.py` stage.

**Results — the acceptance test passed**
- **NDBI vs LST = +0.74**, the strongest single relationship: built-up index drives surface
  heat harder than vegetation absence does. **NDVI vs LST = −0.45** — greener is cooler, the
  core premise, clearly present. Two sensors, independent instruments, agreeing.
- Ward cross-check is decisive: greenest wards by NDVI (R/C 0.39, T 0.33 — the national-park
  wards) are the coolest by LST; greyest (C 0.13, B, L — dense island city) are the hottest.
  This is the LST ward ranking reproduced from a completely different sensor.

**Decided**
- **30 m reduction, not 20 m.** The smoke test measured ~70 s/200 cells at 20 m (~70 min
  full grid). A 200 m cell *mean* is insensitive to sampling below ~50 m for a smooth field,
  so 30 m gives the same cell mean at ~half the cost — full grid ran in 10.6 min.
- **`S2_SR_HARMONIZED`, not `S2_SR`.** The harmonised collection removes the post-2022
  processing-baseline offset. A normalised difference is invariant to a common *scale* but
  not to an *offset*, so the offset would bias NDVI across the 2019–2026 span if unremoved.
- **SCL-band cloud masking**, water class kept — same principle as the LST QA mask. Simpler
  and more directly explainable at a viva than Cloud Score+, and dry season is low-cloud.

**Broke / learned**
- **Dropped `.filterBounds()` again** in the first draft — the collection came back as
  349,333 scenes (global) instead of 542. Same lazy-evaluation trap as the LST stage: the
  reduced values are identical either way, the only symptom is the scene count. Same guard
  now protects both stages.
- **NDVI is non-monotonic with LST at the low end.** Binning LST by NDVI, the coolest bin is
  *not* the lowest-NDVI one — cells under 0.1 NDVI include inland water, wet mangrove and
  salt pans, which are cool *and* low-NDVI. So NDVI alone cannot tell "bare hot" from "wet
  cool"; NDBI, NDWI and the WorldCover water fraction are what disambiguate. Good argument
  for the multi-feature model, and a limitation worth stating rather than hiding.
- The refactor-then-verify-byte-identical pattern is worth keeping: it let me change a
  shared code path with confidence and without re-spending Earth Engine quota to prove it.

**Next**
- ESA WorldCover land-cover fractions (tree / grass / built / water) per cell — the water
  fraction is now known to be needed to disambiguate the low-NDVI cells above.
- Still no `pytest`; the byte-identical refactor check and the index invariants ran as
  scratch scripts.

---

## 2026-07-20 — Phase 1 — The target variable: per-cell LST

**Done**
- `data_pipeline/ee_session.py` — one Earth Engine init per run, with the three known
  failure modes funnelled into a message that points at `runbook.md` §6.
- `data_pipeline/sources/landsat.py` → `data/interim/lst.parquet`. 11,944 rows,
  `lst_mean` / `lst_p90` / `lst_obs_count`. 134 scenes, 102 s for the full reduction.
- `data_pipeline/run.py` — `--stage {all,boundary,grid,landsat}`, skipping stages whose
  output exists. Completes the Phase 1 scaffolding.

**Results**
- `lst_mean` 29.8 – 50.6, mean **39.7 °C**. `lst_p90` 32.3 – 55.8, mean 43.5 °C.
- **Zero cells without a value; the sparsest has 46 cloud-free observations** (mean 58.3).
  That closes the cloud-starvation open question — no cell is starved, so `lst_obs_count`
  stays as a diagnostic rather than becoming a filter.
- **The urban heat island signal is clean: the park belt is 3.15 °C cooler than the
  southern city** (37.91 vs 41.06, inland cells only).

**Decided**
- **Chunked `reduceRegions`, 500 cells per request, 24 requests.** `reduceRegions` is
  server-side, but the result still has to come down through `getInfo`, and one call over
  12k cells exceeds the payload limit. Twenty-four requests each returning a fully reduced
  table is the "export aggregates" pattern ADR-0001 asks for — not the per-cell `getInfo`
  loop it forbids. The distinction is what is computed per request, not how many requests.
- **Cells go up as explicit polygons with `geodesic=False`.** They were built as squares in
  EPSG:32643, so their edges are straight in projection; letting Earth Engine assume
  geodesic edges would bow them slightly outward.
- **`lst_p90` is a *temporal* percentile**, not a spatial one within the cell — the hot
  years, not the hot corner. Asserted `p90 ≥ median` on every cell (0 violations), which is
  what would catch the two reducers being wired up backwards.

**Broke / learned**
- **Dropped `.filterBounds()` when promoting the notebook code.** The collection became the
  *global* archive: 349,333 scenes instead of Mumbai's 134. The values were unaffected —
  Earth Engine is lazy and spatially indexed, so it only ever computed the tiles the cells
  touched, and the smoke test returned byte-identical numbers before and after the fix.
  **That is what makes it dangerous:** the sole symptom was a scene count, and nothing would
  have failed. Now guarded by `if n_scenes > 1000: raise` — a filter that silently does
  nothing is worse than one that errors, so the check asserts the filter had an effect.
- **The cold tail is water, not vegetation, and `land_fraction` predicts it monotonically:**
  33.7 °C below 0.1 land, rising through 34.5 / 35.5 / 37.1 / 37.6 to 40.1 °C for fully
  inland cells. A 6.4 °C spread. Water is deliberately unmasked (the sea genuinely is a cool
  surface), so a mostly-sea cell reports mostly sea temperature while its predictors will
  describe the land sliver. Keeping those cells with a `land_fraction` column — rather than
  filtering at grid-build time — is what turned this from an assumption into evidence. Phase
  2 now has a real distribution to pick a threshold against.
- **Ward A looks like the coolest ward until its coastal cells are excluded**, then it falls
  to 5th. The wards that are genuinely cool are T and R/C, which hold Sanjay Gandhi National
  Park. A city-wide ward ranking published without that correction would have been wrong in
  a way that looks entirely plausible — worth remembering when the hotspot ranking is built.
- **The strongest check was again a reconciliation, not an assertion.** Phase 0's notebook
  gave a city mean of 39.8 °C over the GAUL boundary at pixel level; this pipeline gives
  39.7 °C over the ward boundary at 200 m cells with an extra year of data. Different code,
  footprint and aggregation agreeing to 0.1 °C is worth more than any range check, and the
  slight compression of the extremes (29.0→29.8, 51.6→50.6) is exactly what 200 m averaging
  should do.

**Next**
- Sentinel-2 NDVI/NDBI/NDWI. The reduction machinery in `landsat.py` generalises, so the
  chunked-`reduceRegions` helper should be lifted into a shared module rather than copied.
- Still no `pytest`. The `cell_id` stability property and the `p90 ≥ median` invariant are
  both load-bearing and both currently checked by scratch scripts.

---

## 2026-07-20 — Phase 1 — The 200 m grid and a permanent cell_id

**Done**
- `data_pipeline/grid.py` → `data/interim/grid.parquet`. **11,944 cells**, columns
  `cell_id` / `grid_row` / `grid_col` / `geometry` / `centroid_lat` / `centroid_lon` /
  `land_fraction` / `ward_code`.
- Added `pyarrow` for GeoParquet.

**Decided**
- **`cell_id = grid_row × 1_000_000 + grid_col`, anchored to the EPSG:32643 origin.** The
  obvious alternative — a sequential `0..N` over whatever cells come out — is a trap. Drop
  one coastal cell and every id after it shifts by one, so a stored scenario keeps its
  number and silently points at different ground. Anchoring to the projected CRS makes an
  id a property of *where the cell is on Earth*, so re-running against a revised boundary
  adds and removes cells but renumbers nothing.
  **Verified rather than asserted:** rebuilding without ward T gives 10,891 cells, all of
  which carry their original ids, and zero ids appear that were not in the full grid.
- **Grid built in EPSG:32643, stored in EPSG:4326.** A 200 m cell defined in degrees is
  neither square nor constant in size with latitude. Centroids are likewise computed in UTM
  and converted afterwards. This is the split `conventions.md` already mandated; the grid is
  the first place it actually bites.
- **`grid_row`/`grid_col` are kept as columns, not just folded into the id.** Neighbourhood
  features (`ndvi_neigh_mean`, `built_neigh_mean`) become integer arithmetic on the row/col
  lattice instead of a spatial join over 12k polygons.
- **Coastal slivers are kept, with `land_fraction` recording how much land each holds.**
  Filtering here would bake a guess into a permanent cell set. Phase 2 can drop or
  down-weight low-`land_fraction` cells on evidence, which is reversible; deleting them now
  is not.
- **Ward by majority overlap**, from the same overlay that produces `land_fraction`, so the
  two can never disagree about which geometry they came from.

**Learned / noted**
- The strongest correctness check turned out to be a reconciliation, not an assertion: total
  cell land area **458.3 km²** against ward area **458.3 km²**, difference −0.00. If the
  overlay had double-counted, dropped a ward, or mismatched a projection, that number would
  not close. It is worth more than any single unit test here.
- Per-ward counts sanity-check against area independently: R/C is 48.03 km² and gets 1,259
  cells; C is 1.91 km² and gets 52. At 0.04 km² per cell those are the right magnitudes,
  with the excess explained by partial edge cells.
- 92.1% of cells are fully inland, 1.6% hold under a tenth of a cell of land. The
  distribution is printed on every run so a future boundary change shows up immediately as
  a shifted profile.

**Next**
- Promote the Phase 0 Landsat code into `sources/landsat.py` and reduce LST to per-cell
  `lst_mean` / `lst_p90` / `lst_obs_count`. That is the first stage that spends Earth Engine
  quota against the real grid, so `--stage` caching in `run.py` matters from here on.

---

## 2026-07-20 — Phase 1 — Ward boundaries, and the study area is 458 km² not 603

**Done**
- `data_pipeline/config.py` — `pydantic-settings`, replacing the notebook's bare `dotenv`.
  Resolves `DATA_DIR` against a repo root derived from `__file__`, so stages behave
  identically whichever directory they are launched from.
- `data_pipeline/boundary.py` — caches the DataMeet source under `data/raw/`, validates it,
  writes `data/processed/wards.geojson`. Runs as `uv run python -m data_pipeline.boundary`.
- Output: 24 wards, EPSG:4326, columns `ward_code` / `area_km2` / `geometry`, 573 KB.

**Decided**
- **The gate is the exact set of 24 ward codes, not the count.** Phase 0's bug passed a
  `count != 0` check while matching one district of two. A count check answers "did I get
  something?"; a set check answers "did I get the *right* thing?". No truncated or wrong
  dataset reproduces all 24 of A…T with the E/W and N/S splits. Verified by deleting a ward
  and confirming the failure names it: `missing=['T']`.
- **Area is reported, not tightly gated.** No two sources agree on Mumbai's area, so a
  narrow band around any one figure would reject a legitimate source. The band is
  380–700 km²: wide enough for any real Mumbai boundary, narrow enough to reject a
  different city entirely.
- **Wards must tile** — `sum(areas) == area(union)` within 0.5 km². Overlapping wards would
  let one cell belong to two wards and silently double-count every ward-level aggregate.
- **6 decimal places on write.** float64's ~15 digits produced 972 KB; RFC 7946's
  recommended 6 dp (~0.11 m) gives 573 KB, for an area difference of 167 m² across the
  entire city — 0.000036%. No vertices removed, 29 coincident points collapsed. Storing
  precision the source survey never had is not worth 400 KB in git.
- **`ward_code` only; `ward_name` deferred.** The source's `name` field holds the BMC code
  ("A", "R/C"), not a place name. Mapping R/C→Borivali from memory would be precisely the
  invented-label problem `conventions.md` forbids. It needs a citable source first.

**Broke / learned**
- **The study area is 458 km², not the 603 km² that five documents asserted.** 603 is the
  two *districts* (Mumbai City 157 + Mumbai Suburban 446), which include harbour, creek and
  tidal area that no ward polygon covers. FAO GAUL independently measures 487. All three
  describe different footprints; this project's is the ward union, 458 km².
- **Consequence: ~11–12k cells at 200 m, not the "15–20k" written into BLUEPRINT.**
  ADR-0007's *decision* is unaffected — 11.5k is still comfortable for boosted trees, and
  it strengthens rather than weakens the rejection of 300 m (~5k rows). But the supporting
  figure inside that ADR is now known to be wrong, and `conventions.md` makes ADRs
  immutable, so it stays as written. The corrected number lives in `data-dictionary.md`,
  which is the living spec. **Open question for the author:** whether "immutable" permits
  an appended dated correction note, or whether a stale supporting figure is simply what an
  ADR is — a record of what was known at decision time.
- **Checked SGNP coverage explicitly before trusting the dataset**, because a heat study
  that excluded the city's largest cool surface would be broken in a way no schema check
  catches. Kanheri Caves resolves to ward R/C; Aarey, Powai and Vihar are all inside. The
  park is in.
- The wards tile exactly — sum equals union, no interior holes — so the missing 145 km² is
  a notch in the outer boundary (coastline, creeks) rather than a hole punched in the
  middle. That is what ruled out the "SGNP is excluded" hypothesis before writing any code.

**Next**
- The 200 m grid and `cell_id`. Everything above exists so that stage has a validated
  polygon to clip to.

---

## 2026-07-20 — Phase 1 — Kickoff: planning pass

**Done**
- Phase 0 closed: exit criterion ticked, CHANGELOG entry written, `architecture.md` checked.
- ADR-0007 — 200 m analysis grid.
- `data-pipeline/` → `data_pipeline/`, now an installable package (hatchling) so
  `python -m data_pipeline.run` works as `runbook.md` §3 already documented.
- Phase 1 expanded into grouped tasks in `PROGRESS.md`: scaffolding → geometry → target →
  predictors → assemble.

**Decided**
- **Ward boundaries: DataMeet `Municipal_Spatial_Data`, `Mumbai/BMC_Wards.geojson`,
  CC BY 4.0**, already EPSG:4326. This closes the longest-standing open question in
  `data-dictionary.md` §5. A materially better licence than GAUL's restricted
  redistribution, and it comes with a trap: the same folder ships
  `bmc_electoral_wards_2017`, the 227 *electoral* wards. This project uses the **24
  administrative** wards — those are the units MCAP is written against and that budgets
  follow. Ranking electoral wards would produce a result no planner could act on.
- **200 m grid (ADR-0007).** The deciding argument is the *direction* of the resolution
  claim: Landsat thermal is 100 m native (the 30 m delivery grid is packaging, not
  information), so a 200 m cell averages ~4 measured pixels and sits deliberately coarser
  than the instrument. Nothing is ever downscaled. 100 m was rejected because one pixel per
  cell means no averaging and co-registration error propagates undiluted; 300 m because it
  blurs the ~200 m scale at which a park or a block of cool roofs actually exists.
- **Years: Mar–May 2019–2026.** Phase 0 measured 56 scenes over 2019–2025 after cloud
  filtering, so the range is known-good; 2026 is complete and free, giving an 8th year for
  `lst_trend`. Decided from evidence rather than guessed, which is the point of having run
  Phase 0 first.
- **Renamed the pipeline directory now.** `data-pipeline` with a hyphen is not a legal
  Python module name, so the `python -m data_pipeline.run` in the runbook could never have
  worked. The folder held one `.gitkeep`, so the fix cost nothing today; after three weeks
  of imports it would have been a refactor.

**Learned / noted**
- `architecture.md` §3 claimed pipeline output is "committed as data artifacts". It is the
  opposite — `data/processed/` and `models/` are gitignored build outputs, and ADR-0004's
  whole argument is that excluding them is safe *because* they are regenerable. Left
  standing, that sentence would have quietly licensed committing a 50 MB parquet in Phase 1.
  Caught only because `conventions.md` requires an architecture check at phase close, which
  is the first time that rule has earned its keep.

**Next**
- First code task: fetch and validate BMC wards → `data/processed/wards.geojson`, gated on
  24 wards and total area ≈ 603 km².
- Then the 200 m grid and `cell_id`. That builder deserves the most scrutiny of anything in
  Phase 1: `cell_id` is permanent once assigned, and every saved scenario, stored model and
  cached API response downstream is keyed on it.

---

## 2026-07-19 — Phase 0 — Python environment and the Earth Engine hello-world notebook

**Done**
- Python environment: `pyproject.toml` + `uv.lock`, pinned to 3.12 via `.python-version`.
  `uv sync` installs 151 packages — `earthengine-api` 1.7.35, `geemap` 0.38.3,
  `geopandas` 1.1.4, JupyterLab, `ruff`.
- `notebooks/00_hello_earth_engine.ipynb`, 25 cells: authenticate → GAUL Mumbai boundary →
  Landsat 8/9 C2 L2 dry-season composite → numeric sanity check → interactive map → static
  PNG → NDVI cross-check.
- `runbook.md` §1.5, §2 and §6 corrected to match the setup that actually exists.
- Earth Engine registered against the `urbanheat-mumbai` Cloud project (noncommercial,
  academic) and the notebook run end to end: 56 Landsat scenes, both Mumbai districts,
  LST composite rendered as both an interactive map and a static PNG.

**Decided**
- **Python 3.12, not the system 3.14.** `geopandas`/`pyproj`/`shapely` wheels lag the newest
  CPython, and a source build needs a GEOS/PROJ toolchain that is miserable on Windows. 3.12
  satisfies "3.11+" with full wheel coverage, and `.python-version` makes the venv
  reproducible rather than dependent on whatever `python` resolves to.
- **`pyproject.toml` + `uv.lock` instead of `requirements.txt`.** The runbook originally
  specified `requirements.txt`; a lockfile pins the full transitive graph, which is what
  ADR-0004's "must be regenerable by re-running the pipeline" contract actually needs.
- **`python-dotenv` in the notebook, not `pydantic-settings`.** `conventions.md` mandates
  pydantic-settings for *modules*, and explicitly scopes notebooks as exploration. The
  settings module lands in Phase 1, when `data-pipeline/` exists and there is more than one
  consumer to share it with. Deferred deliberately, not overlooked.
- **FAO GAUL 2015 level-2 as the Phase 0 boundary.** Already in the EE catalog, so no
  download and no shapefile handling. Greater Mumbai spans two GAUL districts (Mumbai +
  Mumbai Suburban), dissolved into one polygon. A placeholder by design — and its licence
  turns out to restrict redistribution, which is a second, independent reason Phase 1's
  swap to BMC/OSM wards is the right call (`data-dictionary.md` §1, §5).
- **Verify LST numerically before plotting.** The notebook prints min/mean/max °C before any
  map cell. A map renders a picture whether or not the scale factor was applied; only the
  numbers catch it.

**Learned / noted**
- The two Collection 2 scale factors are easy to confuse and fail differently. Thermal is
  `× 0.00341802 + 149.0` (→ Kelvin); optical is `× 0.0000275 − 0.2` (→ reflectance 0–1).
  Applying the optical factor to `ST_B10` yields ~0.15 — wrong enough to ruin the model,
  plausible enough to go unnoticed. Failure table in notebook §3.1.
- `QA_PIXEL` masking rejects four bits, not one: cloud (3), shadow (4), cirrus (2), dilated
  cloud (1). Cirrus is the dangerous one — invisible in a true-colour preview while still
  attenuating the thermal signal. Water (bit 7) is deliberately kept; the sea and the lakes
  are genuine cool surfaces, not errors.
- Band arithmetic drops image metadata in Earth Engine. `system:time_start` has to be
  carried forward with `copyProperties` or the per-year work in Phase 1 breaks silently.
- **Boundary bug — a partial match that raised no error.** GAUL spells the island city
  `Mumbai city` (lowercase "c"); the hardcoded list said `Mumbai`, so `ee.Filter.inList`
  matched only `Mumbai Suburban` and the study area silently lost ~78 km² of the densest
  part of the city. Caught by the printed area (409 km², against ~603 expected), not by
  any exception. **The guard was the real defect:** it tested `n_matched == 0`, which only
  catches total failure. A partial match is the dangerous case — it yields a valid geometry
  that is quietly incomplete, and every downstream statistic inherits the omission. Now
  asserts `n_matched == len(MUMBAI_DISTRICTS)` and prints the matched names on failure.
  General lesson for Phase 1: **validate the count and the magnitude, never just
  non-emptiness.**
- **GAUL under-measures Mumbai by ~19%** — 487 km² against BMC's published 603 km². Not a
  bug; GAUL is a generalised global product that smooths coastlines, and Mumbai is built
  substantially on reclaimed land. Harmless for a Phase 0 picture, but it is a third
  independent reason (alongside no ward geometry and the redistribution licence) that
  Phase 1 must use real BMC polygons. The notebook now prints the gap as a percentage
  rather than a pass/fail verdict.
- **Authentication took three separate failures to clear**, none of them code:
  1. The paste-code flow produced a code that was never redeemed — it has to go into the
     prompt of the *same* run, since the PKCE verifier is per-session.
  2. `earthengine authenticate` with the default auth mode returned "This app is blocked"
     — the college Workspace domain blocks that OAuth client. Different `--auth_mode`
     values use *different* clients, so notebook mode worked where the default did not.
  3. `ee.Initialize` then returned 403 `SERVICE_DISABLED`: the Cloud project existed but
     had never been registered with Earth Engine. Creating a project and registering it
     are separate steps. Registration enables `earthengine.googleapis.com` as a side
     effect. All three are now rows in `runbook.md` §6.
- **First real numbers**, Mar–May 2019–2025, 56 scenes after cloud filtering, clipped to
  the GAUL land boundary: min 29.0 °C, mean 39.8 °C, max 51.6 °C.
- **The predicted 30–36 °C mean was miscalibrated, and the code was right.** The prediction
  assumed sea-surface pixels were in the region; an administrative *land* boundary excludes
  them, so the minimum is the coolest land (park canopy) rather than water, and everything
  shifts up. Worth remembering that a "plausible range" is a property of the clip footprint
  as much as of the retrieval — comparing against a published figure that used a different
  footprint would be an error. §4's table now carries observed values, not guesses.

**Next**
- Visual confirmation of the LST/NDVI inverse relationship — Sanjay Gandhi National Park
  and Aarey cool, Dharavi and the eastern industrial belt hot. The one check that cannot
  be automated, and the last thing standing between here and the Phase 0 ✅.
- Phase 1 kickoff: BMC ward boundaries → `data/processed/wards.geojson`, then the ~200 m
  grid with stable `cell_id`.
- **Carry into Phase 1:** assert counts *and* magnitudes on every join and filter, never
  just non-emptiness. The boundary bug above is the cheap version of a defect that would
  be far more expensive to find inside a 20k-row feature table, where no printed area
  number would be sitting there to contradict it.

---

## 2026-07-17 — Phase 0 — Project scaffolding and documentation

**Done**
- Git repo connected to `github.com/DevGurav/urbanheat-mumbai`; local identity set.
- `.gitignore` extended (secrets, data artifacts, models, vector store); `.env.example`
  written with every variable the project will need through Phase 6.
- Root: `README.md`, `PROGRESS.md` (task board), `LICENSE` (MIT + data attributions).
- Full `docs/` tree: BLUEPRINT, conventions (hard rules + Definition of Done), architecture
  (Mermaid), data-dictionary, ml-methodology, agents, api-reference, runbook, references,
  CHANGELOG, this devlog.
- Six ADRs covering every load-bearing choice made so far.

**Decided**
- **Scope of the roadmap** — 8 phases over ~24 weeks, each ending in something runnable.
  No big-bang integration at the end.
- **ADR-0001 Earth Engine** over local raster processing. Deciding factor: where the compute
  happens. Terabytes of Landsat on a laptop with 10 GB free was never viable.
- **ADR-0002 Gemini Flash free tier**, Groq as fallback. Local Ollama rejected — no GPU
  means CPU inference too slow for an agent graph, and small-model tool calling is unreliable.
- **ADR-0003 Redis and WebSockets cut.** They solve multi-instance and push problems this
  system does not have; Render's free tier (one sleeping container, no worker) would make
  them inert. Staying in the report as production considerations with scaling triggers.
- **ADR-0004 Files first, Supabase from Phase 6.** The feature table is a regenerable build
  artifact, not database state. Supabase's idle-pause would also have been an outage risk
  during the ML phases.
- **ADR-0005 LST as target** — the most consequential decision. Air temperature has <10
  stations across the study area; a 20k-cell model trained on that would be interpolation
  wearing an ML costume. LST gives a measured label per cell. Cost: outputs are *surface*
  temperature, mid-morning, and must be labelled as such everywhere.
- **ADR-0006 Gradient-boosted trees.** At 20k×20 tabular, this is the right tool, not a
  compromise — and SHAP's exact tree explainer is what the whole recommendation layer
  stands on. Deep learning would be the wrong answer here, independent of hardware.

**Learned / noted**
- Free-tier terms verified as of today: Gemini free tier is Flash-only (~10 req/min,
  ~1,500/day) since Pro moved behind billing in May 2026; Render free sleeps at 15 min idle
  and dropped to 5 GB/mo bandwidth in April 2026; Earth Engine noncommercial runs on a
  monthly compute-unit quota. All three shape design, not just budget — recorded in the ADRs.
- Two risks written down early because they are the classic ways this kind of project
  produces a worthless-but-impressive result: spatial autocorrelation inflating R² under a
  random split, and the scenario engine extrapolating past the training envelope. Both have
  mitigations specified before any code exists (`ml-methodology.md` §2, §6).

**Next**
- Folder scaffold: `data-pipeline/`, `backend/`, `frontend/`, `notebooks/`, `data/`, `models/`.
- **Earth Engine noncommercial registration** — the only approval wait; blocks Phase 0's ✅.
- Gemini key → `.env`. Python 3.11 env + `earthengine-api`, `geemap`, `geopandas`.
- Then the Phase 0 exit criterion: a notebook rendering a Landsat LST image over Mumbai.

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

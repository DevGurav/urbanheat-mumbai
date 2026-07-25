# Data Dictionary

Every dataset consumed and every column produced. **Maintenance rule:** a new dataset or
feature column gets its row here the same day it is added ([conventions.md](conventions.md)).

**Status:** planned specification — Phase 1 fills in actual date ranges, cell counts and
observed value ranges as the pipeline is built. Nothing below is claimed as measured yet.

**Study area** Greater Mumbai — the union of BMC's 24 administrative wards, **458 km²**
as measured from the DataMeet polygons in EPSG:32643.

> The widely quoted **603 km²** is the two *districts* (Mumbai City 157 + Mumbai Suburban
> 446), which include harbour, creek and tidal area that no ward polygon covers. FAO GAUL
> independently measures 487 km². All three describe different footprints; this project's
> study area is the ward union, so **458 km² is the figure every per-area number uses.**

**Grid** 200 m cells (ADR-0007), **≈11–12k expected** — confirmed when the grid stage lands
**Season** Dry season, March–May (monsoon cloud makes Jun–Sep unusable — ADR-0005)
**CRS** EPSG:4326 for storage and API; EPSG:32643 (UTM 43N) for area/distance maths

---

## 1. Source datasets

| Dataset | Provider | Native res. | Temporal | Used for | Licence |
|---|---|---|---|---|---|
| **Landsat 8/9 C2 L2** (`LANDSAT/LC08/C02/T1_L2`, `LC09/...`) | USGS/NASA via GEE | 30 m optical, 100 m thermal (resampled 30 m) | 2013– , 16-day revisit | **LST target**, albedo | Public domain |
| **Sentinel-2 SR Harmonized** (`COPERNICUS/S2_SR_HARMONIZED`) | ESA via GEE | 10–20 m | 2017– , 5-day revisit | NDVI, NDBI, NDWI | CC BY-SA 3.0 IGO |
| **ESA WorldCover v200** (`ESA/WorldCover/v200`) | ESA via GEE | 10 m | 2021 | Land-cover fractions | CC BY 4.0 |
| **WorldPop** (`WorldPop/GP/100m/pop`) | WorldPop via GEE | 100 m | annual | Population density | CC BY 4.0 |
| **SRTM v3** (`USGS/SRTMGL1_003`) | NASA via GEE | 30 m | 2000 static | Elevation | Public domain |
| **OpenStreetMap** | OSM contributors via OSMnx/Overpass | vector | live | Building/road density, parks | ODbL |
| **Open-Meteo** (archive + forecast) | Open-Meteo | ~11 km (ERA5) | 1940– | Weather covariates, alerts | CC BY 4.0, keyless |
| **BMC ward boundaries** (`Mumbai/BMC_Wards.geojson`) | [DataMeet](https://github.com/datameet/Municipal_Spatial_Data) | vector, EPSG:4326 | static | Aggregation units — **24 administrative wards** | CC BY 4.0 |
| **FAO GAUL 2015 level-2** (`FAO/GAUL/2015/level2`) | FAO via GEE | vector | 2015 static | **Phase 0 only** — placeholder city boundary | Redistribution restricted — see §5 |

**FAO GAUL is a Phase 0 scaffold, not a project dataset.** It supplies a serviceable Greater
Mumbai outline (the union of the *Mumbai* and *Mumbai Suburban* districts) with no download,
which is all the hello-world notebook needs. It is replaced in Phase 1 by BMC ward polygons
for two independent reasons: GAUL has no ward-level geometry, and its licence restricts
redistribution, which would be a problem for a publicly deployed dashboard. No GAUL geometry
is persisted to disk or served by the API.

**Attribution obligations.** CC BY sources (Sentinel-2, WorldCover, WorldPop, Open-Meteo,
DataMeet) require credit; OSM requires "© OpenStreetMap contributors" on any map display.
DataMeet's wording: *"Municipal data by DataMeet India community (CC BY 4.0)"*. These appear
in the dashboard footer and the report — tracked as a Phase 5 task.

⚠️ The DataMeet Mumbai folder also ships `bmc_electoral_wards_2017` — the **227 electoral**
wards. This project uses the **24 administrative** wards, which are the units MCAP is
written against and that budgets follow. Aggregating to electoral wards would produce
rankings no planner could act on.

---

## 2. Target variable

| Column | Type | Unit | Observed | Derivation |
|---|---|---|---|---|
| `lst_mean` | float | °C | 29.8 – 50.6, mean 39.7 | Landsat C2 L2 `ST_B10` × 0.00341802 + 149.0 − 273.15; QA_PIXEL cloud/shadow mask; **temporal median** over Mar–May 2019–2026, spatially averaged to the cell at 100 m |
| `lst_p90` | float | °C | 32.3 – 55.8, mean 43.5 | **Temporal** 90th percentile of the same stack — the hot extreme the median hides. Not a spatial percentile within the cell |
| `lst_obs_count` | float | count | 46 – 66, mean 58.3 | Cloud-free observations contributing to the cell. Flags cells whose composite rests on too little data to trust |
| `lst_trend` | float | °C/yr | *not yet built* | Slope of per-year Mar–May medians (needs ≥5 years) |

⚠️ **`lst_mean` is a spatial mean of a temporal median**, not a mean of means. The name is
retained for continuity with the rest of the schema; the derivation column is authoritative.

**Measured, Phase 1** — 11,944 cells, 134 scenes, Mar–May 2019–2026. **Zero cells lack an
LST value** and the sparsest cell still has 46 cloud-free observations, which closes the
cloud-starvation question in §5: no cell is starved, and `lst_obs_count` is retained as a
diagnostic rather than a filter.

**Independent validation.** Phase 0's notebook measured a city-wide mean of 39.8 °C over the
*GAUL* boundary at pixel level. This pipeline measures 39.7 °C over the *ward* boundary,
aggregated to 200 m cells, with an extra year of imagery — a different code path, footprint
and aggregation agreeing to 0.1 °C. The extremes compress slightly (min 29.0 → 29.8, max
51.6 → 50.6), which is what spatial averaging to 200 m should do.

⚠️ **Water contamination scales with `land_fraction`, and it is large.** Water is
deliberately *not* masked — the sea and the lakes are genuine cool surfaces — so a cell that
is mostly sea reports mostly sea temperature:

| `land_fraction` | cells | mean `lst_mean` |
|---|---|---|
| < 0.10 | 189 | 33.7 °C |
| 0.10 – 0.25 | 126 | 34.5 °C |
| 0.25 – 0.50 | 172 | 35.5 °C |
| 0.50 – 0.90 | 295 | 37.1 °C |
| 0.90 – 0.999 | 163 | 37.6 °C |
| = 1.00 | 10,999 | 40.1 °C |

The gradient is monotonic and spans 6.4 °C. For a model predicting *urban* heat from *urban*
predictors, low-`land_fraction` cells carry a target describing water while their features
describe land. **Phase 2 must choose and justify a threshold** — this is the empirical
evidence the decision was deferred for (ADR-0007 consequences).

**Physical check passed.** Restricted to fully-inland cells, the coolest wards are T (38.01)
and R/C (38.03) — the two holding Sanjay Gandhi National Park — and the hottest are B
(44.16), L (43.18) and C (42.84), all dense built-up. The park belt runs **3.15 °C cooler**
than the southern city. Ward A appears coolest city-wide only until its coastal cells are
excluded, at which point it falls to 5th: its apparent coolness is water, not shade.

**Critical caveat.** This is **surface** temperature at ~10:30 local overpass, not air
temperature and not the 3 pm peak. Every label in UI, API and report says *surface*
(ADR-0005).

**First observation (Phase 0, `notebooks/00_hello_earth_engine.ipynb`).** Mar–May 2019–2025,
56 Landsat 8/9 scenes after cloud filtering, clipped to the GAUL land boundary: **min 29.0,
mean 39.8, max 51.6 °C** (per pixel at 100 m). Note this is a *land-only* footprint — an
administrative boundary excludes the sea, so the minimum is the coolest land surface rather
than water. The per-cell `lst_mean` range above will be narrower than these per-pixel
extremes once aggregation to ~200 m cells averages them out. Phase 1 confirms.

---

## 3. Feature columns → `data/processed/features.parquet`

### Identity & geometry

| Column | Type | Unit | Notes |
|---|---|---|---|
| `cell_id` | int64 | — | **Stable primary key. Never reindex** ([conventions.md](conventions.md)). `grid_row × 1_000_000 + grid_col` |
| `grid_row`, `grid_col` | int64 | — | Cell index on the EPSG:32643 grid. Adjacency is arithmetic, so neighbourhood features need no spatial join |
| `geometry` | polygon | EPSG:4326 | 200 m cell, built in EPSG:32643 (ADR-0007) |
| `centroid_lat`, `centroid_lon` | float | ° | Computed in UTM then converted — a degree is not a constant distance |
| `land_fraction` | float | 0…1 | Share of the cell inside the ward union. Coastal slivers are kept, not filtered |
| `ward_code` | str | — | BMC ward by **majority overlap**; aggregation unit |
| `ward_name` | str | — | *Not yet populated.* The source supplies only the code ("R/C"); official ward names need a citable source before use |

**`cell_id` is derived from position, never from row order.** A sequential `0..N` id shifts
every downstream id the moment one coastal cell is added or dropped, silently repointing
saved scenarios at the wrong ground. Anchoring to the projected CRS means an id depends only
on where the cell is on Earth. Verified: rebuilding without ward T drops the grid from
11,944 to 10,891 cells and renumbers **none** of the survivors.

**Grid as built (Phase 1):** 11,944 cells, covering 458.3 km² of land — reconciling with the
ward area to within 0.01 km². 92.1% are fully inland (`land_fraction` = 1.0); 1.6% hold less
than a tenth of a cell's worth of land. Largest ward R/C at 1,259 cells, smallest C at 52.

### Vegetation & water

| Column | Unit | Observed | Derivation |
|---|---|---|---|
| `ndvi_mean` | index | −0.22 … +0.75, mean +0.29 | `(NIR−Red)/(NIR+Red)` = S2 `(B8−B4)/(B8+B4)`, Mar–May median. Primary cooling driver |
| `ndvi_p10` | index | −0.72 … +0.62, mean +0.19 | Temporal 10th percentile — worst-case (dry-year) greenness |
| `ndwi_mean` | index | −0.67 … +0.35, mean −0.32 | `(B3−B8)/(B3+B8)`. Over land this tracks canopy water, so it runs inverse to NDVI, not "open water" |
| `tree_fraction` | fraction | 0…1, mean 0.34 | WorldCover class 10 share of cell |
| `grass_fraction` | fraction | 0…1, mean 0.03 | WorldCover class 30 share |

Sentinel-2 indices come from `COPERNICUS/S2_SR_HARMONIZED`, SCL cloud/shadow-masked,
Mar–May 2019–2026 (542 scenes), reduced to the cell at 30 m. `S2_SR_HARMONIZED` is required
specifically: it removes the post-2022 processing-baseline offset that would otherwise skew
a normalised-difference ratio.

### Built environment

| Column | Unit | Observed | Derivation |
|---|---|---|---|
| `ndbi_mean` | index | −0.44 … +0.40, mean −0.02 | `(SWIR−NIR)/(SWIR+NIR)` = S2 `(B11−B8)/(B11+B8)`. Primary warming driver |
| `built_fraction` | fraction | 0…1, mean 0.39 | WorldCover class 50 share |
| `albedo` | fraction | 0…1 | Liang (2001) narrowband→broadband from Landsat SR. **Cool-roof lever** |
| `building_density` | m²/m² | 0…~2 | OSM building footprint area ÷ cell area |
| `building_count` | count | — | OSM buildings per cell |
| `road_density` | m/m² | — | OSM road length ÷ cell area |
| `impervious_fraction` | fraction | 0…1 | built + roads, capped at 1 |

**ESA WorldCover — full class set (Phase 1).** WorldCover v200, a single static 10 m mosaic
(2021), reduced to per-class pixel *fractions* per cell via a frequency histogram. The sea is
class 80, not masked, so every cell has ~425 classified pixels and the fractions sum to 1
(share of the whole cell). Inspection showed the original tree/grass/built plan was too
narrow, so all occurring classes are kept:

| Column | Unit | Observed mean | WorldCover class |
|---|---|---|---|
| `tree_fraction` | fraction | 0.34 | 10 Tree cover |
| `shrub_fraction` | fraction | ~0 | 20 Shrubland |
| `grass_fraction` | fraction | 0.03 | 30 Grassland |
| `crop_fraction` | fraction | 0.04 | 40 Cropland |
| `built_fraction` | fraction | 0.39 | 50 Built-up |
| `bare_fraction` | fraction | 0.02 | 60 Bare / sparse |
| `water_fraction` | fraction | 0.08 | 80 Permanent water |
| `wetland_fraction` | fraction | ~0 | 90 Herbaceous wetland |
| `mangrove_fraction` | fraction | 0.10 | 95 Mangroves |
| `wc_pixels` | count | ~425 | Classified pixels in the cell (QA / denominator) |

City composition: **built 39%, tree 34%, mangrove 10%, water 8%, crop 4%.** Mangrove at 10%
is a major Mumbai cover with a distinct (cool) thermal signature — the reason it is broken out
from `tree_fraction` rather than lumped in. Snow (70) and moss (100) never occur and are
dropped.

⚠️ **`crop_fraction` is not farmland here.** Crop-dominated cells are the *hottest* land in the
city (mean 42.6 °C, above built's 41.9; 12 of the 20 hottest cells), because WorldCover labels
Mumbai's dry-season bare ground, fallow land and the Deonar dump as cropland. Read it as
"dry bare ground", not agriculture.

**Validated against LST and the Sentinel-2 indices.** Signs are all as physics requires, and
the two independent datasets corroborate each other:

| Relationship | corr | Reading |
|---|---|---|
| `built_fraction` vs `lst_mean` | +0.59 | Built-up is hot |
| `water_fraction` vs `lst_mean` | −0.46 | Water is cool |
| `mangrove_fraction` vs `lst_mean` | −0.46 | Mangrove is cool — a real distinct cooler |
| `built_fraction` vs `ndbi_mean` | +0.46 | Agrees with the S2 built-up index |
| `tree_fraction` vs `ndvi_mean` | +0.53 | Agrees with the S2 vegetation index |
| `water_fraction` vs `ndwi_mean` | +0.57 | Agrees with the S2 water index |

**`water_fraction` resolves the low-NDVI ambiguity.** The 285 land cells that were low-NDVI
*and* cool — unexplainable from NDVI alone (§ Sentinel-2) — have mean `water_fraction` **0.96**
against 0.03 for every other cell. They are inland water and creeks. This is the disambiguation
the column was added for, confirmed.

**Sentinel-2 indices validated against LST (Phase 1).** The whole premise is that vegetation
cools and built-up warms, so the acceptance test is the sign and strength of the correlation
with `lst_mean` (land cells, `land_fraction ≥ 0.9`):

| Predictor | corr with `lst_mean` | Reading |
|---|---|---|
| `ndbi_mean` | **+0.74** | Built-up index is the *strongest* single driver of surface heat |
| `ndvi_mean` | **−0.45** | Greener is cooler — the core premise, clearly present |
| `ndwi_mean` | +0.24 | Over land, higher NDWI ≈ less canopy ≈ warmer |
| `ndvi_p10` | −0.25 | Worst-case greenness, weaker than the median |

Two independent sensors agree at ward level: the greenest wards by NDVI — R/C (0.39) and
T (0.33), which hold Sanjay Gandhi National Park — are exactly the coolest by LST, and the
greyest — C (0.13), B, L, all dense island-city — are the hottest.

⚠️ **NDVI is non-monotonic with LST at the extreme low end.** Cells with NDVI < 0.1 are *not*
the hottest — inland water, wet mangrove and salt-pan cells have both low NDVI and low
temperature. NDVI alone therefore cannot separate "bare hot" from "wet cool"; the model needs
`ndbi_mean`, `ndwi_mean` and the WorldCover water fraction to disambiguate. A notable finding
for the report: in a dense tropical city the built-up signal outweighs the vegetation signal.

### Terrain & context

| Column | Unit | Notes |
|---|---|---|
| `elevation_mean` | m | SRTM |
| `slope_mean` | ° | Derived from SRTM |
| `dist_coast` | m | Distance to coastline — dominant in Mumbai; sea breeze |
| `dist_park` | m | Distance to nearest OSM park/green polygon |
| `dist_water` | m | Distance to nearest water body |
| `ndvi_neigh_mean` | index | Mean NDVI of adjacent cells — explicit spatial context (ADR-0006) |
| `built_neigh_mean` | fraction | Mean built fraction of adjacent cells |

### Human exposure

| Column | Unit | Observed | Notes |
|---|---|---|---|
| `population` | persons | 0 … 2,641, total 11.7 M | WorldPop `GP/100m/pop`, year **2020** (latest available), person count **summed** to the cell at native 100 m |
| `pop_density` | persons/km² | median 26,240, max 66,029 | `population ÷ 0.04 km²` (full 200 m cell). Coastal cells with little land under-state true density; noted, minor since they hold few people |

**WorldPop validated (Phase 1).** The total over the grid is **11.7 M**, against BMC's ~12.4 M
census — the strongest possible check that the units are person-counts (sum, not mean), the
year is right and the mosaic is not double-counting. People land where expected:
`pop_density` correlates **+0.74** with `built_fraction` and **−0.31 / −0.33** with
tree / water. The densest cells resolve to Dharavi (ward G/N) and Parel (F/S) at ~65,000/km²,
Mumbai's known dense cores.

**The HVI seed.** `pop_density` correlates **+0.56** with `lst_mean` — population and surface
heat co-locate, which is exactly what makes a Heat Vulnerability Index meaningful: the people
are where the heat is. 225 cells sit in the top decile of *both* density and LST, concentrated
in Kurla (L, K/E), Ghatkopar (N), Parel (F/S) and Dharavi (G/N) — the wards a heat action plan
would prioritise.

### Weather covariates

| Column | Unit | Notes |
|---|---|---|
| `air_temp_mean` | °C | Open-Meteo Mar–May mean. Coarse (~11 km) — city-scale context, not a within-city driver |
| `humidity_mean` | % | As above |
| `wind_speed_mean` | m/s | As above |

⚠️ Weather covariates are near-constant across a 458 km² city at 11 km resolution. They
add little within-city signal and risk being noise. Phase 2 decides empirically whether
they stay — record the outcome in `ml-methodology.md`.

### Derived indices

| Column | Unit | Range | Derivation |
|---|---|---|---|
| `hvi` | index | 0…1 | **Heat Vulnerability Index** — normalised weighted blend of heat exposure (`lst_mean`), population (`pop_density`) and lack of green (`1 − ndvi_mean`). Weights + justification in `ml-methodology.md`. A **relative prioritisation tool, not a health-risk score** (ADR-0005) |
| `hotspot_rank` | int | — | City-wide rank by `hvi` |

---

## 4. Leakage watch

Features that could leak the target and must not be added without thought:

- Anything derived from the thermal band itself (only `albedo` uses Landsat, from optical
  bands — verify).
- Any "temperature" field from a source that itself ingested satellite LST.
- Ward-level aggregates of `lst_mean` as a feature — would leak the target into itself.

`ndvi_neigh_mean` and `built_neigh_mean` are neighbourhood aggregates of **predictors**,
not the target, so they are safe — but they *strengthen* spatial autocorrelation, which is
exactly why spatial block CV is mandatory (ADR-0006).

---

## 5. Open questions for Phase 1

**Settled at the Phase 1 kickoff, 2026-07-20**

- [x] **Ward provenance and licence** — DataMeet `Municipal_Spatial_Data`,
      `Mumbai/BMC_Wards.geojson`, CC BY 4.0, already EPSG:4326. Use the 24 *administrative*
      wards, not the 227 electoral ones.
- [x] **Grid resolution — 200 m** (ADR-0007). It survives the 100 m native thermal because
      it sits *coarser* than native: ~4 measured pixels average into each cell, so nothing
      claims detail the instrument did not deliver. 300 m was rejected for blurring the
      ~200 m scale at which interventions actually happen.
- [x] **Landsat years — Mar–May 2019–2026.** Phase 0 measured 56 scenes over 2019–2025
      after cloud filtering; 2026 is complete and free, giving an 8th year for `lst_trend`.
- [x] **FAO GAUL redistribution terms** — retired rather than answered. No GAUL geometry
      outlives Phase 0, so the question never becomes live.

**Still open**

- [x] **Cloud-free observation count — resolved, no cell is starved.** Minimum 46
      observations, mean 58.3, and zero cells without an LST value. `lst_obs_count` stays
      in the table as a diagnostic, but no cell needs excluding on these grounds.
- [ ] **`land_fraction` threshold for the model** — new, and now evidenced rather than
      hypothetical. Cells below ~0.5 report substantially water temperature (see §2). Phase 2
      must pick a cutoff or a weighting and justify it
- [ ] Do Open-Meteo covariates survive Phase 2 feature selection?
- [x] **WorldPop year — resolved: 2020**, the latest the collection offers (it ends at 2020),
      one year inside the 2019–2026 LST window. Total reconciles to 11.7 M vs BMC's ~12.4 M.
- [ ] Reduction method per source into a 200 m cell — area-weighted mean, majority class or
      sum. Differs by source and must be recorded here as each one lands (ADR-0007)

---

## 6. Artifacts

| Path | Contents | In git? |
|---|---|---|
| `data/raw/` | Earth Engine exports, OSM dumps | No — regenerate via `data-pipeline/` |
| `data/interim/` | Per-source intermediate tables | No |
| `data/processed/features.parquet` | **The feature table** — one row per cell | No (regenerable) |
| `data/processed/wards.geojson` | Ward polygons | Yes if small |
| `data/knowledge_base/` | RAG source PDFs (Phase 4) | No — licence-bound, list sources in `references.md` |
| `models/` | Trained model + SHAP artifacts | No |

Everything large is gitignored and **must** be reproducible by re-running the pipeline.
That is the contract that makes it safe to exclude (ADR-0004).

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

| Column | Type | Unit | Range (expected) | Derivation |
|---|---|---|---|---|
| `lst_mean` | float | °C | ~28–48 | Landsat C2 L2 `ST_B10` × 0.00341802 + 149.0 − 273.15; QA_PIXEL cloud/shadow mask; median composite over Mar–May across years |
| `lst_p90` | float | °C | — | 90th percentile of the same stack — captures extremes the median hides |
| `lst_trend` | float | °C/yr | — | Slope of per-year Mar–May medians (needs ≥5 years) |

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

| Column | Unit | Range | Derivation |
|---|---|---|---|
| `ndvi_mean` | index | −1…1 | `(NIR−Red)/(NIR+Red)` = S2 `(B8−B4)/(B8+B4)`, Mar–May median. Primary cooling driver |
| `ndvi_p10` | index | −1…1 | Worst-case greenness |
| `ndwi_mean` | index | −1…1 | `(B3−B8)/(B3+B8)` — water presence |
| `tree_fraction` | fraction | 0…1 | WorldCover class 10 share of cell |
| `grass_fraction` | fraction | 0…1 | WorldCover class 30 share |

### Built environment

| Column | Unit | Range | Derivation |
|---|---|---|---|
| `ndbi_mean` | index | −1…1 | `(SWIR−NIR)/(SWIR+NIR)` = S2 `(B11−B8)/(B11+B8)`. Primary warming driver |
| `built_fraction` | fraction | 0…1 | WorldCover class 50 share |
| `albedo` | fraction | 0…1 | Liang (2001) narrowband→broadband from Landsat SR. **Cool-roof lever** |
| `building_density` | m²/m² | 0…~2 | OSM building footprint area ÷ cell area |
| `building_count` | count | — | OSM buildings per cell |
| `road_density` | m/m² | — | OSM road length ÷ cell area |
| `impervious_fraction` | fraction | 0…1 | built + roads, capped at 1 |

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

| Column | Unit | Notes |
|---|---|---|
| `population` | persons | WorldPop, summed to cell |
| `pop_density` | persons/km² | Normalised |

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

- [ ] Cloud-free observation count per cell after masking — if some cells are starved, the
      composite is unreliable there and must be flagged (`lst_obs_count`)
- [ ] Do Open-Meteo covariates survive Phase 2 feature selection?
- [ ] WorldPop year alignment against Landsat composite years
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

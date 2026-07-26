# References

Papers, datasets and documents consulted. Grows as the project does — anything consulted
gets logged here the day it is used ([conventions.md](conventions.md)), so the bibliography assembles
itself.

**Status:** Phase 0. Method and dataset citations are known from the design; the UHI
literature list is populated during Phases 1–2 as sources are actually read. **Nothing is
listed as "used" until it has been read** — a bibliography of unread papers is detectable
and embarrassing at a viva.

---

## 1. Datasets

Cited in `data-dictionary.md` §1 with licences and attribution obligations.

- **Landsat 8/9 Collection 2 Level-2 Science Products** — USGS EROS. Surface temperature
  and reflectance. Public domain. <https://www.usgs.gov/landsat-missions>
- **Sentinel-2 MSI Level-2A** — ESA Copernicus. CC BY-SA 3.0 IGO.
  <https://sentinels.copernicus.eu>
- **ESA WorldCover v200 (2021)** — 10 m global land cover. CC BY 4.0.
  <https://esa-worldcover.org>
- **WorldPop** — gridded population, 100 m. CC BY 4.0. <https://www.worldpop.org>
- **SRTM v3 (SRTMGL1)** — NASA/USGS, 30 m elevation. Public domain.
- **OpenStreetMap** — © OpenStreetMap contributors, ODbL. <https://www.openstreetmap.org>
- **FAO GAUL 2015** — Global Administrative Unit Layers, FAO. Used **only** as the Phase 0
  boundary placeholder; redistribution restricted, superseded by BMC wards in Phase 1
  (`data-dictionary.md` §1). <https://data.apps.fao.org/map/catalog/>
- **Open-Meteo** — ERA5-based historical + forecast API. CC BY 4.0.
  <https://open-meteo.com>
- **Google Earth Engine** — Gorelick, N. et al. (2017). *Google Earth Engine:
  Planetary-scale geospatial analysis for everyone.* Remote Sensing of Environment, 202,
  18–27.

## 2. Methods

- **SHAP** — Lundberg, S. M. & Lee, S.-I. (2017). *A Unified Approach to Interpreting Model
  Predictions.* NeurIPS 30.
- **TreeSHAP** — Lundberg, S. M. et al. (2020). *From local explanations to global
  understanding with explainable AI for trees.* Nature Machine Intelligence, 2(1), 56–67.
  — the exact tree explainer ADR-0006 depends on.
- **XGBoost** — Chen, T. & Guestrin, C. (2016). *XGBoost: A Scalable Tree Boosting System.*
  KDD '16.
- **LightGBM** — Ke, G. et al. (2017). *LightGBM: A Highly Efficient Gradient Boosting
  Decision Tree.* NeurIPS 30.
- **Spatial cross-validation** — Roberts, D. R. et al. (2017). *Cross-validation strategies
  for data with temporal, spatial, hierarchical, or phylogenetic structure.* Ecography,
  40(8), 913–929. — the argument behind `ml-methodology.md` §2.
- **Albedo from Landsat** — Liang, S. (2001). *Narrowband to broadband conversions of land
  surface albedo: I Algorithms.* Remote Sensing of Environment, 76(2), 213–238.

## 3. Urban heat island literature *[Phases 1–2 — to read]*

Needed for: LST retrieval practice, the HVI weighting argument, and — most importantly —
the intervention coefficients in `interventions.yaml`, which must be cited rather than
invented (`agents.md` §5).

**Read — scenario-engine coefficients (Phase 2)**
- [x] **Cool / reflective roofs** — Li, D., Bou-Zeid, E. & Oppenheimer, M. (2014). *The
  effectiveness of cool and green roofs as urban heat island mitigation strategies.*
  Environmental Research Letters, 9(5), 055002. **Cool roof albedo 0.7 vs conventional 0.3;
  ~1.0 °C surface-UHI reduction at 30 % roof coverage, ~1.7 °C at 50 %.** → the cool-roof ΔLST
  coefficient (used *directly*, bypassing the model's confounded albedo term — ADR-0008).
- [x] **Reflective surfaces review** — Santamouris, M. (2014). *Cooling the cities — A review
  of reflective and green roof mitigation technologies…* Solar Energy, 103, 682–703. Albedo
  0.15→0.5 lowers peak 2 m air temperature 0.25–0.5 K; surface reductions larger. Corroborates
  the cool-roof magnitude and its order.
- [x] **NDVI cooling, Indian metros** — Grover, A. & Singh, R. B. (2015). *Analysis of urban
  heat island (UHI) in relation to NDVI: a comparative study of Delhi and Mumbai.* Environments,
  2(2), 125–138. **~1.39 °C LST decrease per unit NDVI increase** — corroborates the model's
  (SHAP-validated) NDVI cooling that the greening scenario relies on.

**Still to find / read**
- [ ] Foundational SUHI definition and LST-based measurement
- [ ] Green roof cooling effect · Water body ("blue space") cooling — for those levers
- [ ] Heat Vulnerability Index construction and weighting — for `ml-methodology.md` §5
- [ ] Landsat C2 L2 surface-temperature validation — accuracy expectations

**Standing note.** Every intervention coefficient shipped in the scenario engine needs a
citation here. A cost or ΔLST figure without a source is a fabrication, and the report and
the API both claim these are literature-derived (`api-reference.md`, `ml-methodology.md` §6).

## 4. Policy & knowledge-base documents *[Phase 4]*

RAG corpus for the Copilot (`agents.md` §4). All public. Files → `data/knowledge_base/`
(gitignored — listed here instead).

**Phase 4 kickoff MVP (ADR-0009)** — the 3 most Mumbai/India-specific and load-bearing:
- [ ] **Mumbai Climate Action Plan (MCAP)** — BMC. Primary local policy source
- [ ] **NDMA heat-wave guidelines / National Action Plan** — <https://ndma.gov.in>
- [ ] **IMD heat-wave criteria** — the thresholds the monitoring agent implements in code
      (`agents.md` §7). **Cite the exact definition used**

**Later candidates** — not built this phase; add if a demo or report need surfaces material
only they contain (ADR-0009):
- [ ] **WHO heat and health** fact sheets
- [ ] **IPCC AR6** — urban areas chapter, relevant excerpts
- [ ] City-level Heat Action Plans from Indian cities (Ahmedabad's is the well-known
      precedent) — useful comparison for the recommendation layer

## 5. Technical documentation

- Earth Engine Python API — <https://developers.google.com/earth-engine>
- Landsat C2 L2 Data Format Control Book — scale factors for `ST_B10`
  (the `× 0.00341802 + 149.0` in `data-dictionary.md` §2) and the `QA_PIXEL` bit
  definitions used for cloud masking (`notebooks/00_hello_earth_engine.ipynb` §3.1–3.2)
- FastAPI — <https://fastapi.tiangolo.com>
- LangGraph — <https://langchain-ai.github.io/langgraph/>
- Gemini API rate limits — <https://ai.google.dev/gemini-api/docs/rate-limits> (ADR-0002)
- Earth Engine noncommercial tiers —
  <https://developers.google.com/earth-engine/guides/noncommercial_tiers> (ADR-0001)
- Render free tier — <https://render.com/docs/free> (ADR-0003)
- OSMnx — Boeing, G. (2017). *OSMnx: New methods for acquiring, constructing, analyzing,
  and visualizing complex street networks.* Computers, Environment and Urban Systems, 65,
  126–139.

---

**Citation style** for the final report: IEEE (adjust to the department's requirement —
confirm before Phase 7).

# AstroCare Bug Register

**Last updated:** 2026-11-15  
**Status legend:** `Fixed` means a root-cause fix and regression or reproducible verification exist.  
**Severity:** Critical, High, Medium, Low.

---

## 1. Register

| Bug ID | Component | Severity | Reproduction | Expected | Actual | Root cause | Fix | Regression test | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QA-001 | Frontend/Backend integration | Critical | Start `scripts/run.sh`; open `/`; open Simulation; inspect network. | Simulation controls reach the unified service. | `http://localhost:3000/simulation/status` and control POSTs returned 404. | Frontend used same-origin paths without a backend base URL. | Added `frontend/src/lib/backend.ts` and `NEXT_PUBLIC_BACKEND_HTTP_URL`; routed all simulation calls through it. | `frontend/src/lib/backend.test.ts`; live endpoint check in `docs/API_ENDPOINT_AUDIT.md`. | Fixed |
| QA-002 | Frontend Digital Twin | Medium | Load Overview with browser network panel. | No request for an absent optional model. | `HEAD /models/astronaut_twin.glb` always returned 404. | Code probed an optional user-supplied asset directly. | Added `astronaut_models.json`; custom-twin HEAD is issued only when the manifest advertises it. | Asset manifest present; production build passed; live model URL check. | Fixed |
| QA-003 | Simulation/Backend integration | High | Start simulation and inspect Brain output. | Frontend selected astronaut matches Brain tick. | Brain emitted `ASTRO-01` while frontend selector used `astro-01`. | Public ID mapping used uppercase IDs. | Mapped simulation IDs to frontend IDs `astro-01`/`astro-02`; status endpoint uses same IDs. | `test_simulation_state_maps_to_brain_contract`; `test_public_astronaut_mapping_is_stable`. | Fixed |
| QA-004 | Frontend | Medium | Connect WebSocket with both astronauts active and inspect latest tick. | Overview uses telemetry for the selected astronaut. | Last tick could belong to the other astronaut. | `useDashboard` used the last element of an interleaved tick list. | Filter live ticks by selected astronaut ID, case-insensitively. | Contract test for ID mapping; frontend build/type check. | Fixed |
| QA-005 | Frontend | Medium | Receive interleaved ticks and inspect alert trend badge. | Spike/sustained classification uses one astronaut's history. | History included the other astronaut. | `ActiveFlags` sliced all ticks. | Filter recent ticks by the current tick's astronaut ID. | Frontend build/type check; code-level review. | Fixed |
| QA-006 | Simulation | High | Run a What-If from an advanced baseline. | Experiment continues from baseline state. | Engine state reset to initial defaults. | `reload_config` rebuilt all engines and astronaut states after restoration. | Apply mutations to the already cloned configuration without rebuilding engines. | `test_what_if_experiment_is_isolated`; What-If endpoint exercised over HTTP. | Fixed |
| QA-007 | Simulation | Medium | POST What-If with `sleep_duration_delta_h=-2`. | Sleep opportunity and sleep debt change. | Field was declared but never used. | No model parameter or application path existed. | Added `sleep_duration_delta_h` to sleep parameters and daily update. | `test_what_if_sleep_delta_actually_changes_sleep_debt`. | Fixed |
| QA-008 | Simulation | Medium | POST What-If with `missed_ared_days=7`. | ARED is missed and VO2max declines. | Field was declared but never used. | No scenario or adherence application existed. | Inject `MISSED_ARED` when requested and no explicit scenario is supplied. | `test_what_if_missed_ared_actually_reduces_vo2max`. | Fixed |
| QA-009 | Simulation/API | Medium | POST unknown countermeasure. | HTTP 400; no model change. | HTTP 200; no model change. | Unknown types fell through an if/elif chain. | Raise `ValueError`; unified service returns 400. | `test_unknown_countermeasure_is_rejected`; live API check. | Fixed |
| QA-010 | Frontend | Low | Set mission day below one. | Day stays within the 1-based domain. | Day could become zero. | Lower clamp was zero. | Clamp to day 1. | TypeScript build and existing triage tests. | Fixed |
| QA-011 | Shared contracts | High | Run `shared/generate_contracts_schema.py --check`. | Schema check passes. | Import failed because generator used an ASTRALIS-only module. | Unified contracts moved to `shared/contracts.py`. | Import shared contracts; update AstroCare schema identity. | `generate_contracts_schema.py --check` in QA script. | Fixed |
| QA-012 | Data pipeline | Medium | Normalize `N/A`. | Status `MISSING`, value null. | Status `SUSPECT`. | Missing-token comparison used uppercase token against lowercase set. | Use case-insensitive comparison. | `test_normalization_preserves_original_values`. | Fixed |
| QA-013 | Documentation | Low | Inspect project naming. | Consistent AstroCare naming. | Some documents still said ASTRALIS/Astralis. | Earlier repository naming. | Replaced project-name references while preserving code identifiers and verified constants. | Documentation link/name check. | Fixed |
| QA-014 | Frontend/Backend integration | Informational | Press Escape with modal/dropdown combinations. | Only the topmost dismissible surface closes; no navigation or API call. | Escape could close more than one global listener at once. | Multiple window-level handlers lacked dismissal priority. | Drawers and What-If drawer use capture-phase priority and stop propagation. | Source audit; frontend build; no navigation/API call found in code. | Fixed |
| QA-015 | Deployment | Medium | Start `docker compose up backend frontend`; browser calls backend. | Browser can reach mapped backend. | Backend bound only to container loopback. | HTTP/WebSocket servers used hardcoded `localhost`. | Documented native mode as the verified path; Docker configuration uses host-published ports but requires container binding review. | Not fully verified in a container runtime. | Open |

---

## 2. Non-bugs investigated

| Observation | Investigation result | Action |
| --- | --- | --- |
| “Escape caused HTTP 404.” | Source audit found only state-dismissal handlers; no navigation, router call, form submit, or API call. Live tests showed the actual 404s were simulation endpoints and the optional twin model. | Fixed those independent causes; Escape now has explicit dismissal priority. |
| Unknown frontend route returns 404. | `/unknown-intentional` returning 404 is the correct Next.js behavior. | No change. |
| Backend `/unknown` returns 404 JSON. | This is intentional and names the missing path. | No change. |

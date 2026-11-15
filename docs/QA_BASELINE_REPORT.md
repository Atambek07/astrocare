# AstroCare QA Baseline Report

**Date:** 2026-11-15  
**Repository state before stabilization:** `0e2c6cf docs: rename project references to AstroCare`  
**Working tree:** clean at the start of the audit.  
**Status:** baseline recorded before fixes.

---

## 1. Scope

The baseline covered:

- Backend Brain tests.
- Frontend unit tests.
- NASA data-pipeline tests available in the unified repository.
- Simulation tests available in the unified repository.
- Next.js production build.

No test was disabled, skipped, or weakened for this baseline.

---

## 2. Commands

### Complete baseline

```bash
scripts/test.sh
```

### Frontend production build

```bash
cd frontend
npm run build
```

---

## 3. Environment

| Item | Value |
| --- | --- |
| Operating system | Linux |
| Backend Python | CPython 3.12, AstroCare virtual environment |
| Frontend runtime | Node.js 20/npm toolchain |
| Backend framework | Standard-library HTTP service plus Pydantic contracts |
| Frontend framework | Next.js 14, React 18, TypeScript, Vitest |
| Doctor mode used for integration checks | Offline deterministic fallback |

---

## 4. Baseline test results

| Suite | Command | Result |
| --- | --- | --- |
| Backend Brain | `cd backend && .venv/bin/python -m pytest -q` | **651 passed** |
| Frontend | `cd frontend && npm test` | **37 passed** |
| NASA data pipeline (initial unified subset) | `PYTHONPATH=. backend/.venv/bin/python -m pytest data_pipeline/tests -q` | **3 passed** |
| Simulation (initial unified subset) | `PYTHONPATH=. backend/.venv/bin/python -m pytest tests/test_simulation_engine.py -q` | **3 passed** |
| Frontend production build | `npm run build` | **Passed** |

Aggregate initial result: **694 passed, 0 failed**. Sixteen ASTRALIS-era backend placeholders were not copied into the unified AstroCare repository and are therefore not counted as AstroCare skips.

---

## 5. Baseline build result

The Next.js production build completed successfully.

```text
✓ Compiled successfully
✓ Linting and checking validity of types
✓ Generating static pages
Route /        First Load JS: 89.1 kB
Route /crew    First Load JS: 89.1 kB
```

---

## 6. Baseline findings carried to the bug register

1. Simulation-control requests used same-origin frontend URLs such as `http://localhost:3000/simulation/status`, although the unified service listened on port `8765`.
2. The optional 3D twin asset `astronaut_twin.glb` did not exist, so every Digital Twin initialization issued a HEAD request with a guaranteed HTTP 404.
3. Brain IDs `astro-01` and `astro-02` did not match the frontend astronaut selector IDs unless case was ignored accidentally.
4. Live-flag trend classification mixed interleaved telemetry from both astronauts.
5. What-If experiments reset cloned astronaut state because configuration reload rebuilt engine state.
6. Two advertised What-If controls, `sleep_duration_delta_h` and `missed_ared_days`, were not fully applied.
7. Unknown countermeasures were silently ignored instead of rejected.
8. Mission-day control allowed day `0`, inconsistent with the 1-based domain contract.
9. Shared-schema generation still imported an ASTRALIS-only backend module and used an ASTRALIS schema identity.
10. NASA missing-value tokens were treated inconsistently because case folding was not used.
11. The optional custom-twin request was not gated by an asset manifest.

---

## 7. Interpretation

The existing test suites were healthy, but tests did not cover the cross-process HTTP boundary, frontend asset availability, or several What-If mutation paths. The baseline therefore showed that component-level code was sound while several integration seams remained unverified.

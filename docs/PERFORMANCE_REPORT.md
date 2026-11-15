# Performance Report

**Date:** 2026-11-15  
**Environment:** local Linux development workstation, CPU-only, no GPU required.  
**Backend:** CPython 3.12.  
**Frontend build:** Node.js 20/npm, Next.js 14.

---

## 1. Results

| Test | Configuration | Result | Runtime | Max RSS |
| --- | --- | ---: | ---: | ---: |
| 60-minute simulation | 2 astronauts, 1 Hz, 1 s internal/output step | 3,600 ticks/astronaut; 1 daily record/astronaut | **0.93 s** | ~39 MiB |
| 180-day simulation | 2 astronauts, 300 s internal/output step | 51,840 ticks/astronaut; 180 daily records/astronaut | **6.81 s** | ~128 MiB |
| Next.js production build | TypeScript check + static generation | success | **27.74 s** | ~720 MiB |

---

## 2. Integration latency

| Operation | Result |
| --- | --- |
| Simulation status HTTP query | immediate local response |
| Scenario start/terminate | immediate local response |
| What-If 10-minute isolated experiment | completed within normal synchronous request |
| WebSocket first tick | received immediately after service start |

---

## 3. Frontend bundle

Production build reported:

| Route | Size | First Load JS |
| --- | ---: | ---: |
| `/` | 1.4 kB | 89.1 kB |
| `/crew` | 1.4 kB | 89.1 kB |
| shared | — | 87.7 kB |

---

## 4. Resource strategy

1. Long-duration simulation does not integrate every physiological process at 1 Hz.
2. Historical runs use a 300 s internal/output step.
3. Frontend keeps a bounded 600-tick live ring buffer.
4. Backend history is bounded to the last 50 outputs.
5. Static NASA artifacts are fetched only when a view needs them.
6. Optional 3D assets are not requested unless advertised by the asset manifest.

---

## 5. Observations

- A 180-day 1-Hz export would produce about 15.55 million rows per astronaut and is intentionally not the default.
- The 3D twin is the largest client-side asset; required anatomy model is approximately 7.3 MB.
- Frontend production build is the largest transient memory consumer in the current QA suite.

---

## 6. Future measurements

For production readiness, add:

1. long-run memory sampling over 24 hours;
2. WebSocket fan-out benchmark with many clients;
3. browser CPU/frame profiling for the 3D twin;
4. query benchmarking after persistent history storage is enabled.

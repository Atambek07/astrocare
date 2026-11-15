# Frontend Reference

**Application:** AstroCare Core  
**Framework:** Next.js 14 App Router, React 18, TypeScript, Tailwind CSS, Zustand, Recharts, Three.js.  
**Mode:** offline-first decision-support prototype.

---

## 1. Routes

| Route | Purpose |
| --- | --- |
| `/` | Main Digital Twin application. |
| `/crew` | Crew overview route. |
| Unknown route | Intentional Next.js 404. |

Most product sections are client-side states within `/` rather than separate server routes.

---

## 2. Main sections

| Section | Purpose |
| --- | --- |
| Overview | Critical alerts, status, vitals, 3D twin, next actions, cabin environment. |
| Health Analytics | Trends, baselines, abnormal readings, mission explorer. |
| AI Assistant | Offline rule-based role-specific briefing and question interface. |
| Training & Recovery | Recovery, readiness, exercise and bone/muscle status. |
| Mission History | Daily status, events, reports and activity log. |
| Data Sources | NASA provenance, pipeline status and study catalog. |
| Simulation | Unified simulation lifecycle, scenario and What-If controls. |
| Crew | Crew-wide status view. |
| Risk Radar | HRP-aligned risk visualization. |
| Routine | Measurement routine and gamified tasks. |
| Learn | Glossary and education. |

---

## 3. Digital Twin

The 3D twin supports:

- procedural or optional custom GLB model;
- anatomical muscle/organ/skeleton layers;
- body-zone selection;
- camera focus and rotation;
- system filtering;
- status-driven color and highlighting;
- 2D fallback when WebGL is unavailable.

The required anatomy asset is:

```text
frontend/public/models/astronaut_anatomy.glb
```

The body mesh is:

```text
frontend/public/models/astronaut_body.fbx
```

Optional custom twin availability is governed by:

```text
frontend/public/models/astronaut_models.json
```

This prevents a guaranteed 404 for an absent optional asset.

---

## 4. State management

`frontend/src/store/useHealthStore.ts` maintains:

- selected astronaut;
- mission day;
- environment;
- What-If selections;
- manual check-in overrides;
- bounded 600-tick live ring buffer;
- connection state;
- alert acknowledgment and audit log;
- protocol progress;
- view state.

The selected astronaut is `astro-01` by default, matching IDs emitted by the unified service.

---

## 5. Backend integration

### WebSocket

```text
NEXT_PUBLIC_BRAIN_WS_URL
```

The client reconnects with exponential backoff. If disconnected, explicit mock mode is enabled and shown.

### HTTP

```text
NEXT_PUBLIC_BACKEND_HTTP_URL
```

Used by Simulation view for status, lifecycle, scenario, countermeasure and What-If calls.

### Static NASA artifacts

Data Sources fetches local files under:

```text
/data/manifests/
/data/reference/
/data/processed/
```

---

## 6. Provenance display

The interface distinguishes:

- `NASA_REAL`;
- `NASA_DERIVED`;
- `SYNTHETIC`;
- demo/mock data.

The Data Sources view shows OSDR study IDs, pipeline stages, processing status, accepted/rejected studies and scientific limitations.

---

## 7. Error and connection states

| State | UI behavior |
| --- | --- |
| Fresh telemetry | Normal live status. |
| Delayed telemetry | Delayed indicator. |
| Signal lost | Stale/lost indicator. |
| Backend disconnected | Explicit mock badge; no silent substitution. |
| Simulation unavailable | Error banner in Simulation view. |
| WebGL failure | 2D twin fallback. |
| Malformed BrainTick | Rejected by zod; no unsafe render. |

---

## 8. Accessibility and interaction

Implemented patterns include:

- keyboard dismissal for drawers with topmost-surface priority;
- labels and aria attributes for major controls;
- status indicators that include text/color, not color alone;
- responsive layout;
- persistent research-prototype disclaimer.

---

## 9. Build and tests

```bash
cd frontend
npm install
npm test
npm run build
```

Current result: **39 frontend tests passed** and production build successful.

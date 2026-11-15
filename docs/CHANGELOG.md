# Changelog

All notable changes are documented here. Dates use UTC.

---

## [2026-11-15] QA stabilization release

### Added

- Formal QA baseline report.
- Bug register with verified root causes.
- API endpoint audit.
- NASA data validation report.
- Simulation validation report.
- Contract validation report.
- Error handling and observability reference.
- Performance report.
- System architecture, scientific methods, backend/frontend references, API reference, installation guide, limitations, changelog, QA final report and documentation index.
- Automated quality gates under `scripts/`.
- Machine-readable QA summary under `reports/`.
- Backend client helper for explicit unified-service base URL.
- Asset manifest for required and optional 3D models.
- Data pipeline normalization, quality and provenance tests.
- Unified contract tests.
- Simulation numerical, What-If and countermeasure regression tests.

### Fixed

- Frontend simulation controls no longer request same-origin `/simulation/*` routes and now use the configured backend URL.
- Optional custom twin asset is requested only when the asset manifest advertises it.
- Simulation IDs now map consistently to frontend astronaut IDs.
- Overview selects telemetry for the selected astronaut rather than the last interleaved tick.
- Alert spike/sustained classification no longer mixes astronauts.
- What-If experiments preserve restored baseline state.
- What-If `sleep_duration_delta_h` is applied.
- What-If `missed_ared_days` activates the missed-ARED path.
- Unknown countermeasures return HTTP 400 instead of silently doing nothing.
- Simulation controls no longer double-wrap backend URLs, fixing `backend route must start with /`.
- Mission day cannot drop below one.
- Shared JSON Schema generator uses unified AstroCare contracts and schema identity.
- Case-insensitive NASA missing tokens are classified as missing rather than suspect.
- Escape has explicit topmost dismissal priority for drawers and What-If panel.

### Changed

- Project documentation now consistently uses AstroCare naming.
- Backend virtual environment declares Pydantic because it consumes shared simulation contracts.
- QA scripts distinguish backend, frontend, data, simulation, integration, build and documentation checks.

---

## [2026-11-15] Unified integration release

### Added

- Unified AstroCare repository.
- Integrated Backend Brain, frontend Digital Twin, NASA data pipeline and simulation engine.
- Unified service combining Brain, HTTP dashboard, WebSocket and simulation.
- NASA evidence artifacts and manifests.
- Data Sources and Simulation frontend views.
- Native setup, run, test and demo scripts.
- Docker Compose scaffold.
- Integration audit and initial API/contract documentation.

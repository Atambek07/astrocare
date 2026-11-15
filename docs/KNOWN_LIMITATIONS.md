# Known Limitations

**Version:** 2026-11-15  
**Classification:** research/decision-support prototype; not a medical device.

---

## 1. Scientific limitations

1. AstroCare is not a clinically validated diagnostic or prognostic system.
2. NEWS2 was developed for adult hospital patients and has not been validated for astronauts or microgravity.
3. IMM-lite output is an evidence-style ranking of possible conditions, not a diagnosis or calibrated probability.
4. Doctor recommendations are decision-support text, not treatment authorization.
5. The simulation is not calibrated to an individual astronaut and does not reproduce a specific crew member.
6. SANS-related risk is an engineering indicator, not a measurement of intracranial pressure or a SANS diagnosis.
7. Radiation handling is accumulated exposure, not particle transport, organ dose or acute clinical severity modeling.
8. VO2max and musculoskeletal trajectories are simplified adaptation models.
9. Cognitive metrics are model outputs, not a validated neurobehavioral assessment.

---

## 2. NASA data limitations

1. NASA OSDR evidence is laboratory, biospecimen and timepoint data.
2. No continuous NASA astronaut HR/HRV/BP/SpO2 telemetry is included.
3. Sparse NASA measurements are never converted into fabricated 1 Hz vitals.
4. Some NASA values lack absolute timestamps; relative labels are preserved instead.
5. Some units are source-specific and remain unconverted when no documented mapping exists.
6. Large raw sequencing datasets were intentionally not downloaded.
7. OSD-977, OSD-968, OSD-898 and OSD-989 were inspected and rejected as radiation evidence.

---

## 3. Simulation limitations

1. Model coefficients include engineering assumptions and synthetic demonstration values.
2. Scenario magnitudes are synthetic and are not reproductions of specific events.
3. Multiscale integration can reduce fidelity when large internal steps are used.
4. What-If results are comparative explorations, not clinical predictions.
5. Only configured scenarios and countermeasures are modeled.
6. Unconfigured medical events, pharmacology, injuries and cumulative multimorbidity are not modeled.

---

## 4. Backend and integration limitations

1. The unified service binds to localhost and is intended for local demonstration.
2. CORS currently uses a wildcard and must be restricted before non-local deployment.
3. There is no authentication or multi-tenant authorization.
4. The WebSocket broadcaster is simple and does not include authentication, backpressure or horizontal scaling.
5. `SimulationEvent` is an internal contract, not yet an Architect-approved shared contract.
6. Request IDs and structured metrics are not yet implemented.

---

## 5. Frontend limitations

1. The 3D Digital Twin requires a modern WebGL-capable browser; otherwise it falls back to 2D.
2. Mock mode is needed when the backend is unavailable and is therefore always explicitly labeled.
3. Some historical analytics are derived from the existing deterministic demo generator, not from live backend history.
4. Browser automation coverage is not yet implemented.
5. Very long browser sessions require additional memory profiling.

---

## 6. Operational limitations

1. NASA data refresh requires internet access.
2. Local Ollama is optional; CPU-only inference may be slower than the doctor timeout, in which case fallback is used.
3. Docker Compose is provided but native startup is the verified primary path.
4. Data persistence currently uses files and manifests rather than a production database.

---

## 7. Non-goals

AstroCare does not:

1. diagnose disease;
2. authorize treatment;
3. replace a flight surgeon;
4. claim NASA, clinical or flight qualification;
5. represent synthetic crew members as real astronauts;
6. present mock data as live telemetry.

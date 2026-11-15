# ASTRALIS Data Pipeline (SPEC 1)

This package builds the offline `data_bundle/` from NASA OSDR public data and deterministic synthetic scenarios. It is owned by Data-agent (SPEC 1). The demo path never makes network calls; network access is used only during `make data`.

## Pipeline

```text
NASA DATA DISCOVERY
  -> INGESTION
  -> VALIDATION
  -> NORMALIZATION
  -> FEATURE EXTRACTION
  -> BASELINES
  -> OFFLINE BUNDLE
```

## Commands

From the repository root:

```bash
make data
```

Equivalent direct command:

```bash
python -m data_pipeline.build_offline_bundle
```

Generate only the synthetic 60-minute stream and anomaly manifest:

```bash
python -m data_pipeline.stream_generator
```

### Offline rebuild

If network access is unavailable but the pipeline cache already contains OSDR metadata, set:

```bash
ASTRALIS_OFFLINE_DATA=1 python -m data_pipeline.build_offline_bundle
```

In this mode the OSDR connector returns cached JSON and reports `CACHE_FALLBACK` when appropriate. It never invents missing NASA data.

## Module Map

| Path | Purpose |
| --- | --- |
| `connectors/osdr_api.py` | OSDR metadata, file index, and search connector with cache fallback |
| `connectors/osdr_files.py` | Public file listing, download, checksum verification, and raw-file preservation |
| `connectors/nasa_s3.py` | Public S3 access only after bucket verification from metadata or environment |
| `discovery/study_catalog.py` | OSDR search, ranking, classification, and explicit rejection records |
| `discovery/dataset_registry.py` | Dataset registry by category, modality, and downloaded-file counts |
| `ingestion/download_manager.py` | Retry, checksum, cache, HTTP Range resume, and fallback status |
| `ingestion/format_detector.py` | Format, modality, units hints, and recursive ZIP inspection |
| `processing/normalization.py` | Unit, value, timestamp, and subject normalization without imputation |
| `processing/quality_checks.py` | Completeness, ranges, timestamps, and baseline sufficiency |
| `processing/lab_extractor.py` | Real OSDR CBC, CMP, multiplex, and urine panel extraction |
| `processing/microbiome.py` | Species-level Shannon diversity from the OSD-572 MetaPhlAn table |
| `processing/baseline_builder.py` | Phase 1 and Phase 2 baselines computed from daily records |
| `processing/feature_extraction.py` | Contract-safe daily, laboratory, and derived feature helpers |
| `provenance/evidence_registry.py` | Provenance validation and `provenance_manifest.json` export |
| `provenance/knowledge.py` | Verified NASA references, protocols, evidence cards, radiation audit |
| `daily_generator.py` | Deterministic 180-day A1/A2 synthetic daily series |
| `stream_generator.py` | Deterministic 1-Hz A1/A2 stream and anomaly manifest |
| `synthetic_labs.py` | Synthetic CBC, CMP, and cytokine demonstration panels |
| `build_offline_bundle.py` | Bundle orchestration, SQLite, manifests, validation, and frontend mirror |

## Configuration

The following files document the values used by the pipeline:

- `config/sources.yaml` — OSDR endpoints, verified studies, rejected-study audit, offline mode.
- `config/ingestion_policy.yaml` — selected-file policy, HTTP retries, checksums, cache, restricted-access rules.
- `config/scoring.yaml` — transparent 100-point relevance scoring and category rules.
- `config/quality_rules.yaml` — quality statuses, missing-value tokens, physiological ranges, baseline rules.
- `config/synthetic_scenarios.yaml` — seed, crew, stream, daily, anomaly, and lab-panel configuration.

`data_bundle/synthetic/generation_config.json` is the machine-readable generation record written by the build.

## Scientific Traceability

- `NASA_REAL` records preserve original values, source files, URLs, subjects, timepoints, and SHA-256 hashes.
- `NASA_DERIVED` records such as Shannon diversity state the exact processing method and parent source.
- `SYNTHETIC` records always identify generator name, generator version, random seed, scenario ID, and configuration.
- Missing NASA values remain `null`; they are never inferred.
- The seven Inspiration4 OSDR studies are verified, but they are biospecimen and laboratory studies, not continuous 180-day mission telemetry.
- OSD-977, OSD-968, OSD-898, and OSD-989 were inspected and rejected as DET-06 radiation evidence; the rejection reasons are stored in `data_bundle/provenance/radiation_evidence.json`.

## Tests

Run:

```bash
make test
```

The bundle-specific tests live in `tests/test_data_bundle.py`. They verify row counts, timestamps, SQLite integrity, schema validation, provenance coverage, anomaly behavior, baselines, lab evidence, reports, and the frontend mirror.

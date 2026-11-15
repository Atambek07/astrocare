# NASA Data Validation Report

**Date:** 2026-11-15  
**Pipeline:** `data_pipeline/`  
**Bundle manifest:** `data/manifests/bundle_manifest.json`  
**Provenance classes:** `NASA_REAL`, `NASA_DERIVED`, `SYNTHETIC`

---

## 1. Verification summary

| Check | Result |
| --- | --- |
| Public OSDR studies verified | 7 core Inspiration4 studies |
| Additional discovered studies cataloged | 79 total |
| Accepted studies | 71 |
| Rejected studies with reason | 8 |
| Real laboratory values extracted | 23,174 |
| Real laboratory panel groupings | 133 |
| Microbiome samples processed | 329 |
| Valid Shannon-diversity values | 327 |
| Provenance records in source bundle | 31,339 |
| Download fallback status | `NONE` |
| Fabricated continuous NASA vitals | None |

---

## 2. Datasets used

| Study | Title/scope | Public data used | Processing result |
| --- | --- | --- | --- |
| OSD-569 | Whole blood measurements from SpaceX Inspiration4; CBC and omics. | CBC submitted/transformed CSV; ISA metadata ZIP. | 553 CBC observations normalized and retained as `NASA_REAL`. |
| OSD-570 | PBMC snRNA/snATAC and immune repertoire. | ISA metadata ZIP; processed snRNA XLSX. | Cataloged; not interpreted as continuous vitals. |
| OSD-571 | Plasma proteomics, EVPs, metabolomics, cfDNA/cfRNA. | Metadata ZIP, sample metadata, processed proteomics/metabolomics tables. | Cataloged; file-level evidence retained. |
| OSD-572 | Oral, nasal and skin microbiome swabs. | MetaPhlAn taxonomy TSV, pathway TSV, README, metadata ZIP. | Species-relative abundances used to derive Shannon diversity. |
| OSD-573 | Dragon capsule microbiome swabs. | Metadata ZIP. | Cataloged; raw metagenomics intentionally not downloaded. |
| OSD-575 | CMP and serum immune/cardiac cytokine arrays. | CMP, EvePanel and AlamarPanel files. | 13,733 serum laboratory observations. |
| OSD-656 | Urine inflammation panel. | AlamarPanel and target information. | 8,888 urine laboratory observations. |

Source URLs follow the public OSDR study pattern:

```text
https://osdr.nasa.gov/bio/repo/data/studies/OSD-569
https://osdr.nasa.gov/bio/repo/data/studies/OSD-570
https://osdr.nasa.gov/bio/repo/data/studies/OSD-571
https://osdr.nasa.gov/bio/repo/data/studies/OSD-572
https://osdr.nasa.gov/bio/repo/data/studies/OSD-573
https://osdr.nasa.gov/bio/repo/data/studies/OSD-575
https://osdr.nasa.gov/bio/repo/data/studies/OSD-656
```

---

## 3. Download and integrity verification

Selected public files are recorded in:

```text
data/manifests/download_manifest.json
```

Each record includes:

- study ID;
- file name;
- category/subcategory;
- expected and actual size;
- SHA-256;
- public source URL;
- download timestamp;
- local path;
- public redistribution status.

The download manager verifies checksums, supports cache fallback, retries, timeout handling and HTTP Range resume. Restricted or invisible OSDR files are not downloaded.

---

## 4. Normalization and quality control

### Laboratory values

Original values and units are retained. Normalization uses a documented unit table and does not invent conversions.

Quality statuses used:

- `VALID`;
- `VALID_WITH_WARNINGS`;
- `MISSING`;
- `SUSPECT`;
- `INVALID_UNIT`.

Case-insensitive missing tokens include `N/A`, `NA`, `NaN`, `none`, `null`, `missing`, `not reported` and `not available`.

### Timepoints

OSDR timepoints such as `L-92`, `L-44`, `L-3`, `R+1`, `R+45`, `R+82` and `R+194` are preserved as source-relative labels. They are not converted into fabricated timestamps.

### Quality report

The bundled report states:

- quality status: `VALID`;
- continuous telemetry available: `false`;
- no missing laboratory values in the processed set;
- warnings that absolute collection time is unavailable and synthetic A1/A2 values are not NASA measurements.

---

## 5. Derived evidence

### Microbiome Shannon diversity

Source: OSD-572 MetaPhlAn species table.  
Method: Shannon diversity over species-relative abundance.  
Class: `NASA_DERIVED`.  
Result: 329 samples; 327 valid diversity values.

### Laboratory summaries

Class: `NASA_DERIVED`.  
Method: descriptive mean, standard deviation, median, minimum and maximum grouped by study, panel, analyte, timepoint and unit.  
No reference interval is inferred from these summaries.

---

## 6. Rejected studies

OSD-977, OSD-968, OSD-898 and OSD-989 were inspected and explicitly rejected as DET-06 radiation evidence. Their actual titles and reasons are recorded in `data/reference/radiation_evidence.json`.

Examples:

- OSD-977: rat bone study, not radiation evidence.
- OSD-968: hippocampal neuron study, not radiation evidence.
- OSD-898: mouse blood-brain barrier study, not radiation evidence.
- OSD-989: spacecraft bioburden study, not radiation evidence.

Rejected studies are not silently discarded.

---

## 7. Provenance verification

| Class | Requirement | Verification |
| --- | --- | --- |
| `NASA_REAL` | Study/file/URL/source value retained. | Laboratory extractor retains original value, unit, study, file, subject, timepoint and provenance ID. |
| `NASA_DERIVED` | Transformation method retained. | Shannon and descriptive summaries record method and parent study. |
| `SYNTHETIC` | Generator/version/seed/scenario/configuration retained. | Simulation provenance records include engine version, model version, seed and scenario. |

Automated checks confirm that a synthetic record claiming a NASA study is rejected.

---

## 8. Scientific limitation

OSDR evidence is sparse, laboratory-based and timepoint-specific. AstroCare does not convert these measurements into continuous 1 Hz HR, HRV, blood pressure or SpO2 telemetry. Continuous physiological streams are generated by the simulation engine and labeled `SYNTHETIC`.

---

## 9. Test evidence

```bash
PYTHONPATH=. backend/.venv/bin/python -m pytest data_pipeline/tests -q
```

Result: **10 passed**.

Covered areas:

- missing/invalid value handling;
- unit preservation;
- relative timepoint handling;
- completeness, units, ranges and timestamps;
- baseline sufficiency;
- NASA_REAL provenance export;
- rejection of synthetic NASA identity.

---

## 10. Reproduce

Full rebuild:

```bash
python -m data_pipeline.build_offline_bundle
```

Offline rebuild:

```bash
ASTRALIS_OFFLINE_DATA=1 python -m data_pipeline.build_offline_bundle
```

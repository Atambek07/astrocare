# Installation and Deployment

**Version:** 2026-11-15  
**Primary verified path:** native local execution.  
**Primary use:** local research demonstration.

---

## 1. Prerequisites

| Requirement | Version |
| --- | --- |
| Python | 3.11 or newer; tested on 3.12 |
| Node.js/npm | Node 20-era toolchain |
| Git | Any recent version |
| Disk | Several GB if frontend dependencies and NASA assets are included |
| GPU | Not required |

Optional:

- Docker and Docker Compose;
- Ollama with `qwen2.5:7b-instruct` for local model-generated recommendations.

---

## 2. Obtain the repository

```bash
git clone git@github.com:Atambek07/astrocare.git
cd astrocare
```

---

## 3. One-command setup

```bash
scripts/setup.sh
```

This creates `backend/.venv`, installs backend dependencies, and installs frontend dependencies if `frontend/node_modules` is absent.

---

## 4. Environment configuration

Copy the example:

```bash
cp .env.example .env
```

Variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `ASTROCARE_BACKEND_PORT` | `8765` | Backend HTTP port. |
| `ASTROCARE_WS_PORT` | `8787` | WebSocket port. |
| `ASTROCARE_FRONTEND_PORT` | `3000` | Frontend port. |
| `ASTRO_DOCTOR_OFFLINE` | `1` in scripts | Disables the background Ollama recommendation layer; an explicitly selected AI Assistant chat model still works. |
| `ASTRO_OLLAMA_URL` | `http://localhost:11434` | Local Ollama URL used by Doctor Layer and AI Assistant chat. |
| `ASTRO_OLLAMA_MODEL` | `qwen2.5:7b-instruct` | Default/background recommendation model; does not override a user-selected chat model. |
| `NEXT_PUBLIC_BRAIN_WS_URL` | `ws://localhost:8787` | Frontend WebSocket URL. |
| `NEXT_PUBLIC_BACKEND_HTTP_URL` | `http://localhost:8765` | Frontend simulation/data status URL. |

Do not commit `.env`.

---

## 5. NASA data setup

The repository includes a verified NASA evidence bundle under `data/`.

To rebuild:

```bash
python -m data_pipeline.build_offline_bundle
```

Offline rebuild:

```bash
ASTRALIS_OFFLINE_DATA=1 python -m data_pipeline.build_offline_bundle
```

Internet is required only for fresh OSDR retrieval.

### Optional: local AI model

AstroCare works fully without Ollama. To enable the optional local model:

1. Install [Ollama](https://ollama.com).
2. Pull a model, for example:

   ```bash
   ollama pull qwen2.5:7b-instruct
   ```

3. Start the unified backend.
4. Open **AI Assistant**.
5. Pick the model in **Local AI model**.
6. If it does not appear, use **Check again**.

`qwen2.5:7b-instruct` is the model verified with the current prompt. Smaller 1.5B and 3B models may be useful on weak laptops, but they have **not** been tested with the current AstroCare prompt; do not present them as verified.

On Windows, cloning to a short path and enabling long paths avoids `Filename too long` errors from long NASA file names:

```bash
git config --global core.longpaths true
```

---

## 6. Start the unified application

Native verified mode:

```bash
scripts/run.sh
```

Optional scenario startup:

```bash
scripts/run.sh HYPERCAPNIC_CABIN
```

URLs:

- Frontend: `http://localhost:3000`;
- Backend: `http://localhost:8765`;
- WebSocket: `ws://localhost:8787`.

---

## 7. Start individual components

### Backend only

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=src:$PWD/.. ASTRO_DOCTOR_OFFLINE=1 \
  python -m astro_brain.astrocare_service --port 8765 --ws-port 8787
```

### Frontend only

```bash
cd frontend
npm run dev
```

### Simulation CLI only

```bash
python -m simulation_engine.cli \
  --duration-seconds 3600 \
  --internal-step 1.0 \
  --output-step 1.0 \
  --export-dir simulation_exports \
  --format jsonl \
  --summary
```

---

## 8. Docker Compose

A compose file is provided:

```bash
docker compose up --build
```

Current note: the Python HTTP and WebSocket services were designed for local binding. If container networking fails, use the native path or adjust the service bind hosts before deployment.

---

## 9. Database/data setup

The NASA pipeline currently stores evidence as files and manifests. No external database is required for the demonstration.

Artifacts:

```text
data/raw/nasa/
data/manifests/
data/processed/
data/reference/
```

---

## 10. Offline operation

After setup and NASA acquisition, AstroCare works offline:

1. Use cached NASA files.
2. Run simulation locally.
3. Set `ASTRO_DOCTOR_OFFLINE=1`.
4. Serve frontend locally.
5. Observe explicit mock/live badges.

The last NASA retrieval timestamp and fallback status are shown in Data Sources and `/data/status`.

---

## 11. Troubleshooting

| Symptom | Cause | Resolution |
| --- | --- | --- |
| Frontend simulation returns 404 | Frontend is not configured with backend HTTP URL. | Set `NEXT_PUBLIC_BACKEND_HTTP_URL=http://localhost:8765`. |
| Port already in use | Previous backend/frontend process. | Stop process or change `ASTROCARE_*_PORT`. |
| Doctor recommendation source is `fallback` | Ollama unavailable/slow/offline. | Expected; deterministic fallback is intentional. |
| WebSocket mock badge appears | Backend WebSocket unavailable. | Start unified service or set WebSocket URL. |
| Schema check fails | Shared contracts changed. | Run `shared/generate_contracts_schema.py`. |
| NASA manifests unavailable | Bundle missing. | Run `data_pipeline/build_offline_bundle.py`. |

---

## 12. Stop the application

Use `Ctrl+C` in the terminal running `scripts/run.sh`.

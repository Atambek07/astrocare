#!/usr/bin/env bash
# Минимальный end-to-end контроль: запуск сервиса, HTTP и WebSocket.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHONPATH="$ROOT" backend/.venv/bin/python - <<'PY'
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

root = Path.cwd()
env = os.environ.copy()
env["PYTHONPATH"] = str(root)
env["ASTRO_DOCTOR_OFFLINE"] = "1"
port = 8871
ws_port = 8872
process = subprocess.Popen(
    [
        str(root / "backend/.venv/bin/python"),
        "-m",
        "astro_brain.astrocare_service",
        "--port", str(port),
        "--ws-port", str(ws_port),
    ],
    cwd=root / "backend",
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)

def request(path: str, method: str = "GET", body: dict | None = None) -> tuple[int, dict | list | str]:
    data = None if body is None else json.dumps(body).encode()
    headers = {} if body is None else {"Content-Type": "application/json"}
    req = urllib.request.Request(f"http://localhost:{port}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            payload = response.read().decode()
            status = response.status
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode()
        status = exc.code
    try:
        return status, json.loads(payload)
    except json.JSONDecodeError:
        return status, payload

try:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        try:
            status, _ = request("/simulation/status")
            if status == 200:
                break
        except Exception:
            time.sleep(0.2)
    else:
        raise RuntimeError("service did not become ready")

    checks = []
    status, payload = request("/simulation/status")
    checks.append(("simulation status", status == 200 and payload["status"]["source_type"] == "SYNTHETIC"))
    status, payload = request("/data/status")
    checks.append(("NASA status", status == 200))
    status, payload = request("/state/all")
    checks.append(("Brain state/all", status == 200 and payload["count"] >= 1))
    status, payload = request("/history")
    checks.append(("Brain history", status == 200 and len(payload) >= 1))
    status, payload = request("/log")
    checks.append(("mission log", status == 200))
    status, payload = request("/report?astronaut_id=astro-01")
    checks.append(("mission report", status == 200))
    status, payload = request("/simulation/scenario", "POST", {"scenario_id": "HYPERCAPNIC_CABIN", "action": "start"})
    checks.append(("scenario start", status == 200))
    status, payload = request("/simulation/control", "POST", {"action": "pause"})
    checks.append(("pause", status == 200))
    status, payload = request("/simulation/control", "POST", {"action": "resume"})
    checks.append(("resume", status == 200))
    status, payload = request("/simulation/countermeasure", "POST", {"type": "ENVIRONMENTAL_CORRECTION"})
    checks.append(("countermeasure", status == 200))
    status, payload = request("/simulation/scenario", "POST", {"scenario_id": "HYPERCAPNIC_CABIN", "action": "terminate"})
    checks.append(("scenario terminate", status == 200))
    status, payload = request("/simulation/what-if", "POST", {"sleep_duration_delta_h": -2, "duration_seconds": 600})
    checks.append(("What-If", status == 200 and "difference_metrics" in payload))
    status, payload = request("/unknown-intentional")
    checks.append(("intentional 404", status == 404))

    # WebSocket handshake and one framed BrainTick.
    sock = socket.create_connection(("localhost", ws_port), timeout=5)
    key = "dGhlIHNhbXBsZSBub25jZQ=="
    sock.sendall(
        (
            f"GET / HTTP/1.1\r\nHost: localhost:{ws_port}\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        ).encode()
    )
    handshake = b""
    while b"\r\n\r\n" not in handshake:
        handshake += sock.recv(1024)
    checks.append(("WebSocket handshake", b"101 Switching Protocols" in handshake))

    def recv_exact(n: int) -> bytes:
        out = b""
        while len(out) < n:
            part = sock.recv(n - len(out))
            if not part:
                raise EOFError
            out += part
        return out

    header = recv_exact(2)
    length = header[1] & 127
    if length == 126:
        length = int.from_bytes(recv_exact(2), "big")
    elif length == 127:
        length = int.from_bytes(recv_exact(8), "big")
    tick = json.loads(recv_exact(length))
    checks.append(("WebSocket BrainTick", {"timestamp", "alertLevel", "activeFlags", "rawVitals", "doctorRecommendation"} <= set(tick)))
    sock.close()

    failed = [name for name, passed in checks if not passed]
    if failed:
        print("E2E FAILED: " + ", ".join(failed), file=sys.stderr)
        raise SystemExit(1)
    print(f"E2E PASSED: {len(checks)} checks")
finally:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
PY

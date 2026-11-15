"""Единый runtime AstroCare: Brain, HTTP-дашборд, WebSocket и живая симуляция.

Модуль связывает Advanced Hybrid Simulation Engine с существующим Brain и
существующим WebSocket-броадкастером. Он не заменяет Backend Brain и не
реализует медицинскую аналитику на фронте.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from collections.abc import Mapping
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from astro_brain.adapters.astralis import stream_tick_to_input  # noqa: E402
from astro_brain.dashboard import (  # noqa: E402
    DEFAULT_CREW,
    DEFAULT_PORT,
    DEFAULT_SEED,
    DEFAULT_WS_PORT,
    StateStore,
    _doctor_stats_of,
    build_brain,
    build_server,
)
from astro_brain.pipeline import Brain  # noqa: E402
from astro_brain.ws_server import BrainWebSocketServer  # noqa: E402
from simulation_engine import SimulationController  # noqa: E402

# Маппинг внутренних симуляционных ID на публичные ID AstroCare.
ASTRONAUT_ID_MAP: dict[str, str] = {
    "A1": "astro-01",
    "A2": "astro-02",
}


def public_astronaut_id(astronaut_id: str) -> str:
    """Преобразовать внутренний ID симуляции в публичный ID AstroCare."""
    return ASTRONAUT_ID_MAP.get(astronaut_id, astronaut_id)


def _daily_context_from_state(state: Mapping[str, Any]) -> dict[str, Any]:
    """Преобразовать суточное состояние симуляции в словарь для адаптера."""
    countermeasure = state.get("countermeasure", {})
    return {
        "sleep_duration_h": state.get("physiology", {}).get("sleep_duration_h"),
        "ared_exercise_completed": countermeasure.get("ared_completed_today", False),
        "cumulative_radiation_msv": state.get("environment_state", {}).get("cumulative_radiation_msv"),
    }


def _state_from_controller(controller: SimulationController, astronaut_id: str) -> dict[str, Any]:
    """Собрать состояние астронавта и окружения для адаптера."""
    astronaut_state = controller.get_astronaut_state(astronaut_id)
    environment = controller.get_environment_state()
    return {
        **astronaut_state,
        "environment_state": environment,
    }


def simulation_state_to_input(controller: SimulationController, astronaut_id: str) -> dict[str, Any]:
    """Собрать входной контракт Brain из текущего состояния симуляции."""
    state = _state_from_controller(controller, astronaut_id)
    tick = {
        "timestamp": controller.clock.timestamp_utc,
        "astronaut_id": astronaut_id,
        "mission_day": controller.clock.mission_day,
        "mission_phase": controller.clock.mission_phase,
        "hr": state["physiology"]["hr"],
        "spo2": round(state["physiology"]["spo2"]),
        "systolic_bp": int(round(state["physiology"]["sbp"])),
        "diastolic_bp": int(round(state["physiology"]["dbp"])),
        "temp_c": state["physiology"]["temp_c"],
        "resp_rate": int(round(state["physiology"]["resp_rate"])),
        "radiation_dose_rate": state["environment_state"]["radiation_dose_rate_msv_h"],
        "cabin_ppco2": state["environment_state"]["cabin_ppco2_mmhg"],
        "iop_mmhg": state["physiology"]["iop_mmhg"],
        "hrv_rmssd": state["physiology"]["hrv_rmssd"],
        "pvt_slowest10_rt": state["physiology"]["pvt_slowest10_rt_ms"],
    }
    daily = _daily_context_from_state(state)
    payload = stream_tick_to_input(tick, daily)
    payload["astronaut_id"] = public_astronaut_id(astronaut_id)
    return payload


class AstrocareStateStore(StateStore):
    """StateStore с ссылкой на runtime симуляции для HTTP-контроля."""

    def __init__(self, history_limit: int = 50) -> None:
        super().__init__(history_limit=history_limit)
        self.simulation_controller: SimulationController | None = None
        self.mode: str = "simulation"

    def set_simulation_controller(self, controller: SimulationController) -> None:
        """Привязать контроллер симуляции к store."""
        self.simulation_controller = controller


def _simulation_loop(
    *,
    brain: Brain,
    store: AstrocareStateStore,
    controller: SimulationController,
    ws: BrainWebSocketServer | None,
    seq: list[int],
    duration_seconds: float | None = None,
    verbose: bool = False,
) -> None:
    """Живой цикл симуляции: один тик -> Brain -> WebSocket/HTTP store."""
    deadline = time.monotonic() + duration_seconds if duration_seconds else None
    try:
        for tick in controller.iter_live():
            if deadline is not None and time.monotonic() >= deadline:
                break
            astronaut_id = str(tick.get("astronaut_id", ""))
            if not astronaut_id:
                continue
            raw = simulation_state_to_input(controller, astronaut_id)
            try:
                output = brain.process(raw)
            except Exception as exc:  # noqa: BLE001 - плохой тик не должен убивать поток
                if verbose:
                    print(f"simulation: skipped tick for {astronaut_id}: {exc!r}", file=sys.stderr)
                continue
            store.update(output, _doctor_stats_of(brain))
            if ws is not None:
                ws.broadcast(_frontend_tick(output, raw, seq[0]))
                seq[0] += 1
    except Exception as exc:  # noqa: BLE001 - логируем и останавливаем цикл аккуратно
        print(f"simulation loop stopped: {type(exc).__name__}: {exc}", file=sys.stderr)


def _frontend_tick(output: Mapping[str, Any], raw: Mapping[str, Any], seq: int) -> dict[str, Any]:
    """Формировать BrainTick для существующего фронтенда."""
    from astro_brain.adapters.frontend import to_brain_tick

    return to_brain_tick(output, raw, seq)


def build_astrocare_handler(
    brain: Brain,
    store: AstrocareStateStore,
    *,
    ws: BrainWebSocketServer | None = None,
    seq: list[int] | None = None,
) -> type:
    """Создать обработчик с стандартными эндпоинтами и управлением симуляцией."""
    from astro_brain.dashboard import _Handler

    class AstrocareHandler(_Handler):
        """Расширяет тестовый дашборд эндпоинтами управления симуляцией."""

        def do_GET(self) -> None:  # noqa: N802
            path = urlsplit(self.path).path
            if path == "/simulation/status":
                self._handle_simulation_status()
                return
            if path == "/data/status":
                self._handle_data_status()
                return
            super().do_GET()

        def do_POST(self) -> None:  # noqa: N802
            path = urlsplit(self.path).path
            if path == "/simulation/control":
                self._handle_simulation_control()
                return
            if path == "/simulation/scenario":
                self._handle_simulation_scenario()
                return
            if path == "/simulation/countermeasure":
                self._handle_simulation_countermeasure()
                return
            if path == "/simulation/what-if":
                self._handle_simulation_what_if()
                return
            super().do_POST()

        def _controller(self) -> SimulationController:
            controller = store.simulation_controller
            if controller is None:
                raise RuntimeError("simulation controller is unavailable")
            return controller

        def _read_json_body(self) -> Any:
            return super()._read_json_body()

        def _handle_simulation_status(self) -> None:
            controller = self._controller()
            self._send_json(
                200,
                {
                    "status": controller.get_state().model_dump(mode="json"),
                    "astronauts": [public_astronaut_id(item) for item in controller.astronaut_states],
                    "environment": controller.get_environment_state(),
                    "mode": store.mode,
                },
            )

        def _handle_data_status(self) -> None:
            manifest_path = _PROJECT_ROOT / "data" / "manifests" / "bundle_manifest.json"
            payload: dict[str, Any] = {"manifest_available": manifest_path.exists()}
            if manifest_path.exists():
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    payload.update(
                        {
                            "bundle_id": manifest.get("bundle_id"),
                            "generated_at_utc": manifest.get("generated_at_utc"),
                            "fallback_status": manifest.get("fallback_status"),
                            "counts": manifest.get("counts", {}),
                        }
                    )
                except json.JSONDecodeError as exc:
                    payload["manifest_error"] = str(exc)
            self._send_json(200, payload)

        def _handle_simulation_control(self) -> None:
            try:
                payload = self._read_json_body()
            except json.JSONDecodeError as exc:
                self._send_json(400, {"error": f"invalid JSON body: {exc}"})
                return
            action = payload.get("action")
            try:
                controller = self._controller()
                if action == "start":
                    controller.start()
                elif action == "pause":
                    controller.pause()
                elif action == "resume":
                    controller.resume()
                elif action == "stop":
                    controller.stop()
                elif action == "reset":
                    controller.reset()
                elif action == "set_speed":
                    controller.set_speed(float(payload.get("speed", 1.0)))
                else:
                    raise ValueError("action must be start, pause, resume, stop, reset, or set_speed")
            except (TypeError, ValueError) as exc:
                self._send_json(400, {"error": str(exc)})
                return
            self._send_json(200, {"status": "ok", "simulation": controller.get_state().model_dump(mode="json")})

        def _handle_simulation_scenario(self) -> None:
            try:
                payload = self._read_json_body()
            except json.JSONDecodeError as exc:
                self._send_json(400, {"error": f"invalid JSON body: {exc}"})
                return
            scenario_id = payload.get("scenario_id")
            action = payload.get("action", "start")
            if not isinstance(scenario_id, str) or not scenario_id:
                self._send_json(400, {"error": "scenario_id is required"})
                return
            try:
                controller = self._controller()
                if action == "start":
                    event = controller.inject_scenario(scenario_id)
                elif action == "terminate":
                    event = controller.terminate_scenario(scenario_id)
                else:
                    raise ValueError("action must be start or terminate")
            except (KeyError, ValueError) as exc:
                self._send_json(400, {"error": str(exc)})
                return
            self._send_json(200, {"status": "ok", "event": event.model_dump(mode="json")})

        def _handle_simulation_countermeasure(self) -> None:
            try:
                payload = self._read_json_body()
            except json.JSONDecodeError as exc:
                self._send_json(400, {"error": f"invalid JSON body: {exc}"})
                return
            countermeasure_type = payload.get("type")
            if not isinstance(countermeasure_type, str) or not countermeasure_type:
                self._send_json(400, {"error": "type is required"})
                return
            astronaut_id = payload.get("astronaut_id")
            if astronaut_id is not None and not isinstance(astronaut_id, str):
                self._send_json(400, {"error": "astronaut_id must be a string or null"})
                return
            try:
                event = self._controller().apply_countermeasure(
                    countermeasure_type,
                    astronaut_id=astronaut_id,
                    effectiveness=float(payload.get("effectiveness", 1.0)),
                )
            except (KeyError, TypeError, ValueError) as exc:
                self._send_json(400, {"error": str(exc)})
                return
            self._send_json(200, {"status": "ok", "event": event.model_dump(mode="json")})

        def _handle_simulation_what_if(self) -> None:
            try:
                payload = self._read_json_body()
            except json.JSONDecodeError as exc:
                self._send_json(400, {"error": f"invalid JSON body: {exc}"})
                return
            from simulation_engine.what_if import WhatIfModification

            try:
                modification = WhatIfModification(
                    ppco2_target_mmhg=payload.get("ppco2_target_mmhg"),
                    sleep_duration_delta_h=float(payload.get("sleep_duration_delta_h", 0.0)),
                    missed_ared_days=int(payload.get("missed_ared_days", 0)),
                )
                result = self._controller().run_what_if(
                    modification,
                    duration_seconds=int(payload.get("duration_seconds", 3600)),
                    experiment_id=str(payload.get("experiment_id", "WHAT_IF_EXPERIMENT")),
                )
            except (KeyError, TypeError, ValueError) as exc:
                self._send_json(400, {"error": str(exc)})
                return
            self._send_json(200, result.to_dict())

    return type(
        "BoundAstrocareHandler",
        (AstrocareHandler,),
        {
            "brain": brain,
            "store": store,
            "verbose": False,
            "ws": ws,
            "seq": seq or [0],
            "server_version": "AstroCareUnified/1.0",
        },
    )


def build_astrocare_server(
    port: int,
    brain: Brain,
    store: AstrocareStateStore,
    *,
    ws: BrainWebSocketServer | None = None,
    seq: list[int] | None = None,
) -> ThreadingHTTPServer:
    """Создать HTTP-сервер AstroCare с эндпоинтами управления симуляцией."""
    handler_cls = build_astrocare_handler(brain, store, ws=ws, seq=seq)
    return ThreadingHTTPServer(("localhost", port), handler_cls)


def main(argv: list[str] | None = None) -> None:
    """Запустить единый сервис AstroCare."""
    parser = argparse.ArgumentParser(prog="astro_brain.astrocare_service")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--ws-port", type=int, default=DEFAULT_WS_PORT)
    parser.add_argument("--duration-seconds", type=float, default=0)
    parser.add_argument("--scenario", action="append", default=[])
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    brain = build_brain(offline=args.offline)
    store = AstrocareStateStore()
    controller = SimulationController()
    store.set_simulation_controller(controller)
    ws = BrainWebSocketServer(port=args.ws_port) if args.ws_port else None
    if ws is not None:
        ws.start()
    seq = [0]
    server = build_astrocare_server(args.port, brain, store, ws=ws, seq=seq)
    controller.start()
    for scenario_id in args.scenario:
        controller.inject_scenario(scenario_id)
    thread = threading.Thread(
        target=_simulation_loop,
        kwargs={
            "brain": brain,
            "store": store,
            "controller": controller,
            "ws": ws,
            "seq": seq,
            "duration_seconds": args.duration_seconds if args.duration_seconds > 0 else None,
            "verbose": args.verbose,
        },
        daemon=True,
    )
    thread.start()
    print(
        f"AstroCare unified service listening on http://localhost:{server.server_port} "
        f"and ws://localhost:{ws.port if ws is not None else DEFAULT_WS_PORT}",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
        if ws is not None:
            ws.close()


if __name__ == "__main__":
    main()

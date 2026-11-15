"""CLI симуляционного движка.

Позволяет быстро проверить 60-минутный поток, 180-дневную миссию и экспорт.
Не является API Backend Agent.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import NumericalConfig
from .controller import SimulationController
from .profiles import default_environment, default_profiles, default_validation


def build_parser() -> argparse.ArgumentParser:
    """Создать argparse-парсер CLI."""
    parser = argparse.ArgumentParser(description="Run the ASTRALIS hybrid simulation engine.")
    parser.add_argument("--duration-seconds", type=int, default=3600, help="Mission time to simulate.")
    parser.add_argument("--internal-step", type=float, default=1.0, help="Internal integration step, seconds.")
    parser.add_argument("--output-step", type=float, default=1.0, help="Telemetry output step, seconds.")
    parser.add_argument("--scenario", action="append", default=[], help="Scenario ID to inject at start.")
    parser.add_argument("--export-dir", type=Path, default=Path("simulation_exports"), help="Export directory.")
    parser.add_argument("--format", choices=["json", "jsonl", "csv", "all"], default="jsonl")
    parser.add_argument("--summary", action="store_true", help="Print final mission summary as JSON.")
    return parser


def run_from_cli(args: argparse.Namespace) -> dict[str, object]:
    """Выполнить симуляцию из аргументов CLI."""
    from .config import MissionConfig, SimulationConfig

    config = SimulationConfig(
        mission=MissionConfig(
            mission_id="ASTRALIS-CLI-DEMO",
            mission_name="ASTRALIS CLI Simulation",
            start_utc="2026-04-22T08:00:00Z",
            planned_duration_days=180,
        ),
        environment=default_environment(),
        numerical=NumericalConfig(
            internal_step_seconds=args.internal_step,
            output_step_seconds=args.output_step,
        ),
        validation=default_validation(),
        profiles=default_profiles(),
    )
    controller = SimulationController(config)
    controller.start()
    for scenario_id in args.scenario:
        controller.inject_scenario(scenario_id)
    controller.advance(args.duration_seconds)
    exported = controller.export_telemetry(format=args.format, directory=str(args.export_dir))
    summary = {
        "mission_time_seconds": controller.clock.elapsed_seconds,
        "mission_day": controller.clock.mission_day,
        "mission_phase": controller.clock.mission_phase,
        "stream_tick_counts": {
            astronaut_id: len(rows) for astronaut_id, rows in controller._stream_ticks.items()
        },
        "daily_log_counts": {
            astronaut_id: len(rows) for astronaut_id, rows in controller._daily_logs.items()
        },
        "exported_files": exported,
        "status": controller.get_state().model_dump(mode="json"),
    }
    if args.summary:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main() -> None:
    """Точка входа CLI."""
    parser = build_parser()
    args = parser.parse_args()
    run_from_cli(args)


if __name__ == "__main__":
    main()

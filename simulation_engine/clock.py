"""Миссионные часы и фазы миссии.

Часы оперируют только миссионным временем. Скорость влияет на прогресс
миссионного времени при live-воспроизведении, но не искажает уравнения.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

MISSION_SECONDS_PER_DAY: int = 86400


@dataclass
class MissionClock:
    """Миссионное время и управление скоростью."""

    start_utc: datetime
    elapsed_seconds: int = 0
    speed: float = 1.0
    paused: bool = False
    stopped: bool = False
    phase_1_end_day: int = 14
    phase_2_start_day: int = 15
    _event_queue: list[tuple[int, str]] = field(default_factory=list)

    @property
    def mission_day(self) -> int:
        """Вернуть 1-индексированный день миссии."""
        return self.elapsed_seconds // MISSION_SECONDS_PER_DAY + 1

    @property
    def mission_phase(self) -> str:
        """Вернуть текущую фазу миссии."""
        if self.mission_day <= self.phase_1_end_day:
            return "PHASE_1_ACUTE_ADAPTATION"
        return "PHASE_2_LONG_DURATION"

    @property
    def timestamp_utc(self) -> str:
        """Вернуть текущее UTC-время миссии."""
        current = self.start_utc.timestamp() + self.elapsed_seconds
        return datetime.fromtimestamp(current, tz=UTC).isoformat().replace("+00:00", "Z")

    def set_speed(self, speed: float) -> None:
        """Установить множитель скорости миссионного времени."""
        if speed <= 0.0:
            raise ValueError("speed must be positive")
        self.speed = speed

    def pause(self) -> None:
        """Поставить миссию на паузу."""
        self.paused = True

    def resume(self) -> None:
        """Возобновить миссию."""
        self.paused = False
        self.stopped = False

    def stop(self) -> None:
        """Остановить миссию."""
        self.stopped = True
        self.paused = False

    def reset(self) -> None:
        """Сбросить миссионное время."""
        self.elapsed_seconds = 0
        self.paused = False
        self.stopped = False
        self.speed = 1.0
        self._event_queue.clear()

    def advance(self, seconds: int) -> None:
        """Продвинуть миссионное время вперёд."""
        if seconds < 0:
            raise ValueError("mission time cannot move backward")
        if self.stopped:
            return
        self.elapsed_seconds += int(seconds)

    def can_accept_event(self, event_id: str) -> bool:
        """Проверить, что событие ещё не зарегистрировано."""
        return event_id not in {event[1] for event in self._event_queue}

    def register_event(self, seconds: int, event_id: str) -> None:
        """Зарегистрировать событие по миссионному времени."""
        if self.can_accept_event(event_id):
            self._event_queue.append((seconds, event_id))
            self._event_queue.sort(key=lambda item: (item[0], item[1]))

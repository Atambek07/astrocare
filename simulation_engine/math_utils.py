"""Математические утилиты гибридной симуляции.

Здесь реализованы явный Эйлер, RK4, экспоненциальная релаксация,
Ornstein-Uhlenbeck шум и безопасные ограничения. Функции чистые и
детерминированные.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T", float, int)


def clamp(value: float, bounds: tuple[float, float]) -> float:
    """Ограничить значение диапазоном."""
    lower, upper = bounds
    if value < lower:
        return lower
    if value > upper:
        return upper
    return value


def clamp_probability(value: float) -> float:
    """Ограничить вероятность диапазоном [0, 1]."""
    return clamp(value, (0.0, 1.0))


def exponential_relaxation(current: float, target: float, tau: float, dt: float) -> float:
    """Экспоненциальное приближение к целевому состоянию."""
    if tau <= 0.0:
        raise ValueError("tau must be positive")
    return current + (target - current) * (1.0 - math.exp(-dt / tau))


def euler_step(
    state: float,
    derivative: Callable[[float], float],
    dt: float,
) -> float:
    """Явный шаг Эйлера для скалярного состояния."""
    return state + derivative(state) * dt


def rk4_step(
    state: float,
    derivative: Callable[[float], float],
    dt: float,
) -> float:
    """Классический RK4 для скалярного состояния."""
    k1 = derivative(state)
    k2 = derivative(state + 0.5 * dt * k1)
    k3 = derivative(state + 0.5 * dt * k2)
    k4 = derivative(state + dt * k3)
    return state + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


@dataclass(frozen=True)
class OUProcess:
    """Дискретный Ornstein-Uhlenbeck процесс с контролируемой дисперсией."""

    theta: float
    sigma: float
    equilibrium: float = 0.0

    def step(self, current: float, dt: float, rng: random.Random) -> float:
        """Сделать один шаг процесса."""
        if dt <= 0.0:
            return current
        decay = math.exp(-self.theta * dt)
        variance = self.sigma * self.sigma * (1.0 - decay * decay) / (2.0 * self.theta) if self.theta > 0 else self.sigma * self.sigma * dt
        noise = rng.gauss(0.0, math.sqrt(max(variance, 0.0)))
        return self.equilibrium + (current - self.equilibrium) * decay + noise

    def step_to(self, current: float, target: float, dt: float, rng: random.Random) -> float:
        """Сделать шаг вокруг целевого значения."""
        shifted = current - target
        stepped = self.step(shifted, dt, rng)
        return target + stepped


def derivative_of_target_relaxation(
    current: float,
    target: float,
    tau: float,
) -> Callable[[float], float]:
    """Получить производную релаксации к целевому состоянию."""
    def derivative(state: float) -> float:
        return (target - state) / tau
    return derivative


def stable_division(numerator: float, denominator: float, epsilon: float = 1e-9) -> float:
    """Деление с защитой от деления на ноль."""
    if abs(denominator) < epsilon:
        return 0.0
    return numerator / denominator


__all__ = [
    "OUProcess",
    "clamp",
    "clamp_probability",
    "derivative_of_target_relaxation",
    "euler_step",
    "exponential_relaxation",
    "rk4_step",
    "stable_division",
]

from __future__ import annotations

from abc import ABC, abstractmethod


class DesiredSpendCurve(ABC):
    @abstractmethod
    def target_fraction(self, minute_of_day: int) -> float:
        raise NotImplementedError

    def target_spend(self, minute_of_day: int, budget_amount: float) -> float:
        return self.target_fraction(minute_of_day) * budget_amount


class UniformSpendCurve(DesiredSpendCurve):
    def target_fraction(self, minute_of_day: int) -> float:
        minute = min(max(int(minute_of_day), 0), 1440)
        return minute / 1440.0


class FrontLoadedSpendCurve(DesiredSpendCurve):
    def __init__(self, frontload_power: float = 0.75):
        if frontload_power <= 0:
            raise ValueError("frontload_power must be positive")
        self.frontload_power = frontload_power

    def target_fraction(self, minute_of_day: int) -> float:
        minute = min(max(int(minute_of_day), 0), 1440)
        x = minute / 1440.0
        return x ** self.frontload_power

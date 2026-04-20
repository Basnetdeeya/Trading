"""Misc helpers."""
from __future__ import annotations

import math
from typing import Iterable, List


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def safe_div(a: float, b: float, default: float = 0.0) -> float:
    if b == 0 or math.isnan(b):
        return default
    return a / b


def rolling(seq: List[float], n: int) -> Iterable[List[float]]:
    for i in range(n, len(seq) + 1):
        yield seq[i - n : i]

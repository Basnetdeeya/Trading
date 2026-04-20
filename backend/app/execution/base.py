"""Broker interface."""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.types import Order


class Broker(ABC):
    name: str = "base"

    @abstractmethod
    async def place(self, order: Order) -> Order: ...

    async def close(self) -> None:
        return None

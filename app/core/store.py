from __future__ import annotations

import asyncio

from app.core.models import ServiceStatus, SystemHealth


class HealthStore:
    def __init__(self) -> None:
        self._statuses: dict[str, ServiceStatus] = {}
        self._system: SystemHealth | None = None
        self._lock = asyncio.Lock()

    async def update(
        self,
        statuses: dict[str, ServiceStatus],
        system: SystemHealth,
    ) -> None:
        async with self._lock:
            self._statuses = statuses
            self._system = system

    async def get_all(self) -> dict[str, ServiceStatus]:
        async with self._lock:
            return dict(self._statuses)

    async def get(self, name: str) -> ServiceStatus | None:
        async with self._lock:
            return self._statuses.get(name)

    async def get_system(self) -> SystemHealth | None:
        async with self._lock:
            return self._system

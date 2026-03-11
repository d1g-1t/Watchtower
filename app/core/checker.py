from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

import httpx

from app.core.models import HealthStatus, ServiceConfig, ServiceStatus


class HealthChecker:
    def __init__(self, client: httpx.AsyncClient, services: list[ServiceConfig]):
        self._client = client
        self._services = {s.name: s for s in services}

    async def check_all(self) -> dict[str, ServiceStatus]:
        return await self.check_services(list(self._services.values()))

    async def check_services(
        self, services: list[ServiceConfig]
    ) -> dict[str, ServiceStatus]:
        tasks = [self._check_one(svc) for svc in services]
        results = await asyncio.gather(*tasks)
        return {r.name: r for r in results}

    async def _check_one(self, service: ServiceConfig) -> ServiceStatus:
        start = time.monotonic()
        try:
            response = await self._client.get(
                service.url, timeout=service.timeout
            )
            latency_ms = (time.monotonic() - start) * 1000
            is_healthy = response.status_code == service.expected_status

            details: dict = {}
            try:
                body = response.json()
                if isinstance(body, dict):
                    details = body
            except Exception:
                pass

            return ServiceStatus(
                name=service.name,
                status=HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY,
                latency_ms=round(latency_ms, 2),
                status_code=response.status_code,
                details=details,
                checked_at=datetime.now(timezone.utc),
            )
        except httpx.TimeoutException:
            return ServiceStatus(
                name=service.name,
                status=HealthStatus.UNHEALTHY,
                latency_ms=round(service.timeout * 1000, 2),
                checked_at=datetime.now(timezone.utc),
                error="timeout",
            )
        except Exception as exc:
            return ServiceStatus(
                name=service.name,
                status=HealthStatus.UNHEALTHY,
                checked_at=datetime.now(timezone.utc),
                error=str(exc),
            )

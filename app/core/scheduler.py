from __future__ import annotations

import asyncio
import logging
import time

from app.core.checker import HealthChecker
from app.core.graph import DependencyGraph
from app.core.models import ServiceConfig, ServiceStatus
from app.core.store import HealthStore
from app.exporters.prometheus import PrometheusExporter
from app.exporters.slack import SlackAlerter

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(
        self,
        checker: HealthChecker,
        graph: DependencyGraph,
        store: HealthStore,
        prometheus: PrometheusExporter,
        slack: SlackAlerter,
        services: list[ServiceConfig],
    ) -> None:
        self._checker = checker
        self._graph = graph
        self._store = store
        self._prometheus = prometheus
        self._slack = slack
        self._services = services
        self._raw_statuses: dict[str, ServiceStatus] = {}
        self._last_checked: dict[str, float] = {}
        self._stop = asyncio.Event()
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._task = asyncio.create_task(self._loop())
        logger.info("scheduler started")

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            await self._task
        logger.info("scheduler stopped")

    async def _loop(self) -> None:
        while not self._stop.is_set():
            now = time.monotonic()
            due = [
                svc
                for svc in self._services
                if now - self._last_checked.get(svc.name, 0) >= svc.interval
            ]

            if due:
                try:
                    results = await self._checker.check_services(due)
                    for svc in due:
                        self._last_checked[svc.name] = now

                    self._raw_statuses.update(results)
                    transitive = self._graph.compute_transitive_health(
                        self._raw_statuses
                    )
                    system = self._graph.compute_system_health(transitive)

                    await self._store.update(transitive, system)
                    self._prometheus.update(transitive, system)
                    await self._slack.notify_if_needed(transitive, system)

                    logger.info(
                        "check: %d healthy / %d degraded / %d unhealthy",
                        system.healthy,
                        system.degraded,
                        system.unhealthy,
                    )
                except Exception:
                    logger.exception("health check cycle failed")

            try:
                await asyncio.wait_for(self._stop.wait(), timeout=1.0)
                break
            except asyncio.TimeoutError:
                pass

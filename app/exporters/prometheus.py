from __future__ import annotations

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.responses import Response

from app.core.models import ServiceConfig, ServiceStatus, SystemHealth

SERVICE_UP = Gauge(
    "watchtower_service_up",
    "Service health: 1=healthy, 0.5=degraded, 0=unhealthy",
    ["service_name", "critical"],
)

SERVICE_LATENCY = Histogram(
    "watchtower_health_check_latency_ms",
    "Health check latency in milliseconds",
    ["service_name"],
    buckets=[10, 50, 100, 250, 500, 1000, 2500, 5000],
)

SYSTEM_HEALTH = Gauge(
    "watchtower_system_health",
    "Overall system health: 1=healthy, 0.5=degraded, 0=unhealthy",
)

CHECK_TOTAL = Counter(
    "watchtower_checks_total",
    "Total health checks executed",
    ["service_name", "result"],
)

_STATUS_VALUES = {"healthy": 1.0, "degraded": 0.5, "unhealthy": 0.0}


class PrometheusExporter:
    def __init__(self, services: list[ServiceConfig]) -> None:
        self._configs = {s.name: s for s in services}

    def update(
        self,
        statuses: dict[str, ServiceStatus],
        system: SystemHealth,
    ) -> None:
        for name, status in statuses.items():
            cfg = self._configs.get(name)
            critical = str(cfg.critical).lower() if cfg else "false"
            SERVICE_UP.labels(
                service_name=name, critical=critical
            ).set(_STATUS_VALUES.get(status.status.value, 0.0))

            if status.latency_ms is not None:
                SERVICE_LATENCY.labels(service_name=name).observe(
                    status.latency_ms
                )

            CHECK_TOTAL.labels(
                service_name=name, result=status.status.value
            ).inc()

        SYSTEM_HEALTH.set(_STATUS_VALUES.get(system.status.value, 0.0))


def metrics_response() -> Response:
    return Response(
        content=generate_latest(), media_type=CONTENT_TYPE_LATEST
    )

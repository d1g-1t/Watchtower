from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ServiceConfig(BaseModel):
    name: str
    url: str
    timeout: float = 5.0
    interval: float = 30.0
    critical: bool = False
    depends_on: list[str] = []
    expected_status: int = 200


class ServiceStatus(BaseModel):
    name: str
    status: HealthStatus
    latency_ms: float | None = None
    status_code: int | None = None
    details: dict[str, Any] = {}
    checked_at: datetime
    error: str | None = None
    degraded_by: str | None = None


class SystemHealth(BaseModel):
    status: HealthStatus
    healthy: int
    degraded: int
    unhealthy: int
    total: int

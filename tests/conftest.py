import pytest
from datetime import datetime, timezone

from app.core.models import HealthStatus, ServiceConfig, ServiceStatus


@pytest.fixture
def sample_configs():
    return [
        ServiceConfig(name="db", url="http://db:8000/health", critical=True),
        ServiceConfig(name="cache", url="http://cache:8000/health", critical=True),
        ServiceConfig(
            name="api",
            url="http://api:8000/health",
            critical=True,
            depends_on=["db", "cache"],
        ),
        ServiceConfig(
            name="worker",
            url="http://worker:8000/health",
            critical=False,
            depends_on=["db", "api"],
        ),
    ]


@pytest.fixture
def healthy_statuses():
    now = datetime.now(timezone.utc)
    names = ["db", "cache", "api", "worker"]
    return {
        n: ServiceStatus(
            name=n,
            status=HealthStatus.HEALTHY,
            latency_ms=5.0,
            status_code=200,
            details={},
            checked_at=now,
        )
        for n in names
    }

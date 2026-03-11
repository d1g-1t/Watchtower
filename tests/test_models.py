from datetime import datetime, timezone

from app.core.models import HealthStatus, ServiceConfig, ServiceStatus, SystemHealth


def test_health_status_values():
    assert HealthStatus.HEALTHY == "healthy"
    assert HealthStatus.DEGRADED == "degraded"
    assert HealthStatus.UNHEALTHY == "unhealthy"


def test_service_config_defaults():
    cfg = ServiceConfig(name="test", url="http://test/health")
    assert cfg.timeout == 5.0
    assert cfg.interval == 30.0
    assert cfg.critical is False
    assert cfg.depends_on == []
    assert cfg.expected_status == 200


def test_service_config_custom():
    cfg = ServiceConfig(
        name="stripe",
        url="http://stripe/health",
        timeout=10,
        interval=60,
        critical=False,
        depends_on=["db"],
        expected_status=401,
    )
    assert cfg.expected_status == 401
    assert cfg.depends_on == ["db"]


def test_service_status_creation():
    status = ServiceStatus(
        name="test",
        status=HealthStatus.HEALTHY,
        latency_ms=42.0,
        status_code=200,
        details={"version": "1.0"},
        checked_at=datetime.now(timezone.utc),
    )
    assert status.name == "test"
    assert status.error is None
    assert status.degraded_by is None


def test_service_status_with_error():
    status = ServiceStatus(
        name="broken",
        status=HealthStatus.UNHEALTHY,
        checked_at=datetime.now(timezone.utc),
        error="timeout",
    )
    assert status.latency_ms is None
    assert status.status_code is None
    assert status.error == "timeout"


def test_system_health():
    health = SystemHealth(
        status=HealthStatus.HEALTHY,
        healthy=4,
        degraded=0,
        unhealthy=0,
        total=4,
    )
    assert health.status == HealthStatus.HEALTHY
    assert health.total == 4

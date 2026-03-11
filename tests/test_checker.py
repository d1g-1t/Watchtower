import httpx

from app.core.checker import HealthChecker
from app.core.models import HealthStatus, ServiceConfig


def _mock_transport(responses: dict):
    def handler(request: httpx.Request) -> httpx.Response:
        for pattern, (code, body) in responses.items():
            if pattern in str(request.url):
                return httpx.Response(code, json=body)
        return httpx.Response(503)

    return httpx.MockTransport(handler)


async def test_check_healthy():
    transport = _mock_transport({"ok-svc": (200, {"status": "ok"})})
    client = httpx.AsyncClient(transport=transport)
    cfg = ServiceConfig(name="ok-svc", url="http://ok-svc/health", timeout=2)
    checker = HealthChecker(client, [cfg])

    result = await checker.check_all()

    assert "ok-svc" in result
    assert result["ok-svc"].status == HealthStatus.HEALTHY
    assert result["ok-svc"].latency_ms is not None
    assert result["ok-svc"].status_code == 200
    await client.aclose()


async def test_check_unhealthy():
    transport = _mock_transport({"bad-svc": (503, {"status": "error"})})
    client = httpx.AsyncClient(transport=transport)
    cfg = ServiceConfig(name="bad-svc", url="http://bad-svc/health", timeout=2)
    checker = HealthChecker(client, [cfg])

    result = await checker.check_all()

    assert result["bad-svc"].status == HealthStatus.UNHEALTHY
    assert result["bad-svc"].status_code == 503
    await client.aclose()


async def test_check_custom_expected_status():
    transport = _mock_transport({"stripe": (401, {})})
    client = httpx.AsyncClient(transport=transport)
    cfg = ServiceConfig(
        name="stripe", url="http://stripe/health", expected_status=401
    )
    checker = HealthChecker(client, [cfg])

    result = await checker.check_all()

    assert result["stripe"].status == HealthStatus.HEALTHY
    await client.aclose()


async def test_check_parallel():
    transport = _mock_transport(
        {
            "svc-a": (200, {"status": "ok"}),
            "svc-b": (503, {"status": "error"}),
        }
    )
    client = httpx.AsyncClient(transport=transport)
    configs = [
        ServiceConfig(name="svc-a", url="http://svc-a/health"),
        ServiceConfig(name="svc-b", url="http://svc-b/health"),
    ]
    checker = HealthChecker(client, configs)

    result = await checker.check_all()

    assert len(result) == 2
    assert result["svc-a"].status == HealthStatus.HEALTHY
    assert result["svc-b"].status == HealthStatus.UNHEALTHY
    await client.aclose()


async def test_check_connection_error():
    def failing_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    transport = httpx.MockTransport(failing_handler)
    client = httpx.AsyncClient(transport=transport)
    cfg = ServiceConfig(name="dead", url="http://dead/health", timeout=1)
    checker = HealthChecker(client, [cfg])

    result = await checker.check_all()

    assert result["dead"].status == HealthStatus.UNHEALTHY
    assert result["dead"].error is not None
    await client.aclose()


async def test_check_parses_json_details():
    transport = _mock_transport(
        {"detail-svc": (200, {"status": "ok", "version": "2.1", "db": "connected"})}
    )
    client = httpx.AsyncClient(transport=transport)
    cfg = ServiceConfig(name="detail-svc", url="http://detail-svc/health")
    checker = HealthChecker(client, [cfg])

    result = await checker.check_all()

    assert result["detail-svc"].details["version"] == "2.1"
    assert result["detail-svc"].details["db"] == "connected"
    await client.aclose()

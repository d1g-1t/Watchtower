# Watchtower

Health Check Aggregator with transitive dependency graph.

Polls your services, builds a dependency graph, and figures out who's *actually* broken — not just who says they're fine while their database is on fire.

If service A depends on B, and B is dead — A is degraded. Automatically. No config magic, just a YAML file and `networkx`.

## Quick Start

```bash
make setup
```

That's it. Open:

| Service    | URL                          | Credentials          |
|------------|------------------------------|----------------------|
| API        | http://localhost:29710       | —                    |
| Prometheus | http://localhost:29711       | —                    |
| Grafana    | http://localhost:29712       | admin / watchtower   |

## API

```
GET /                          → service info
GET /health/system             → 200 if healthy, 503 if not
GET /health/services           → all services with transitive status
GET /health/services/{name}    → single service
GET /health/graph              → dependency graph (nodes + edges)
GET /metrics                   → prometheus scrape endpoint
```

### Example: system health

```bash
curl -s http://localhost:29710/health/system | python -m json.tool
```

```json
{
    "status": "degraded",
    "healthy": 5,
    "degraded": 1,
    "unhealthy": 1,
    "total": 7
}
```

Returns `503` when critical services are down. Use it as a liveness probe for the whole system.

## How It Works

```
services.yaml
     │
     ▼
 Scheduler (per-service intervals)
     │
     ▼
 HealthChecker.check_all()       ← parallel asyncio.gather
     │
     ▼
 DependencyGraph                 ← networkx DiGraph
   ├── compute_transitive_health()   unhealthy deps → DEGRADED
   └── compute_system_health()       critical services → overall status
     │
     ├── HealthStore             ← in-memory, async-safe
     ├── Prometheus Exporter     ← watchtower_service_up, latency histograms
     └── Slack Alerter           ← with cooldown dedup
```

### Transitive Health

Standard `/health` is useless in microservices. Service says `200 OK` while its DB is dead.

```
Without Watchtower:           With Watchtower:

PaymentAPI     → ✅            PaymentAPI     → ⚠️ DEGRADED
DatabaseService → ❌            DatabaseService → ❌ DOWN
OrderAPI       → ✅            OrderAPI       → ⚠️ DEGRADED (depends on Payment)
NotifyAPI      → ✅            NotifyAPI      → ✅ HEALTHY
```

## Configuration

All services declared in `app/config/services.yaml`:

```yaml
services:
  - name: auth-service
    url: http://auth:8001/health
    timeout: 3
    interval: 15
    critical: true
    depends_on:
      - postgresql
      - redis
```

| Field           | Default | Description                              |
|-----------------|---------|------------------------------------------|
| `name`          | —       | unique service identifier                |
| `url`           | —       | health endpoint URL                      |
| `timeout`       | 5       | request timeout in seconds               |
| `interval`      | 30      | polling interval in seconds              |
| `critical`      | false   | if down, entire system is unhealthy      |
| `depends_on`    | []      | upstream dependencies                    |
| `expected_status`| 200    | HTTP status code that means "healthy"    |

### Environment Variables

```
WT_CONFIG_PATH             path to services.yaml
WT_SLACK_WEBHOOK_URL       slack incoming webhook (optional)
WT_SLACK_COOLDOWN_MINUTES  dedup window (default: 15)
WT_LOG_LEVEL               INFO / DEBUG / WARNING
```

## Demo Setup

The included `docker-compose.yml` runs 7 mock services, Watchtower, Prometheus, and Grafana.

`payment-service` is configured as **flaky** (30% failure rate) to demonstrate transitive degradation: when payment goes down, `order-service` (which depends on it) gets marked `DEGRADED` automatically.

```
make setup     # build & start everything
make logs      # follow watchtower logs
make status    # quick health check
make down      # tear down
make restart   # restart watchtower only
```

## Project Structure

```
├── app/
│   ├── main.py                  FastAPI app + routes
│   ├── settings.py              pydantic-settings config
│   ├── core/
│   │   ├── models.py            ServiceConfig, ServiceStatus, SystemHealth
│   │   ├── checker.py           parallel health checker (httpx + asyncio)
│   │   ├── graph.py             networkx dependency graph + transitive health
│   │   ├── store.py             async-safe in-memory store
│   │   └── scheduler.py         per-service interval polling loop
│   ├── exporters/
│   │   ├── prometheus.py        gauges, histograms, counters
│   │   └── slack.py             alerts with cooldown deduplication
│   └── config/
│       └── services.yaml        service declarations
├── mock/                        configurable mock service for demo
├── tests/                       pytest + pytest-asyncio
├── prometheus/                  prometheus.yml
├── grafana/                     pre-provisioned dashboard
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── Makefile
```

## Stack

- **FastAPI** — async HTTP server
- **httpx** — async HTTP client with connection pooling
- **networkx** — directed graph for dependency modeling
- **pydantic v2** — data validation and serialization
- **prometheus-client** — metrics export
- **Grafana** — pre-configured dashboard out of the box

## Tests

```bash
pip install -e ".[dev]"
pytest -v
```

## License

MIT

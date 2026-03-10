from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import yaml
from fastapi import FastAPI, HTTPException, Request
from starlette.responses import Response

from app.core.checker import HealthChecker
from app.core.graph import DependencyGraph
from app.core.models import ServiceConfig
from app.core.scheduler import Scheduler
from app.core.store import HealthStore
from app.exporters.prometheus import PrometheusExporter, metrics_response
from app.exporters.slack import SlackAlerter
from app.settings import Settings

settings = Settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)


def _load_services(path: str) -> list[ServiceConfig]:
    raw = yaml.safe_load(Path(path).read_text())
    return [ServiceConfig(**s) for s in raw["services"]]


@asynccontextmanager
async def lifespan(app: FastAPI):
    services = _load_services(settings.config_path)

    client = httpx.AsyncClient()
    checker = HealthChecker(client, services)
    graph = DependencyGraph(services)
    store = HealthStore()
    prometheus = PrometheusExporter(services)
    slack = SlackAlerter(
        settings.slack_webhook_url, settings.slack_cooldown_minutes
    )

    scheduler = Scheduler(
        checker, graph, store, prometheus, slack, services
    )
    await scheduler.start()

    app.state.store = store
    app.state.graph = graph

    yield

    await scheduler.stop()
    await client.aclose()


app = FastAPI(title="Watchtower", lifespan=lifespan)


@app.get("/")
async def root():
    return {
        "service": "watchtower",
        "version": "1.0.0",
        "endpoints": [
            "/health/system",
            "/health/services",
            "/health/services/{name}",
            "/health/graph",
            "/metrics",
        ],
    }


@app.get("/health/system")
async def system_health(request: Request):
    store: HealthStore = request.app.state.store
    graph: DependencyGraph = request.app.state.graph

    system = await store.get_system()
    if system is None:
        return Response(
            content='{"status":"starting","detail":"no checks completed yet"}',
            status_code=503,
            media_type="application/json",
        )

    code = 200 if system.status.value == "healthy" else 503
    return Response(
        content=system.model_dump_json(),
        status_code=code,
        media_type="application/json",
    )


@app.get("/health/services")
async def all_services(request: Request):
    store: HealthStore = request.app.state.store
    return await store.get_all()


@app.get("/health/services/{service_name}")
async def one_service(service_name: str, request: Request):
    store: HealthStore = request.app.state.store
    status = await store.get(service_name)
    if status is None:
        raise HTTPException(404, f"service '{service_name}' not found")
    return status


@app.get("/health/graph")
async def dependency_graph(request: Request):
    graph: DependencyGraph = request.app.state.graph
    return graph.get_graph_data()


@app.get("/metrics")
async def prometheus_metrics():
    return metrics_response()

from __future__ import annotations

import networkx as nx

from app.core.models import HealthStatus, ServiceConfig, ServiceStatus, SystemHealth


class DependencyGraph:
    def __init__(self, services: list[ServiceConfig]):
        self._graph = nx.DiGraph()
        self._configs = {s.name: s for s in services}
        self._build(services)

    def _build(self, services: list[ServiceConfig]) -> None:
        for svc in services:
            self._graph.add_node(svc.name)
            for dep in svc.depends_on:
                self._graph.add_edge(dep, svc.name)

    def compute_transitive_health(
        self, raw_statuses: dict[str, ServiceStatus]
    ) -> dict[str, ServiceStatus]:
        result = dict(raw_statuses)

        unhealthy = {
            name
            for name, status in raw_statuses.items()
            if status.status == HealthStatus.UNHEALTHY
        }

        for failed in unhealthy:
            if failed not in self._graph:
                continue
            for affected in nx.descendants(self._graph, failed):
                if affected not in result:
                    continue
                current = result[affected]
                if current.status == HealthStatus.HEALTHY:
                    result[affected] = current.model_copy(
                        update={
                            "status": HealthStatus.DEGRADED,
                            "degraded_by": failed,
                            "details": {
                                **current.details,
                                "degraded_because": f"dependency '{failed}' is down",
                            },
                        }
                    )

        return result

    def compute_system_health(
        self, statuses: dict[str, ServiceStatus]
    ) -> SystemHealth:
        critical = {
            name for name, cfg in self._configs.items() if cfg.critical
        }

        has_critical_down = any(
            statuses[name].status
            in (HealthStatus.UNHEALTHY, HealthStatus.DEGRADED)
            for name in critical
            if name in statuses
        )

        total = len(statuses)
        healthy = sum(
            1 for s in statuses.values() if s.status == HealthStatus.HEALTHY
        )
        degraded = sum(
            1 for s in statuses.values() if s.status == HealthStatus.DEGRADED
        )
        unhealthy_count = sum(
            1 for s in statuses.values() if s.status == HealthStatus.UNHEALTHY
        )

        if has_critical_down:
            overall = HealthStatus.UNHEALTHY
        elif healthy == total:
            overall = HealthStatus.HEALTHY
        else:
            overall = HealthStatus.DEGRADED

        return SystemHealth(
            status=overall,
            healthy=healthy,
            degraded=degraded,
            unhealthy=unhealthy_count,
            total=total,
        )

    def get_graph_data(self) -> dict:
        return {
            "nodes": [
                {
                    "id": n,
                    "critical": self._configs[n].critical
                    if n in self._configs
                    else False,
                }
                for n in self._graph.nodes
            ],
            "edges": [
                {"from": u, "to": v, "label": "depends_on"}
                for u, v in self._graph.edges
            ],
        }

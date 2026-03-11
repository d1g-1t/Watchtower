from app.core.graph import DependencyGraph
from app.core.models import HealthStatus


class TestTransitiveHealth:
    def test_all_healthy(self, sample_configs, healthy_statuses):
        graph = DependencyGraph(sample_configs)
        result = graph.compute_transitive_health(healthy_statuses)
        assert all(s.status == HealthStatus.HEALTHY for s in result.values())

    def test_db_down_degrades_dependents(self, sample_configs, healthy_statuses):
        graph = DependencyGraph(sample_configs)
        healthy_statuses["db"] = healthy_statuses["db"].model_copy(
            update={"status": HealthStatus.UNHEALTHY, "error": "timeout"}
        )

        result = graph.compute_transitive_health(healthy_statuses)

        assert result["db"].status == HealthStatus.UNHEALTHY
        assert result["api"].status == HealthStatus.DEGRADED
        assert result["api"].degraded_by == "db"
        assert result["worker"].status == HealthStatus.DEGRADED
        assert result["cache"].status == HealthStatus.HEALTHY

    def test_cache_down_degrades_api_and_worker(self, sample_configs, healthy_statuses):
        graph = DependencyGraph(sample_configs)
        healthy_statuses["cache"] = healthy_statuses["cache"].model_copy(
            update={"status": HealthStatus.UNHEALTHY}
        )

        result = graph.compute_transitive_health(healthy_statuses)

        assert result["cache"].status == HealthStatus.UNHEALTHY
        assert result["api"].status == HealthStatus.DEGRADED
        assert result["worker"].status == HealthStatus.DEGRADED
        assert result["db"].status == HealthStatus.HEALTHY

    def test_leaf_down_no_cascade(self, sample_configs, healthy_statuses):
        graph = DependencyGraph(sample_configs)
        healthy_statuses["worker"] = healthy_statuses["worker"].model_copy(
            update={"status": HealthStatus.UNHEALTHY}
        )

        result = graph.compute_transitive_health(healthy_statuses)

        assert result["worker"].status == HealthStatus.UNHEALTHY
        assert result["db"].status == HealthStatus.HEALTHY
        assert result["api"].status == HealthStatus.HEALTHY
        assert result["cache"].status == HealthStatus.HEALTHY

    def test_degraded_details_include_reason(self, sample_configs, healthy_statuses):
        graph = DependencyGraph(sample_configs)
        healthy_statuses["db"] = healthy_statuses["db"].model_copy(
            update={"status": HealthStatus.UNHEALTHY}
        )

        result = graph.compute_transitive_health(healthy_statuses)

        assert "degraded_because" in result["api"].details
        assert "db" in result["api"].details["degraded_because"]


class TestSystemHealth:
    def test_all_healthy(self, sample_configs, healthy_statuses):
        graph = DependencyGraph(sample_configs)
        system = graph.compute_system_health(healthy_statuses)
        assert system.status == HealthStatus.HEALTHY
        assert system.healthy == 4
        assert system.total == 4

    def test_critical_down(self, sample_configs, healthy_statuses):
        graph = DependencyGraph(sample_configs)
        healthy_statuses["db"] = healthy_statuses["db"].model_copy(
            update={"status": HealthStatus.UNHEALTHY}
        )
        system = graph.compute_system_health(healthy_statuses)
        assert system.status == HealthStatus.UNHEALTHY

    def test_non_critical_down_degrades(self, sample_configs, healthy_statuses):
        graph = DependencyGraph(sample_configs)
        healthy_statuses["worker"] = healthy_statuses["worker"].model_copy(
            update={"status": HealthStatus.UNHEALTHY}
        )
        system = graph.compute_system_health(healthy_statuses)
        assert system.status == HealthStatus.DEGRADED

    def test_counts(self, sample_configs, healthy_statuses):
        graph = DependencyGraph(sample_configs)
        healthy_statuses["db"] = healthy_statuses["db"].model_copy(
            update={"status": HealthStatus.UNHEALTHY}
        )
        healthy_statuses["api"] = healthy_statuses["api"].model_copy(
            update={"status": HealthStatus.DEGRADED}
        )
        system = graph.compute_system_health(healthy_statuses)
        assert system.unhealthy == 1
        assert system.degraded == 1
        assert system.healthy == 2


class TestGraphData:
    def test_nodes_and_edges(self, sample_configs):
        graph = DependencyGraph(sample_configs)
        data = graph.get_graph_data()

        node_ids = {n["id"] for n in data["nodes"]}
        assert node_ids == {"db", "cache", "api", "worker"}

        assert len(data["edges"]) == 4

        critical_nodes = {n["id"] for n in data["nodes"] if n["critical"]}
        assert critical_nodes == {"db", "cache", "api"}

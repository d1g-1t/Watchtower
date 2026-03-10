.PHONY: setup down logs test status restart

setup:
	docker compose up --build -d
	@echo.
	@echo === Watchtower is running ===
	@echo.
	@echo   API:        http://localhost:29710
	@echo   Prometheus: http://localhost:29711
	@echo   Grafana:    http://localhost:29712  (admin / watchtower)
	@echo.
	@echo Try:
	@echo   curl http://localhost:29710/health/system
	@echo   curl http://localhost:29710/health/services
	@echo   curl http://localhost:29710/health/graph
	@echo   curl http://localhost:29710/metrics

down:
	docker compose down -v

logs:
	docker compose logs -f watchtower

test:
	pytest tests/ -v --tb=short

status:
	@curl -s http://localhost:29710/health/system 2>NUL || echo Not running

restart:
	docker compose restart watchtower

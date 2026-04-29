.PHONY: proxy docker-build docker-up docker-down docker-shell run-local help start-all stop-all migrate migrate-history migrate-stamp

help:
	@echo "Meal Planner Commands:"
	@echo "  make proxy        - Start the reminders proxy server (run on Mac)"
	@echo "  make docker-build - Build the Docker image"
	@echo "  make docker-up    - Start the Docker container"
	@echo "  make docker-down  - Stop the Docker container"
	@echo "  make docker-shell - Exec into the running container"
	@echo "  make run-local    - Run the meal planner locally (no Docker)"
	@echo "  make start-all    - Start proxy and all Docker containers (backend + frontend)"
	@echo "  make stop-all     - Stop proxy and all Docker containers"
	@echo "  make migrate       - Run pending database migrations (alembic upgrade head)"
	@echo "  make migrate-history - Show migration history"
	@echo "  make migrate-stamp - Stamp existing DB as initial schema (run once on pre-alembic DBs)"
	@echo ""
	@echo "Typical Docker workflow:"
	@echo "  1. make proxy        (in one terminal)"
	@echo "  2. make docker-up    (in another terminal)"
	@echo "  3. make docker-shell"
	@echo "  4. python backend/agent/meal_planner.py"

proxy:
	cd backend && python3 -m reminders.server

docker-build:
	cd docker && docker compose --env-file ../.env build

docker-up: docker-build
	cd docker && docker compose --env-file ../.env up -d

docker-down:
	cd docker && docker compose --env-file ../.env down

docker-shell:
	docker exec -it meal-planner bash

run-local:
	python3 backend/meal_planner.py

start-all: docker-build
	@echo "Starting proxy server in background..."
	cd backend && nohup python3 -m reminders.server > ../proxy.log 2>&1 & echo $$! > ../.proxy.pid
	@sleep 1
	@echo "Starting Docker containers..."
	cd docker && docker compose --env-file ../.env up -d
	@echo "All services started. Log: proxy.log. Use 'make stop-all' to stop."

migrate:
	docker exec meal-planner bash -c "cd /app/backend && alembic upgrade head"

migrate-history:
	docker exec meal-planner bash -c "cd /app/backend && alembic history"

migrate-stamp:
	@echo "Stamping existing DB as initial schema (run once on pre-alembic databases)..."
	docker exec meal-planner bash -c "cd /app/backend && alembic stamp 001"

stop-all:
	@echo "Stopping Docker containers..."
	-cd docker && docker compose --env-file ../.env down
	@echo "Stopping proxy server..."
	-@if [ -f .proxy.pid ]; then kill $$(cat .proxy.pid) 2>/dev/null; rm .proxy.pid; fi
	-@pkill -f "reminders.server" 2>/dev/null || true
	@echo "All services stopped."

.PHONY: proxy docker-build docker-up docker-down docker-shell run-local help start-all stop-all

help:
	@echo "Meal Planner Commands:"
	@echo "  make proxy        - Start the reminders proxy server (run on Mac)"
	@echo "  make docker-build - Build the Docker image"
	@echo "  make docker-up    - Start the Docker container"
	@echo "  make docker-down  - Stop the Docker container"
	@echo "  make docker-shell - Exec into the running container"
	@echo "  make run-local    - Run the meal planner locally (no Docker)"
	@echo "  make start-all    - Start proxy, Docker container, and frontend"
	@echo "  make stop-all     - Stop proxy, Docker container, and frontend"
	@echo ""
	@echo "Typical Docker workflow:"
	@echo "  1. make proxy        (in one terminal)"
	@echo "  2. make docker-up    (in another terminal)"
	@echo "  3. make docker-shell"
	@echo "  4. python src/meal_planner.py"

proxy:
	cd src && python3 reminders_server.py

docker-build:
	cd docker && docker compose build

docker-up: docker-build
	cd docker && docker compose up -d

docker-down:
	cd docker && docker compose down

docker-shell:
	docker exec -it meal-planner bash

run-local:
	python3 src/meal_planner.py

start-all: docker-build
	@echo "Starting proxy server in background..."
	cd src && nohup python3 reminders_server.py > ../proxy.log 2>&1 & echo $$! > ../.proxy.pid
	@sleep 1
	@echo "Starting Docker container..."
	cd docker && docker compose up -d
	@echo "Starting frontend in background..."
	cd frontend && nohup npm run dev > ../frontend.log 2>&1 & echo $$! > ../.frontend.pid
	@echo "All services started. Logs: proxy.log, frontend.log. Use 'make stop-all' to stop."

stop-all:
	@echo "Stopping Docker container..."
	-cd docker && docker compose down
	@echo "Stopping proxy server..."
	-@if [ -f .proxy.pid ]; then kill $$(cat .proxy.pid) 2>/dev/null; rm .proxy.pid; fi
	-@pkill -f "python3 reminders_server.py" 2>/dev/null || true
	@echo "Stopping frontend..."
	-@if [ -f .frontend.pid ]; then kill $$(cat .frontend.pid) 2>/dev/null; rm .frontend.pid; fi
	-@pkill -f "vite" 2>/dev/null || true
	@echo "All services stopped."

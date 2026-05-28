.PHONY: help build up down logs test clean restart shell health

# Default target
help:
	@echo "Available targets:"
	@echo "  build      - Build Docker image"
	@echo "  up         - Start services in detached mode"
	@echo "  down       - Stop and remove containers"
	@echo "  logs       - Follow service logs"
	@echo "  test       - Run tests in container"
	@echo "  clean      - Remove containers, images, and volumes"
	@echo "  restart    - Restart services"
	@echo "  shell      - Open shell in running container"
	@echo "  health     - Check service health"

# Build the Docker image
build:
	docker-compose build

# Start services in detached mode
up:
	docker-compose up -d

# Build and start
up-build:
	docker-compose up -d --build

# Stop and remove containers
down:
	docker-compose down

# Follow logs
logs:
	docker-compose logs -f ads-api

# Restart services
restart: down up

# Run tests in container
test:
	docker-compose run --rm ads-api pytest -v

# Clean up everything
clean:
	docker-compose down -v --rmi all

# Open bash shell in running container
shell:
	docker exec -it ads-decision-api bash

# Check health endpoint
health:
	@curl -s http://localhost:8000/health | python -m json.tool || echo "Service not responding"

# Quick development workflow: rebuild and restart
dev: down up-build logs

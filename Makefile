.PHONY: help build up down logs shell test clean migrate seed

# Default target
help:
	@echo "Available commands:"
	@echo "  build     - Build the Docker image"
	@echo "  up        - Start all services"
	@echo "  down      - Stop all services"
	@echo "  logs      - Show logs for all services"
	@echo "  logs-api  - Show logs for API service only"
	@echo "  shell     - Open shell in API container"
	@echo "  test      - Run tests in container"
	@echo "  migrate   - Run database migrations"
	@echo "  seed      - Seed database with initial data"
	@echo "  clean     - Remove containers and volumes"
	@echo "  prod-up   - Start production services"
	@echo "  prod-down - Stop production services"

# Development commands
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

logs-api:
	docker-compose logs -f api

shell:
	docker-compose exec api bash

test:
	docker-compose exec api pytest tests/ -v

migrate:
	docker-compose exec api alembic upgrade head

seed:
	docker-compose exec api python seed_data/seed_llm_models.py

clean:
	docker-compose down -v --remove-orphans
	docker system prune -f

# Production commands
prod-up:
	docker-compose -f docker-compose.prod.yml up --build -d

prod-down:
	docker-compose -f docker-compose.prod.yml down

prod-logs:
	docker-compose -f docker-compose.prod.yml logs -f

# Development workflow
dev-setup: build up migrate seed
	@echo "Development environment is ready!"
	@echo "API: http://localhost:8000"
	@echo "Docs: http://localhost:8000/api/v1/docs"

dev-rebuild: down build up
	@echo "Rebuilt and restarted development environment"

# Health checks
health:
	@echo "Checking API health..."
	@curl -f http://localhost:8000/ || echo "API is not responding"
	@echo "\nChecking database..."
	@docker-compose exec db pg_isready -U bitewise -d bitewise_dev || echo "Database is not ready" 
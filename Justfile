default:
    @just --list

# --- DOCKER ---
up:
    docker compose up --build

down:
    docker compose down

build:
    docker compose build backend frontend

run:
    docker compose up backend frontend

backend-ready:
    docker compose up -d --wait db backend

# --- TESTS ---
test: test-back-integration test-front

[working-directory: "backend"]
test-back:
    uv run pytest -m "not integration"

[working-directory: "backend"]
test-back-integration: backend-ready
    uv run pytest

[working-directory: "frontend"]
test-front:
    npm test

# --- LINTING AND FORMATTING ---
[working-directory: "backend"]
lint:
    uv run ruff check --fix src tests
    uv run ruff format src tests

[working-directory: "backend"]
format:
    uv run ruff format src tests

[working-directory: "frontend"]
type-check:
    npm run typecheck

# --- DATABASE MIGRATIONS ---
migration name: backend-ready
    docker compose exec backend alembic revision --autogenerate -m "{{name}}"

migrate: backend-ready
    docker compose exec backend alembic upgrade head

db-current: backend-ready
    docker compose exec backend alembic current

db-history: backend-ready
    docker compose exec backend alembic history

db-reset: backend-ready
    docker compose down -v
    docker compose up -d --wait db backend
    docker compose exec backend alembic upgrade head

[working-directory: "backend"]
db-post command: backend-ready
    uv run scripts/load_csv.py {{command}}

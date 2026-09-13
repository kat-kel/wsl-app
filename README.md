# WSL fullstack application

The repository contains two independently deployable services:

- `backend/`: FastAPI, SQLModel, Alembic, and PostgreSQL integration.
- `frontend/`: React and TypeScript, served by Nginx in production.
- `deploy/`: production Dockerfiles for both services, plus the Nginx config template used to serve the built frontend.

## Local development

Start the database, backend, and frontend together:

```sh
cp .env.example .env
just up
```

Open `http://localhost:5173` in your browser. The API is available at `http://localhost:8000` (including `GET /health`).

The root [`.env.example`](./.env.example) is the single source of truth for local environment variables:

- `DATABASE_URL` : PostgreSQL connection string used by FastAPI.
- `BACKEND_PORT` / `FRONTEND_PORT` : ports the backend and frontend containers listen on and publish to the host. `CORS_ORIGINS` and `BACKEND_URL` are derived from these directly in `compose.yaml`, not set independently.

### Host-native runs are for tests only

The dev servers (frontend and backend) always run in Docker via `compose.yaml` — there's no supported way to run them natively on the host. The only thing that runs natively is the test suite (`just test`), via [`backend/.env.example`](./backend/.env.example):

- [Backend](./backend/.env.example): loaded by `pytest` when run natively with `uv run`. It only needs `DATABASE_URL` pointed at `localhost` instead of the Compose hostname `db`, since one integration test (`test_database_connection`) needs a real Postgres connection; the rest of the suite doesn't touch the network. Copy it to `backend/.env` before running `just test-back`.
- Frontend unit tests (`vitest`) don't need any env vars — they should mock the API layer rather than depend on a live backend.

### Docker Port Mapping & Networking

Inside the container, FastAPI/Uvicorn binds to `0.0.0.0:${BACKEND_PORT:-8000}`. Docker Compose forwards traffic from your host machine to the container using `HOST:CONTAINER` port mapping in `compose.yaml`:

```yaml
services:
  backend:
    ports:
      - "${BACKEND_PORT:-8000}:${BACKEND_PORT:-8000}" # Host Port : Container Port
```

Local Postgres is the Compose `db` service (`app` / `app` / `app`). The backend container uses hostname `db` in `DATABASE_URL`. DBeaver and other host clients use `localhost:5432` with the same database, user, and password.

Run migrations from the backend container:

```sh
just migrate
```

Generate a migration after changing a model, then review the generated file before applying it:

```sh
just migration "describe the schema change"
just migrate
```

The Vite dev server is used locally for fast reloads. The production frontend image builds the React app and serves it with Nginx. The production backend is an independent FastAPI image.

## Checks

```sh
just test
just lint # backend (ruff)
just type-check # frontend (node)
just build
```

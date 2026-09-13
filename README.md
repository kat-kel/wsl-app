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
- `WRITE_API_KEYS` : required, comma-separated, each key minimum 32 characters. The set of keys the API accepts on write endpoints. The app refuses to start if it is missing or any key is too short, so a misconfigured deployment fails immediately instead of serving unauthenticated writes.

## Reads are public, writes are authenticated

`GET` endpoints are open. Every `POST` and `PUT` on `/players` and `/teams` requires an
`X-API-Key` header matching one of `WRITE_API_KEYS`, enforced by the `require_write_access`
dependency in [`backend/src/app/api/security.py`](./backend/src/app/api/security.py) and
compared with `secrets.compare_digest`.

Note that CORS is not part of this: `CORS_ORIGINS` only constrains browser JavaScript and
does nothing to a request from `curl` or a script. The API key is the actual control.

In a deployed environment `WRITE_API_KEYS` must come from a secret store (Secret Manager
injected as an env var on Cloud Run), never from a file in the repo.

Because the API accepts a *set* of keys, rotation needs no window where the server and its
clients disagree:

1. Append the new key to `WRITE_API_KEYS` and redeploy. Both keys now work.
2. Move each client to the new key (for the loader, `WRITE_API_KEY` in its environment).
3. Remove the old key from `WRITE_API_KEYS` and redeploy.

The server accepting many keys and a client sending exactly one is why the two variable
names differ — `WRITE_API_KEYS` for the API, `WRITE_API_KEY` for the loader.

## Populating the database

Schema changes ship as Alembic migrations (see below). Reference data that is effectively
immutable — the country list — is seeded inside the migration that creates its table.
Domain data that changes over time (players, teams) is loaded through the API by
`backend/scripts/load_csv.py`, a git-ignored helper that reads git-ignored CSVs from
`backend/scripts/data/`:

```sh
cd backend
uv run python scripts/load_csv.py teams
uv run python scripts/load_csv.py players
uv run python scripts/load_csv.py players -i some/other.csv   # override the default CSV
```

The script reads `WRITE_API_KEY` from `backend/.env`, so it needs no arguments in normal
use. Each subcommand defaults to its file in `backend/scripts/data/`.

Records are matched on a natural key — team code, and the player's normalized name — so
re-running updates existing rows rather than duplicating them.

To target a deployed environment, set `WSL_API_BASE` (default `http://localhost:8000`)
along with that environment's `WRITE_API_KEY`. An exported `WRITE_API_KEY` takes precedence
over the one in `backend/.env`, so the local key is never sent anywhere by accident.

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

Migrations in `alembic/versions/` are version-controlled source and must be committed and
reviewed like any other code — they are the only record of how to move a database from one
state to the next, including production.

Run migrations from the backend container:

```sh
just migrate
```

Generate a migration after changing a model, then review the generated file before applying it:

```sh
just migration "describe the schema change"
just migrate
```

CI applies migrations against a throwaway Postgres, then runs `alembic check` to prove the
models and the migration history agree, then runs `downgrade base` and `upgrade head` to
prove the migrations reverse cleanly. A model change without a matching migration fails the
build.

Production schema updates are an explicit deploy step that runs `alembic upgrade head`
before the new revision serves traffic. Do not put it in the container's start command:
with more than one instance, concurrent migration runs race each other.

The Vite dev server is used locally for fast reloads. The production frontend image builds the React app and serves it with Nginx. The production backend is an independent FastAPI image.

## Checks

```sh
just test
just lint # backend (ruff)
just type-check # frontend (node)
just build
```

# WSL fullstack application

The repository contains two independently deployable services:

- `backend/`: FastAPI, SQLModel, Alembic, and PostgreSQL integration.
- `frontend/`: React and TypeScript, served by Nginx in production.

## Local development

Start the database, backend, and frontend together:

```sh
cp .env.example .env
just up
```

Open `http://localhost:5173` in your browser. The API is available at `http://localhost:8000` (including `GET /health`).

We manage 3 URL settings:

- `DATABASE_URL` : PostgreSQL connection string used by FastAPI. When running via Docker, ensure no local processes are listening on port 5432.
- `CORS_ORIGINS` : Permitted frontend origins configured in FastAPI to allow cross-origin requests.
- `VITE_API_URL` : Backend base URL consumed by the Vite frontend.

### Multi-level `.env` hierarchy

Environment variables are defined at two distinct levels depending on whether you run services inside Docker or natively on your host machine:

- [Root Level](./.env.example): Used by Docker Compose for containerized execution. Compose injects these variables directly into the backend and frontend containers, overriding any subfolder `.env` files because both the backend and frontend privilege existing environment variables.
- [Backend](./backend/.env.example): Loaded by FastAPI when running the backend directly on your host system using Python.
- [Frontend](./frontend/.env.example): Loaded by Vite when running the frontend directly on your host system using Node.js.

### Docker Port Mapping & Networking

Inside the container, FastAPI/Uvicorn binds to `0.0.0.0:8000`. Docker Compose forwards traffic from your host machine to the container using `HOST:CONTAINER` port mapping in `compose.yaml`:

```yaml
services:
  backend:
    ports:
      - "8000:8000" # Host Port : Container Port
```

Local Postgres is the Compose `db` service (`app` / `app` / `app`). The backend container uses hostname `db` in `DATABASE_URL`. DBeaver and other host clients use `localhost:5432` with the same database, user, and password. Host-side pytest or uvicorn can copy `backend/.env.example` to `backend/.env`, which points at that published port.

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

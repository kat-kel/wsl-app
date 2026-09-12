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

Open `http://localhost:5173`. The API is available at
`http://localhost:8000`, including `GET /health`.

Compose reads the database (`DATABASE_URL`) and CORS (`CORS_ORIGINS`) from the backend's [`.env`](./backend/.env.example) file. The frontend's [`.env`](./frontend/.env.example) file injects the frontend's API URL (`VITE_API_URL`). The committed `.env.example` files contain local values only. Staging and production use the same application images with `DATABASE_URL`, `CORS_ORIGINS`, and `VITE_API_URL` supplied by their Cloud Run deployment configuration.

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

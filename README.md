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

We manage 3 URL settings:

- `DATABASE_URL` : URL to the PostgreSQL database, which the backend uses to connect to the data source. Locally, this runs in the Docker image, and you should make sure nothing else on your local environment is listening on the port you have configured in the `.env` file, i.e. `5432`.
- `CORS_ORIGINS` : URL of the CORS origin, which the backend uses to serve the API.
- `VITE_API_URL` : URL pointing to where the frontend fetches the backend.

The settings are managed multiple times, at multiple levesls, in different `.env` files.

- [root level](./.env.example) : Configuration for the containerized application, read with [compose](compose.yaml).
  - Compose injects `DATABASE_URL` and `CORS_ORIGINS` into the backend service as environment variables, overriding the [`backend/.env`](./backend/.env.example) file because the FastAPI code privileges env vars over its local `.env` file.
  - Compose injects `VITE_API_URL` into the frontend service as environment variables, overriding the [`frontend/.env`](./frontend/.env.example) file.
- [backend/](./.backend/.env.example) : Used when running the FastAPI backend outside the Docker container, with the host's Python.
- [frontend/](./.frontend/.env.example) : Used when runnig the Vite outside the Docker container, with the host's Node.

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

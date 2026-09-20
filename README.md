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

- `DATABASE_URL` : write-capable PostgreSQL connection string, on the `app_writer` role [`deploy/db-init/00-app-writer-role.sh`](./deploy/db-init/00-app-writer-role.sh) creates. Read by the Alembic migrations and the CSV load job — never by the running API process.
- `API_DATABASE_URL` : what the API actually connects with — the `api_reader` role [`deploy/db-init/01-api-reader-role.sh`](./deploy/db-init/01-api-reader-role.sh) creates, with `SELECT` only. `app/database.py` builds the API's engine from this, not `DATABASE_URL`.
- `DATA_SOURCE` : base location the load job reads CSVs from — the `fixtures/` mount locally, a `gs://` bucket prefix in a deployed environment. Only the load job reads it.
- `BACKEND_PORT` / `FRONTEND_PORT` : ports the backend and frontend containers listen on and publish to the host. `CORS_ORIGINS` and `BACKEND_URL` default from these in `compose.yaml` and only need setting independently once a service moves off localhost.
- `BACKEND_URL` : where the frontend's proxy forwards `/api`. Vite's dev server reads it locally; in the cloud image Nginx substitutes it into its config when the container starts. Application code never names the backend — [`frontend/src/api/`](./frontend/src/api/) only ever fetches the relative path `/api` — so this is the one place the address lives, and the same built image works against any backend.
The frontend's Node major is not an environment variable. It is declared twice — in [`frontend/.nvmrc`](./frontend/.nvmrc), which `nvm` and CI read, and as `ARG NODE_VERSION` in [`deploy/Dockerfile.frontend`](./deploy/Dockerfile.frontend), because `FROM` cannot read a file. CI asserts the two match, so drift fails the build rather than surfacing later as a production-only bug.

## The API is read-only

Every route is a `GET`. There are no `POST`, `PUT`, `PATCH` or `DELETE` endpoints, no
authentication layer, and no write credential anywhere in the deployment.

That is a deliberate consequence of how data gets in. The frontend only reads, and domain
data is loaded by a batch job that talks to the database directly (see below). Once the job
existed, the write endpoints had no client left — and a public mutation endpoint guarded by
a shared static key that nothing legitimately calls is a liability, not a feature. So they
were removed, along with `WRITE_API_KEYS` and `app/api/security.py`.

The result is an architecture with exactly two paths in: reads are public and
unauthenticated, writes happen through an authenticated job running inside the deployment
perimeter with its own service account. There is no third path.

Note that CORS is not a security control here. `CORS_ORIGINS` constrains browser JavaScript
and does nothing to a request from `curl`; with a read-only API there is nothing for it to
protect, and it stays only to keep the frontend's fetches well-formed.

If an admin interface is ever added, the write surface should come back with per-user
authentication and an audit trail — not with a shared key, which is the pattern this
removal retired.

## Populating the database

Data reaches the database three different ways, and which one applies depends on what kind
of data it is:

| Kind | Example | How it ships |
| --- | --- | --- |
| Schema | a new column | An Alembic migration, reviewed like code (see below) |
| Reference data | the country list | Seeded inside the migration that creates its table |
| Domain data | players, teams | The load job, `backend/src/app/jobs/load_csv.py` |

The load job is a batch job, not an API client. It opens its own database session and writes
through the service layer, so validation and the natural-key rules live in one place, and it
needs no API key — only `DATABASE_URL` and `DATA_SOURCE`. Run it in the backend container,
which is also how it runs in production:

```sh
just db-load teams
just db-load players
just db-load-all                            # teams first, then players
just db-load "players -s /tmp/other.csv"    # override the source for one run
```

Teams load before players because `players.team_code` is a foreign key onto them.

Records are matched on a natural key — team code, and the player's normalized name — so
re-running updates existing rows rather than duplicating them. Matching and writing are a
single `INSERT ... ON CONFLICT DO UPDATE`, which the database settles atomically: reading
first and then deciding to insert would let two overlapping runs both find nothing, both
insert, and one fail on the unique index.

**A run is all or nothing.** Every row is validated first, and if any row is bad the job
reports every problem with its line number, writes nothing, and exits non-zero:

```txt
players.csv:14: country: unknown code 'ZZ'
players.csv:22: no: non-numeric squad number 'eleven'
Error: 2 invalid row(s) of 29; nothing was written.
```

A squad list is a coherent set, so a half-applied load is worse than none — and it means
re-running after a fix is always safe. The exit code is the job's contract with Cloud Run:
`0` committed, `1` nothing written, `2` bad usage.

### Where the CSVs come from

The job reads a URI, and which URI is configuration rather than code:

| Environment | `DATA_SOURCE` | Who writes the CSVs |
| --- | --- | --- |
| Local | `/app/fixtures` (the `fixtures/` mount) | Committed to this repo |
| Staging, production | `gs://BUCKET/PREFIX` | A separate scraper project |

Parsing, validation and loading are identical either way — only
[`sources.py`](./backend/src/app/jobs/sources.py) knows the difference, and its `gs://`
branch is currently a stub pending a real bucket to test against.

The split exists because match data will come from a scraper that lives in its own private
repository. A bucket is the only thing the two projects share: the scraper never holds
database credentials or knows this schema, and this repo holds no scraping code. The
alternative — letting the scraper write to Postgres directly, or reinstating an
authenticated write endpoint for it to call — would couple them across a boundary that is
much easier to keep clean than to repair.

`fixtures/{players,teams}.csv` are committed on purpose: small, public, reviewable as a
diff, and they double as the column contract the scraper's output is written against. They
are **development data only** and are deliberately not copied into the image by
`deploy/Dockerfile.backend` — a deployed job gets its data from the bucket, so fixtures have
no business shipping to production.

### Running the job in a deployed environment

There is no infrastructure-as-code in this repo yet, so these are manual steps. The job
reuses the backend image — same code as the API service, different command:

```sh
gcloud run jobs deploy wsl-load-players \
  --image=REGION-docker.pkg.dev/PROJECT/wsl/backend:TAG \
  --region=REGION \
  --service-account=wsl-loader@PROJECT.iam.gserviceaccount.com \
  --set-secrets=DATABASE_URL=wsl-database-url:latest \
  --set-env-vars=DATA_SOURCE=gs://BUCKET/PREFIX \
  --set-cloudsql-instances=PROJECT:REGION:INSTANCE \
  --command=python \
  --args=-m,app.jobs.load_csv,players \
  --max-retries=0

gcloud run jobs execute wsl-load-players --region=REGION --wait
```

`--wait` propagates the exit code, so a failed load actually fails. `--max-retries=0`
because a failure here is a data problem needing a human: the job is idempotent so a retry
is safe, but it would fail identically and treble the log noise.

The service account needs `roles/cloudsql.client`, `roles/secretmanager.secretAccessor` on
the database URL, and `roles/storage.objectViewer` on the data bucket — read-only there,
since the scraper's own service account is the only thing that writes to it. With Cloud SQL
the socket path goes inside the URL, so the whole connection stays one variable:

```txt
postgresql+psycopg://USER:PASSWORD@/DBNAME?host=/cloudsql/PROJECT:REGION:INSTANCE
```

Run it after `alembic upgrade head`, not before — a load that depends on a new column will
fail against the old schema.

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

Local Postgres is the Compose `db` service, database `app`, reachable at `localhost:5432` from the host or hostname `db` from inside Compose. It has three roles: `app`/`app` is the bootstrap superuser (admin only, see below), `app_writer`/`app_writer` is what `DATABASE_URL` connects as, and `api_reader`/`api_reader` is what `API_DATABASE_URL` connects as. DBeaver and other host clients can use any of the three depending on what you want to inspect or test.

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
with more than one instance, concurrent migration runs race each other. That step needs
`DATABASE_URL` and nothing else — `alembic/env.py` reads `DatabaseSettings`, not the
API's `AppSettings`.

The Vite dev server is used locally for fast reloads. The production frontend image builds the React app and serves it with Nginx. The production backend is an independent FastAPI image.

## Checks

```sh
just test
just lint # backend (ruff)
just type-check # frontend (node)
just build
```

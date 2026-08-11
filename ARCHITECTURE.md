<!-- last_verified: 2026-08-06 -->
# Architecture

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - Dashboard with write-amplification metrics and recent missions
  - Missions: create/read/edit/delete/run + a mission-scoped artifact explorer
  - Mission-scoped drone-image ingest (presigned direct-to-B2 PUT)
  - Full-bucket file browser (kept) with preview, download, delete
  - Dark mode via `next-themes`
- **services/api/** — FastAPI backend (layered architecture)
  - REST API for missions (CRUD), reconstruction (run/status), ingest, files
  - B2 S3 integration via boto3 (`repo/` only)
  - OpenDroneMap reconstruction via `pyodm` → NodeODM (`repo/odm.py` only)
  - Health check endpoint with B2 connectivity verification
  - Structured JSON logging with request tracing
  - Prometheus-format metrics endpoint
- **packages/shared/** — TypeScript type definitions
  - Mirrors Pydantic models from the API (files, missions, artifacts)
  - Consumed by `apps/web/` as workspace dependency
- **OpenDroneMap / NodeODM** — the local reconstruction engine (CPU,
  containerized via the root `docker-compose.yml`); the backend connects over
  the NodeODM REST API at `ODM_NODE_URL` (default `http://localhost:3001`)

## Backend Layering

The API follows a strict layered architecture:

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access (boto3 B2 client) — no business logic
  |
service/   Business logic — calls repo, returns types
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` -> `config` -> `repo` -> `service` -> `runtime`
2. No backward imports (e.g., service must not import from runtime)
3. `boto3` **and** `pyodm` (the NodeODM SDK) only allowed in `repo/` layer
4. All boundary data uses Pydantic models (no raw dicts across layers)
5. Authored Python files under `services/api/app/` stay under 300 lines

### Directory Structure

```
services/api/
  main.py                  App entrypoint, middleware, router registration
  app/
    types/                 Pydantic models (files, missions, uploads, stats)
    config/                Settings loaded from environment
    repo/                  Data access: b2_client, missions, odm (pyodm), transfer
    service/               Business logic: files, upload, missions, reconstruction
    runtime/               FastAPI route handlers (files, missions, reconstruction, …)
  scripts/                 export_openapi, setup_b2_cors, seed_mission
  tests/                   pytest tests (structural + integration)
```

## Boundary Invariants

- **No external SDK leakage**: `boto3` is only imported in `app/repo/`, and `pyodm` (the NodeODM engine SDK) is only imported in `app/repo/odm.py`. All other layers interact with B2 and the reconstruction engine through the repo interface.
- **No raw dicts at boundaries**: All data crossing layer boundaries uses typed Pydantic models.
- **No cross-layer mutable state**: Configuration is read-only after init, and no mutable state is shared *between* layers. Intra-layer caches/counters (the listing cache in `repo/list_cache.py`, the B2 connectivity cache in `repo/b2_client.py`, the download counter in `repo/counter.py`, the rate-limit and metrics state in `runtime/`, and the reconstruction job registry in `service/reconstruction.py`) are module-local and guarded by a `threading.Lock`. Two things run on background threads: the listing cache serves a stale entry immediately while a thread re-scans (stale-while-revalidate; `main.lifespan` warms it at startup), and each reconstruction runs in its own daemon thread that streams inputs from B2, drives NodeODM, and writes outputs back — its live progress lives in the guarded registry, with milestones persisted to the mission manifest so status survives a restart.
- **Validated inputs**: All HTTP inputs validated by FastAPI/Pydantic. File keys reject empty and path-traversal patterns; optional prefix confinement via `ALLOWED_KEY_PREFIX` (off by default).

## Deployment

- **Local dev** — `pnpm dev` runs both services via `concurrently`
  - Web: `localhost:3000`
  - API: `localhost:8000`
- **Railway** — two services from the same repository: `web` builds from the
  repository root because it consumes `packages/shared`; `api` builds from
  `services/api`. The versioned per-service configs and the human-approved
  staging/production contract live in [infra/railway/README.md](infra/railway/README.md).
- **Vercel** — one project using [Vercel Services](https://vercel.com/docs/services):
  the `web` (Next.js) and `api` (FastAPI) services build from the same repo and
  share one origin — the web app at `/`, the API under `/api`. The repo-root
  `vercel.json` declares both services and routes `/api/*` to the API service;
  the Vercel-only `services/api/index.py` strips the `/api` prefix so FastAPI
  keeps its native paths (`/health`, `/files`, …). Uploads go directly from the
  browser to B2 via a presigned PUT (see
  [File Upload](docs/features/file-upload.md)), so they bypass the Function's
  4.5 MB payload ceiling entirely — the bucket must allow the deploy origin in
  its CORS. A two-separate-Projects alternative and the full delivery contract
  live in [infra/vercel/README.md](infra/vercel/README.md).

External provisioning and deployment remain explicit user-approved actions.

## Data Stores

- **Backblaze B2** — object storage (S3-compatible API)
  - No application database — B2 is the sole data store
  - **Missions** are JSON manifests at `missions/<id>/mission.json`; the manifest
    is the single record for each mission
  - Mission inputs under `missions/<id>/images/`; generated outputs under
    `missions/<id>/outputs/` (orthomosaic, DEM, point cloud, mesh, textures)
  - Generic uploads under `uploads/`
  - Listing, metadata, and stats via S3 `list_objects_v2` / `head_object`;
    large outputs written with boto3 managed multipart (`upload_file` +
    `TransferConfig`) in `repo/transfer.py`

## External Services

- **Backblaze B2 S3 API** — file storage, retrieval, deletion, presigned URLs
- **OpenDroneMap NodeODM REST API** — the reconstruction engine (CPU,
  containerized). Reached via `pyodm` from `repo/odm.py` at `ODM_NODE_URL`. No
  API key; not a Backblaze service.

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md) for full security documentation.

- **Frontend -> API** — CORS-restricted to configured origins. `CORSMiddleware` is registered LAST in `main.py` (outermost) so it wraps **every** response, including uncaught-exception 500s — otherwise the browser would block error responses and the UI would only see an opaque "network error". See [docs/RELIABILITY.md](docs/RELIABILITY.md#error-handling). A per-IP rate-limit middleware sits inner to CORS; see [docs/SECURITY.md](docs/SECURITY.md#rate-limiting).
- **API -> B2** — authenticated via application keys, signature v4
- **Client -> B2** — presigned URLs for download (10-min expiry, forced attachment)

## Data Flows

- **Mission create/edit**: Browser -> `POST /missions` / `PATCH /missions/{id}` -> service writes the JSON manifest to B2 (`put_object`)
- **Mission ingest**: Browser -> `POST /missions/{id}/images/presign` -> Browser PUTs each JPEG **directly to B2** under `missions/{id}/images/` -> `POST /missions/{id}/images/verify`
- **Reconstruction (marquee)**: Browser -> `POST /missions/{id}/run` (202) -> background job in `service/reconstruction.py`: stream inputs from B2 to a temp dir (`repo/transfer`) -> submit to NodeODM (`repo/odm`) -> poll status (progress in an in-memory registry; milestones persisted to the manifest) -> download assets -> write outputs back to B2 via managed multipart -> mark completed. Browser polls `GET /missions/{id}/status` while running.
- **Mission delete**: Browser -> `DELETE /missions/{id}` -> service sweeps `delete_objects` **scoped to `missions/{id}/` only** (manifest + inputs + outputs)
- **Artifact browse/download**: Browser -> `GET /missions/{id}/artifacts` -> presigned `GET` per artifact (reuses `/files-by-key/download`) + copy-able `s3://<bucket>/<key>` URI (`GET /config`)
- **Upload (generic)**: Browser -> `POST /upload/presign` -> direct PUT to B2 -> `POST /upload/verify`
- **List / Download / Delete (files)**: the kept full-bucket `/files` flows

## Observability

- Structured JSON logging on all requests with `request_id`
- Request timing middleware (logs duration per request; also the catch-all that converts uncaught exceptions to a typed JSON 500)
- `/metrics` endpoint (Prometheus format: request count, latency, upload count)
- `/health` endpoint (B2 connectivity check)

## API Contract

- Checked-in OpenAPI artifact: `docs/api/openapi.json`
- Export/check command: `pnpm contract:export` / `pnpm contract:check`
- FastAPI freshness test: `services/api/tests/test_openapi_contract.py`
- Frontend route drift test: `apps/web/src/lib/api-contract.test.ts`

The frontend client keeps a small `API_CLIENT_ROUTES` registry in
`apps/web/src/lib/api-client.ts`. Tests compare that registry to the checked-in
OpenAPI artifact so route changes fail loudly before the hand-written client can
silently drift from FastAPI. `GET /metrics` is intentionally server-only.

## Canonical Files

- Mission CRUD handler: `services/api/app/runtime/missions.py`
- Reconstruction run/status handler: `services/api/app/runtime/reconstruction.py`
- Mission orchestration + stats: `services/api/app/service/missions.py`
- Reconstruction pipeline + job registry: `services/api/app/service/reconstruction.py`
- Mission manifest store + scoped delete: `services/api/app/repo/missions.py`
- OpenDroneMap engine adapter (only `pyodm` import): `services/api/app/repo/odm.py`
- Managed multipart transfer: `services/api/app/repo/transfer.py`
- B2 data access (repo layer): `services/api/app/repo/b2_client.py`
- Pydantic models: `services/api/app/types/` (`files.py`, `missions.py`, `upload.py`, `stats.py`, `formatting.py`)
- Config (pydantic-settings): `services/api/app/config/settings.py`
- Structural tests: `services/api/tests/test_structure.py`
- OpenAPI contract: `docs/api/openapi.json`
- OpenAPI exporter: `services/api/scripts/export_openapi.py`
- Frontend API client: `apps/web/src/lib/api-client.ts`
- Shared TypeScript types: `packages/shared/src/types.ts`

## Core Features

- [Missions](docs/features/missions.md)
- [Reconstruction](docs/features/reconstruction.md)
- [Mission ingest / File Upload](docs/features/file-upload.md)
- [File Browser](docs/features/file-browser.md)
- [Dashboard](docs/features/dashboard.md)
- [Artifact / Metadata Extraction](docs/features/metadata-extraction.md)

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles and implementation
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — reliability expectations
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions

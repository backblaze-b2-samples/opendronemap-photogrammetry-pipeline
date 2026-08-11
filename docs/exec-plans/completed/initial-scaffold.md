# Build plan — `opendronemap-photogrammetry-pipeline`

Source of truth (starter tree): `.claude/scratch/vcsk-df0936c9-c65c-41e6-bc44-5384cc3630ca/`
Target: `./opendronemap-photogrammetry-pipeline`

## 1. Purpose

`opendronemap-photogrammetry-pipeline` is a B2 sample for surveying firms, agricultural
drone operators, and GIS teams. It ingests large sets of overlapping drone JPEGs into a B2
bucket (grouped by mission), runs **OpenDroneMap** locally to reconstruct
publication-quality **orthomosaics, DEMs, dense point clouds, and textured 3D meshes**, and
writes those far-larger outputs back to B2 for downstream GIS analysis and client delivery.
Its whole point is **extreme write amplification**: a modest input image set produces
outputs several times larger, and B2 is the durable storage layer holding both — accessed
exclusively through the S3-compatible API with a custom user agent and standardized `B2_*`
env vars. It runs on local OSS (OpenDroneMap via NodeODM); **no second API key — B2
credentials only.**

## 2. Architecture delta from vibe-coding-starter-kit

The starter kit is the ceiling. Keep its layered FastAPI backend, shadcn UI kit, bucket
explorer, upload flow, contract/branding/agent-doc harness, and deploy configs. Strip the
generic "file management" framing where it no longer fits, and add a **Mission** entity plus
an OpenDroneMap reconstruction engine.

### KEEP (as-is — do not strip/rename/replace)
- **UI kit / design system:** `apps/web/src/components/ui/**`, `globals.css` tokens, `/design` page. Build new screens from these primitives only.
- **Bucket explorer (NON-NEGOTIABLE KEEP):** `/files` route, `apps/web/src/app/files/**`, `apps/web/src/components/files/**`, and the Files sidebar entry. Full-bucket browse stays. (A GIS analyst browsing every object in the bucket is a genuine use — no tension here.)
- **Upload (starter contract KEEP):** `/upload` route + `apps/web/src/components/upload/**` + sidebar entry. Stays as the generic bucket uploader; the mission-scoped image ingest is *added* on top (see ADD), it does not replace this.
- **Backend layering** (`types → config → repo → service → runtime`) and every mechanical invariant: boto3 only in `repo/`, all external SDKs wrapped in `repo/`, Pydantic at boundaries, files < 300 lines, structured logging, TanStack Query hooks (no bare `useEffect+fetch`), OpenAPI contract + `API_CLIENT_ROUTES` drift tests, `check:agent-docs`, branding single-source (`APP_NAME`), one attribution token across `user_agent_extra`/`utm_content`.
- **Presigned-PUT direct-to-B2 upload** mechanism (browser → B2) — reused for ingesting drone JPEGs, which are large and must bypass any serverless payload ceiling.
- **Full-bucket listing cache** (`repo/list_cache.py`, stale-while-revalidate + startup warm), health/metrics/ratelimit middleware, presigned-GET download, key-prefix confinement option.
- Deploy configs (`infra/vercel`, `infra/railway`, `vercel.json`) — retitle only, keep structure.

### TRIM (remove/replace from starter)
- **Dashboard internals** — `apps/web/src/components/dashboard/**` and `/` page: replace file-upload stats/chart/recent-uploads with photogrammetry metrics (see Key features). The screen and its layering stay; the *content* is rewritten (AGENTS.md §2 says the dashboard is the one screen designed to be rewritten per app).
- **Generic file-metadata extraction framing** — `service/metadata.py` currently sniffs images/PDFs. Repurpose toward geospatial/artifact metadata (artifact type + size classification: orthomosaic/DEM/point-cloud/mesh); drop PDF sniffing that no longer applies. Keep it in `service/`, keep it typed.
- **"File management dashboard" copy** everywhere (README, app-config description, docs) → photogrammetry-pipeline copy.
- No wholesale deletion of routes — everything stays wired; only content/copy is retargeted.

### ADD (new for this sample)
- **Mission entity (primary resource)** — persisted as a JSON manifest in B2 (`missions/<id>/mission.json`); B2 remains the sole data store (no DB), consistent with the starter invariant.
  - New Pydantic types: `Mission`, `MissionCreate`, `MissionUpdate`, `MissionStatus`, `Artifact`, `MissionStats` (`app/types/missions.py`).
  - New repo module `app/repo/missions.py` — CRUD over mission manifests in B2 (list = `list_objects_v2` on `missions/` filtered to `mission.json`; get/put/delete manifest; delete-mission scopes a `delete_objects` sweep to the **`missions/<id>/` prefix only** — never a bucket-wide wipe).
  - New repo module `app/repo/odm.py` — wraps the **`pyodm`** client (the ONLY place `pyodm` is imported; it is an external SDK so it lives in `repo/`, same rule as boto3). Submits an image set to NodeODM, polls task status/progress, downloads result artifacts.
  - New repo module `app/repo/transfer.py` (or extend `b2_client.py`) — **boto3 managed multipart transfer** (`upload_file`/`TransferConfig`) for large output artifacts (GeoTIFF/LAS/mesh), and a streaming download of B2 image sets to a temp dir for the reconstruction. This is the write-amplification workhorse.
  - New service `app/service/missions.py` — mission lifecycle orchestration; and `app/service/reconstruction.py` — the run pipeline (download inputs from B2 → submit to NodeODM → poll → upload outputs to B2 → update manifest). A **module-local, `threading.Lock`-guarded in-memory job registry** tracks live progress (mirrors the starter's counter/cache pattern); milestone/terminal state is persisted to the B2 manifest so status survives restart.
  - New runtime routers `app/runtime/missions.py` (CRUD) and `app/runtime/reconstruction.py` (`POST /missions/{id}/run` → 202 + background job; `GET /missions/{id}/status`). Update `main.py` registration, `docs/api/openapi.json` (`pnpm contract:export`), `lib/api-client.ts` `API_CLIENT_ROUTES`, `lib/queries.ts`, and (for backend-only status polling if not client-consumed) `SERVER_ONLY_OPERATIONS`.
- **Frontend Missions feature (the sample-specific, folder-scoped asset explorer):**
  - `/missions` list page — table of missions with status, input size, output size, **write-amplification ratio**, created/date.
  - `/missions/[id]` detail page — status + live progress (TanStack Query `refetchInterval` while running), mission-scoped **artifact gallery** listing only `missions/<id>/` objects (inputs + generated orthomosaic/DEM/point-cloud/mesh) with sizes, per-artifact presigned download, and a copy-S3-URI action for the "serve/query from B2" story. This is the required sample-specific explorer scoped to the app's own folder (distinct from the kept full-bucket `/files` explorer).
  - Create + Edit mission forms (see Key features → Form UX).
  - New "Missions" sidebar entry (icon e.g. `Map`/`Layers`) added to `navItems` in `app-sidebar.tsx`, placed above Files.
- **NodeODM engine** — root `docker-compose.yml` with `opendronemap/nodeodm` (CPU) exposing the ODM REST API; backend connects via `ODM_NODE_URL` (default `http://localhost:3001`). Documented as a local-dev dependency (Docker/Colima is available in this env). ODM/NodeODM is CPU-based — see Key features deployment note.
- **Seed script** `services/api/scripts/seed_mission.py` — downloads a small, public/CC-licensed OpenDroneMap sample image set (builder picks a concrete small dataset and records its license in the seed script + docs), uploads it to B2 under a demo mission prefix, and writes the mission manifest — so a fresh clone has one runnable mission. Keep it optional and documented; the scaffold review does not run a reconstruction.
- Requirements: add `pyodm` (pinned) to `services/api/requirements.txt` and regenerate `requirements.lock`. `pyodm` is a thin HTTP client (imports cleanly without a live node; unit tests mock the node), so it doesn't threaten `pnpm verify:api`.

## 3. B2 surface (S3-compatible only — no b2-native)

| Operation | S3 call | Where |
|---|---|---|
| Ingest drone JPEGs | presigned `put_object` (browser→B2) | reuse upload flow, scoped to `missions/<id>/images/` |
| List missions / artifacts / full bucket | `list_objects_v2` (paginated + cache) | `repo/missions.py`, `repo/b2_client.py` |
| Download image set for reconstruction | `get_object` (streamed to temp dir) | `repo/transfer.py` |
| Write outputs (GeoTIFF/DEM/LAS/mesh/texture) | `put_object` via **managed multipart** `upload_file`+`TransferConfig` | `repo/transfer.py` |
| Write/read/update mission manifest | `put_object` / `get_object` | `repo/missions.py` |
| Artifact size/metadata | `head_object` | `repo/b2_client.py` |
| Serve/query artifacts | presigned `get_object` GET (+ copy S3 URI) | `repo/b2_client.py` |
| Delete mission | `delete_objects` **scoped to `missions/<id>/`** | `repo/missions.py` |
| Health | `head_bucket` | `repo/b2_client.py` |

**No b2-native API anywhere.** boto3 stays confined to `repo/`. Custom user agent set on the single cached S3 client. This is a **write-heavy, high-volume** B2 workload — outputs dominate storage — which is exactly the golden-rule "data-heavy" story.

## 4. Key features (seed README + `docs/features/*.md`)

1. **Mission ingest** — group and upload overlapping drone JPEGs into a mission's B2 prefix via presigned direct-to-B2 PUT. `deployment: local` (no external provider; upload is B2-only).
2. **OpenDroneMap reconstruction (marquee, local engine)** — run SfM + dense MVS via NodeODM to produce orthomosaic, DEM, point cloud, and textured mesh. `deployment: **local**`. **No external API provider** (OpenDroneMap is the local OSS engine; **no second key** — B2 credentials only). Per the local hard-rule: engine runs on **CPU by default**. ODM's pipeline (OpenSfM/OpenMVS) is CPU-based and containerized; there is **no MPS path** and GPU is not required — the NodeODM CPU image is the default and only runtime, which satisfies "default to CPU, never hard-require a GPU." Estimated external cost per full demo run: **$0** (fully local). Demo uses a small dataset + fast/low presets (`--fast-orthophoto`, `--pc-quality lowest`, `--feature-quality low`) so a run completes in minutes.
3. **Write-amplification analytics** — the dashboard and mission detail compute input bytes vs output bytes and the amplification ratio (outputs are typically 3–10× inputs), telling the "B2 as the storage layer for a persistent high-volume workload" story with real numbers from the bucket.
4. **Mission-scoped artifact explorer + serve-from-B2** — browse a mission's inputs and generated artifacts, download each via presigned URL, and copy its S3 URI for downstream GIS pipelines.
5. **Full-bucket explorer (kept)** — the starter's `/files` browser over the entire bucket.

**External API provider:** NONE. Every feature is `deployment: local` or B2-only. No provider key, no Genblaze (the description names no provider and no "Suggested stack" mentioning Genblaze/`genblaze-*`/`genblaze-s3`), no cost beyond B2 storage.

### Primary-entity lifecycle (UI completeness)
Primary entity: **Mission**. All five verbs are user-accessible and MUST be built in the UI:
- **create** — "New Mission" form (name, capture date, quality preset, output products, image-source prefix), then ingest images.
- **read** — `/missions` list + `/missions/[id]` detail (status, progress, artifacts, amplification).
- **edit** — edit mission metadata + ODM options while it is not running.
- **delete** — delete a mission (manifest + its B2 artifacts, scoped to `missions/<id>/`), with a confirm dialog (reuse `alert-dialog` / danger-zone pattern).
- **run** — trigger the reconstruction (the marquee action) from the detail page.

**`omitted_ui_verbs`: none.** No verb is left UI-less; nothing goes in `omitted_ui_verbs`.

### Form UX conventions (create/edit mission forms)
Exemplar to match: `apps/web/src/components/settings/settings-form.tsx` (uses `Select`/`RadioGroup` + `FormDescription`).
- **Finite-value fields → selectors (both create & edit):**
  - **Quality preset** → `Select`: `Draft` / `Standard` / `High` (maps to ODM flag bundles). Never free text.
  - **Output products** → `Checkbox`/`Switch` group: Orthomosaic, DEM, Point cloud, Mesh (finite toggles).
  - **DEM resolution** (if exposed) → `Select` of discrete cm/px values.
- **Free-text fields:** mission name, description. **Date field:** capture date.
- **CREATE-form safe defaults as guidance only** (placeholder / `FormDescription`, never an autofill button): name placeholder `e.g. north-field-2026-08`; quality default **Standard** with description "Draft = fastest/lowest quality — good for a first test run"; output products default to Orthomosaic+DEM checked; image-prefix hint `missions/<id>/images/`.
- **EDIT form** opens pre-filled from the real mission; same selectors; no default hints.

## 5. Doc transforms
- **Rewrite:** `docs/features/dashboard.md` (write-amplification metrics), `docs/features/file-upload.md` → mission ingest (or add `missions-ingest.md` and keep upload doc pointing to it), `docs/features/metadata-extraction.md` → artifact/geospatial metadata. Update `ARCHITECTURE.md` (add Mission data store as B2 manifests, NodeODM external engine, reconstruction data flow), `README.md`, `docs/app-workflows.md` (mission lifecycle journey), `AGENTS.md` repo map + doc-map rows, `docs/SECURITY.md` (mission-scoped delete confinement).
- **Keep (light edits):** `docs/features/file-browser.md` (bucket explorer), `docs/features/settings.md`, `docs/RELIABILITY.md`, `docs/dev-workflows.md` (add NodeODM prerequisite + seed step).
- **Add:** `docs/features/reconstruction.md` (ODM run pipeline, presets, CPU note), `docs/features/missions.md` (lifecycle + write-amplification), and `docs/exec-plans/completed/initial-scaffold.md` (this plan, moved on PASS).

## 6. Rename table (`vibe-coding-starter-kit` → `opendronemap-photogrammetry-pipeline`)

| Kind | From | To |
|---|---|---|
| Repo / kebab slug | `vibe-coding-starter-kit` | `opendronemap-photogrammetry-pipeline` |
| Root `package.json` `name` | `vibe-coding-starter-kit` | `opendronemap-photogrammetry-pipeline` |
| pnpm workspace scope | `@vibe-coding-starter-kit/web`, `@vibe-coding-starter-kit/shared` | `@opendronemap-photogrammetry-pipeline/web`, `@opendronemap-photogrammetry-pipeline/shared` (update `pnpm-workspace.yaml`, both `package.json`, all `pnpm --filter` refs in root scripts) |
| `APP_NAME` (`lib/app-config.ts`) | `Vibe Coding Starter Kit` | `OpenDroneMap Photogrammetry Pipeline` |
| `APP_DESCRIPTION` | `File management dashboard template powered by Backblaze B2` | `Drone photogrammetry pipeline — orthomosaics, DEMs, point clouds & 3D meshes on Backblaze B2` |
| Attribution token (`user_agent_extra` in `b2_client.py` **and** `utm_content` in `app-sidebar.tsx`/README/docs — must stay identical) | `b2ai-oss-start` | `opendronemap-photogrammetry-pipeline` |
| FastAPI title/description | derived from `APP_NAME` (branding single-source) — verify it re-derives; do not hardcode |
| Deploy service names / image tags / workflow slugs | any `vibe-coding-starter-kit` occurrence | `opendronemap-photogrammetry-pipeline` |

### Env-var rename → **Standard #3** (parent CLAUDE.md B2 standard #3; starter deviates — new samples must conform, and `b2-doctor`/sample-reviewer flag deviations)
Update `settings.py` field names, `b2_client.py`, `.env.example`, `scripts/doctor.mjs`/`setup.mjs` (any required-var checks), README, and docs together.

| Starter | Standard #3 | Notes |
|---|---|---|
| `B2_KEY_ID` (`b2_key_id`) | `B2_APPLICATION_KEY_ID` (`b2_application_key_id`) | rename field + all reads |
| `B2_APPLICATION_KEY` | `B2_APPLICATION_KEY` | unchanged |
| `B2_BUCKET_NAME` | `B2_BUCKET_NAME` | unchanged |
| `B2_ENDPOINT` (`b2_endpoint`) | `B2_REGION` (`b2_region`, e.g. `us-west-004`) | drop the raw endpoint var; derive `https://s3.{region}.backblazeb2.com` in `get_s3_client()` |
| `B2_PUBLIC_URL` (`b2_public_url`) | `B2_PUBLIC_URL_BASE` (`b2_public_url_base`) | rename field + `_public_url()` |

Non-B2 app config var to ADD: `ODM_NODE_URL` (default `http://localhost:3001`) — NodeODM engine URL. Not a `B2_*` var.

## Build/verify expectations for the builder
- `pnpm run setup` then `pnpm verify` must pass (lint, tests incl. structural boundary tests, typecheck, build, `check:agent-docs`, contract check). Add/adjust unit tests for the new repo/service modules with `pyodm` and B2 mocked — do NOT require a live NodeODM or live B2 in `pnpm verify`.
- Keep every authored Python file under `services/api/app/` < 300 lines; split modules if needed.
- Do not run a full reconstruction, create binary assets/screenshots, push to a remote, or touch sibling samples — those are later pipeline steps.

<!-- last_verified: 2026-08-11 -->
# Completed: Initial scaffold — opendronemap-photogrammetry-pipeline

Built from the Backblaze B2 vibe-coding starter kit. This records the scaffold
decisions; the living detail lives in the feature docs.

## Purpose
A B2 sample for surveying firms, agricultural drone operators, and GIS teams. It
ingests overlapping drone JPEGs into B2 (grouped by mission), runs **OpenDroneMap**
locally (via NodeODM) to reconstruct orthomosaics, DEMs, dense point clouds, and
textured 3D meshes, and writes those far-larger outputs back to B2 — a
write-heavy, high-volume B2 workload. No second API key: B2 credentials only.

## What was added
- **Mission** primary entity, persisted as B2 JSON manifests (no database) —
  full CRUD + run. Types in `app/types/missions.py`; repo `app/repo/missions.py`
  (manifest store + prefix-scoped delete); service `app/service/missions.py`;
  runtime `app/runtime/missions.py`. Frontend `/missions` + `/missions/[id]` and
  `components/missions/`. See [features/missions.md](../../features/missions.md).
- **OpenDroneMap reconstruction** (marquee): `app/repo/odm.py` (the only `pyodm`
  import), `app/repo/transfer.py` (boto3 managed multipart), and
  `app/service/reconstruction.py` (pipeline + threading-guarded job registry).
  NodeODM via the root `docker-compose.yml`, `ODM_NODE_URL`. CPU-only, no GPU.
  See [features/reconstruction.md](../../features/reconstruction.md).
- **Mission-scoped ingest** reusing the presigned-PUT flow, and a mission-scoped
  artifact explorer (kept the full-bucket `/files` explorer too).
- **Write-amplification analytics** on the dashboard and mission detail.
- Seed script `services/api/scripts/seed_mission.py`.

## What was kept / trimmed
- Kept: UI kit, `/files` explorer, `/upload`, backend layering + all mechanical
  invariants, contract/branding/agent-doc harness, deploy configs.
- Trimmed/retargeted: dashboard content → write-amplification metrics; generic
  copy → photogrammetry copy. Added geospatial artifact classification alongside
  the kept generic metadata extractor.

## Standards
- Env vars migrated to Standard #3: `B2_APPLICATION_KEY_ID`, `B2_APPLICATION_KEY`,
  `B2_BUCKET_NAME`, `B2_REGION` (S3 endpoint derived from region),
  `B2_PUBLIC_URL_BASE`. Added non-B2 `ODM_NODE_URL`.
- Single attribution token `b2ai-opendronemap-photogrammetry-pipeline` across
  `user_agent_extra` and `utm_content`. S3-compatible API only; boto3 and pyodm
  confined to `repo/`.

## Verification
- `pnpm run setup` then `pnpm verify` pass (lint, structural boundary tests, unit
  tests, typecheck, build, `check:agent-docs`, contract check). `pyodm` and B2 are
  mocked in unit tests — no live NodeODM or B2 required for `pnpm verify`.

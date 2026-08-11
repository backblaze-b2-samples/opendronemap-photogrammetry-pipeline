<!-- last_verified: 2026-08-11 -->
# Feature: OpenDroneMap Reconstruction

## Purpose
The marquee action: turn a mission's drone image set into publication-quality
orthomosaics, DEMs, dense point clouds, and textured 3D meshes using the local
OpenDroneMap engine (NodeODM), then write those far-larger outputs back to B2.

## Used By
- UI: `/missions/[id]` — the **Run reconstruction** button + live status card
- API: `POST /missions/{mission_id}/run` (202), `GET /missions/{mission_id}/status`

## Core Functions
- `services/api/app/repo/odm.py` — the ONLY `pyodm` import: `submit()`, `status()`, `download_assets()`, `engine_online()`
- `services/api/app/repo/transfer.py` — stream inputs down from B2 and write outputs back via boto3 managed multipart (`upload_file` + `TransferConfig`)
- `services/api/app/service/reconstruction.py` — the pipeline + `threading.Lock`-guarded in-memory job registry + `build_odm_options()`
- `services/api/app/runtime/reconstruction.py` — run/status routes
- `apps/web/src/components/missions/run-mission-button.tsx`, `mission-status-card.tsx`

## Canonical Files
- Pipeline + job registry: `services/api/app/service/reconstruction.py`
- Engine adapter: `services/api/app/repo/odm.py`

## Inputs
- `mission_id` (path) — the mission to reconstruct; must already have input images
- Engine options derived from the mission's quality preset + selected products (`build_odm_options`)

## Outputs
- NodeODM task; result assets uploaded to `missions/<id>/outputs/`
- `MissionStatus` (state, progress 0–100, stage, task_uuid, error) — live from the registry, milestones persisted to the manifest
- Side effect: large B2 writes (the write-amplification workload)

## Flow
1. `POST /run` validates the mission exists, is not already running, and has ≥1 input image → sets `queued`, spawns a background thread
2. Thread: download inputs from B2 to a temp dir (`repo/transfer`)
3. Submit the image set to NodeODM with the mapped options (`repo/odm.submit`)
4. Poll `repo/odm.status` until COMPLETED/FAILED/CANCELED — progress goes to the in-memory registry each tick; milestones (`running`, terminal) are persisted to the manifest
5. On completion: download assets, upload them to `missions/<id>/outputs/` via managed multipart, mark `completed`
6. The detail page polls `GET /status` every 2s while queued/running (TanStack `refetchInterval`)

## Engine & deployment
- `deployment: local`. The engine is **OpenDroneMap via NodeODM**, started by the root `docker-compose.yml` and reached at `ODM_NODE_URL` (default `http://localhost:3001`).
- **No external API provider and no second key** — B2 credentials only. Estimated external cost per run: **$0** (fully local; you pay only for B2 storage of the outputs).
- **CPU by default, no GPU required.** OpenDroneMap's pipeline (OpenSfM/OpenMVS) is CPU-based and containerized; there is no MPS path and GPU is never required — the NodeODM CPU image is the default and only runtime.
- Demo tip: use the Draft preset (`--fast-orthophoto`, `--pc-quality lowest`, `--feature-quality low`) on a small dataset so a run finishes in minutes.

## Edge Cases
- NodeODM unreachable / task FAILED → mission marked `failed` with the engine error surfaced in the status card
- No input images → 409 from `POST /run`
- Run while already running/queued → 409
- API restart mid-run → the last persisted milestone survives on the manifest; live per-tick progress resets

## UX States
- Idle: Run button enabled (disabled with a hint when there are no images)
- Running: stage text + a live-polled progress indicator. During the early phases that report no percentage (queued, "Downloading images from B2", "Submitting to NodeODM") it shows an indeterminate animated bar so the wait reads as working, not frozen; once NodeODM reports a real percentage ("Reconstructing", "Downloading outputs") it switches to a determinate bar with the numeric `NN%` label
- Failed: destructive alert with the engine error
- Completed: status badge + outputs visible in the artifact gallery
- Terminal edge: when the polled status reaches a terminal state (`completed`/`failed`), the detail page reconciles immediately — the Run button re-enables, and the stats grid, mission list row, and artifacts table refresh without needing a navigation or window refocus

## Verification
- Test files: `services/api/tests/test_reconstruction.py`
- Required cases: option mapping (draft presets, skip-3dmodel), happy-path pipeline (mocked `pyodm`+B2) reaches `completed`, engine failure → `failed`, run endpoint 202, 409 without images, status endpoint reads the registry
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify` (mocks `pyodm` and B2 — no live NodeODM or B2 needed)
- Full local verify command: `pnpm verify:full` when E2E/live prerequisites apply; an actual reconstruction additionally needs `docker compose up` and B2 credentials
- Pass criteria: focused tests and `pnpm verify` green

## Related Docs
- [Missions](missions.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Dev Workflows](../dev-workflows.md)

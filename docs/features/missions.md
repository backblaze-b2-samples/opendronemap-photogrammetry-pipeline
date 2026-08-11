<!-- last_verified: 2026-08-11 -->
# Feature: Missions

## Purpose
The Mission is the app's primary entity — a photogrammetry job that groups a
drone image set and its reconstruction outputs under a single B2 prefix. Its
only datastore is a JSON manifest in the bucket (no database).

## Used By
- UI: `/missions` (list), `/missions/[id]` (detail with all five verbs)
- API: `GET/POST /missions`, `GET/PATCH/DELETE /missions/{mission_id}`, `GET /missions/{mission_id}/artifacts`

## Core Functions
- `services/api/app/types/missions.py` — `Mission`, `MissionCreate`, `MissionUpdate`, `MissionStatus`, `MissionStats`, `Artifact`, and the finite enums (`QualityPreset`, `OutputProduct`, `ArtifactKind`, `MissionState`)
- `services/api/app/repo/missions.py` — manifest read/write, object listing, and the **prefix-scoped** delete sweep
- `services/api/app/service/missions.py` — lifecycle (create/read/update/delete), `compute_stats()`, `classify_artifact()`, `list_artifacts()`
- `services/api/app/runtime/missions.py` — CRUD + artifact routes
- `apps/web/src/components/missions/` — table, forms, status card, artifact gallery, delete dialog

## Canonical Files
- Manifest store + scoped delete: `services/api/app/repo/missions.py`
- Lifecycle orchestration: `services/api/app/service/missions.py`
- Create/edit form (Select/Checkbox selectors): `apps/web/src/components/missions/mission-form.tsx`

## Inputs
- `MissionCreate`: name (free text), description, capture_date, quality preset (Select), output products (Checkbox group), optional DEM resolution (Select), optional image prefix
- `MissionUpdate`: any subset of the above (applied only while not running)

## Outputs
- Manifest at `missions/<id>/mission.json` (`put_object`)
- `Mission` responses carry a live-computed `stats` block (input/output bytes + amplification ratio)
- Delete → `{ deleted, id, objects_deleted }`; removes only `missions/<id>/*`

## Flow
- **Create** → `POST /missions` writes a manifest; id is `slug(name)-<8 hex>`; image prefix defaults to `missions/<id>/images/`
- **Read** → `/missions` lists all manifests newest-first; `/missions/[id]` shows status, amplification, artifacts
- **Edit** → `PATCH` rejects (409) while the mission is queued/running
- **Delete** → `delete_objects` scoped to the mission prefix only, behind an `alert-dialog` confirm
- **Run** → see [Reconstruction](reconstruction.md)

## Edge Cases
- Invalid/traversal mission id → 400 (validated before any B2 call)
- Missing mission → 404
- Edit/delete while running → 409
- Manifest is never listed as an artifact; folder markers are skipped

## UX States
- Empty: "No missions yet" with a New-mission action
- Loading: skeleton rows
- Error: inline `ErrorState` with retry

## Verification
- Test files: `services/api/tests/test_missions.py`, `services/api/tests/test_mission_upload.py`
- Required cases: create/get/list/update/delete, prefix-scoped delete leaves other missions intact, amplification ratio, artifact classification, invalid id, edit-while-running conflict
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Full local verify command: `pnpm verify:full` when E2E/live prerequisites apply
- Pass criteria: focused tests and `pnpm verify` green

## Related Docs
- [Reconstruction](reconstruction.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [App Workflows](../app-workflows.md)
- [SECURITY.md](../SECURITY.md) — mission-scoped delete confinement

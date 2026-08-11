<!-- last_verified: 2026-08-11 -->
# Feature: Dashboard

## Purpose
Give an at-a-glance view of the photogrammetry workload — how many missions
exist, how many have completed, total bucket storage, and the headline **write
amplification** (output bytes ÷ input bytes) computed from real B2 sizes.

## Used By
- UI: `/` page (dashboard home)
- API: `GET /missions`, `GET /files/stats`

## Core Functions
- `apps/web/src/components/dashboard/mission-metric-cards.tsx` — 4 metric cards (missions, completed, bucket storage, write amplification)
- `apps/web/src/components/dashboard/amplification-chart.tsx` — grouped bar chart of input vs output MB per reconstructed mission
- `apps/web/src/components/dashboard/recent-missions-table.tsx` — 5 most recent missions with status + amplification
- `apps/web/src/lib/queries.ts` — `useMissions()`, `useFileStats()`
- `services/api/app/service/missions.py` — `list_missions()` + `compute_stats()` (per-mission input/output byte accounting)

## Canonical Files
- Metric cards: `apps/web/src/components/dashboard/mission-metric-cards.tsx`
- Stats logic: `services/api/app/service/missions.py` (`compute_stats`)

## Inputs
- None (dashboard loads data automatically)

## Outputs
- `GET /missions` → `Mission[]`, each carrying a freshly computed `stats` block (input/output counts and bytes, amplification ratio)
- `GET /files/stats` → `UploadStats` for total bucket storage

## Flow
- Page loads → `useMissions()` and `useFileStats()` fetch in parallel
- Metric cards aggregate across missions: count, completed count, bucket storage, and overall amplification = Σ output_bytes ÷ Σ input_bytes
- The chart shows the top missions by output size as input-vs-output bars, making the amplification visible per mission
- The recent-missions table links each row to `/missions/<id>`

## Edge Cases
- No missions yet → empty states on the cards, chart, and table
- Missions with no reconstruction yet → excluded from the chart (no output bytes); amplification shows "—"
- API unavailable → inline `ErrorState` with retry

## UX States
- Loading: skeletons on cards/chart/table + a loading notice
- Empty: "No missions yet" / "No reconstructions yet"
- Loaded: populated cards, chart, table

## Verification
- Test files: `services/api/tests/test_missions.py` (`test_stats_amplification_ratio`, list/create), `apps/web/src/lib/queries.test.ts`
- Required cases: amplification ratio from real sizes, mission list sorting, empty state
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Full local verify command: `pnpm verify:full` when the E2E/live prerequisites in [Dev Workflows](../dev-workflows.md#commands) are available
- Pass criteria: focused tests and `pnpm verify` green

## Related Docs
- [Missions](missions.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [App Workflows](../app-workflows.md)

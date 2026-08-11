<!-- last_verified: 2026-08-11 -->
# App Workflows

User journeys inside the application.

## Run a Photogrammetry Mission (primary journey)

The Mission is the primary entity, and all five verbs are reachable in the UI.

- **Create** — On `/missions`, click **New mission**. The dialog form (matching
  the settings-form conventions) collects the name (free text, with a
  placeholder hint like `north-field-2026-08`), an optional description and
  capture date, a **quality preset** (Select: Draft/Standard/High), the
  **output products** (Checkbox group: orthomosaic, DEM, point cloud, mesh), and
  an optional DEM resolution (Select). Defaults are surfaced as
  placeholder/description guidance only — there is no autofill button. Submitting
  writes the mission manifest to B2 and navigates to the detail page.
- **Ingest** — On `/missions/[id]`, drop drone JPEGs into the **Ingest** card.
  Each image uploads directly to B2 under `missions/<id>/images/` via a
  presigned PUT; the mission stats and artifact gallery refresh when it finishes.
- **Run** — Click **Run reconstruction**. The API returns 202 and starts a
  background job: download inputs from B2 → submit to NodeODM → poll → write
  outputs back to B2. The status card shows live progress (polled every 2s) and
  the stage; a failure surfaces the engine error.
- **Read** — The `/missions` table shows each mission's status, input/output
  sizes, and write-amplification ratio; the detail page shows the amplification
  cards and a mission-scoped artifact gallery (download each artifact via a
  presigned URL, or copy its `s3://bucket/key` URI for downstream GIS tools).
- **Edit** — The **Edit** dialog (pre-filled, same selectors) updates metadata
  and options; it is blocked while the mission is running.
- **Delete** — The **Delete** confirm dialog removes the manifest and every
  object under `missions/<id>/` — scoped to that prefix only — then returns to
  the list.
- See: [Missions](features/missions.md), [Reconstruction](features/reconstruction.md)

## Upload Files

- User navigates to `/upload`
- Drops or selects files in the dropzone
- Client validates file size (max 100MB) and type
- Files upload **directly from the browser to B2** (a presigned PUT). A determinate progress bar tracks the bytes leaving the browser; once they are all sent the row switches to "Verifying upload..." with an *indeterminate* sweeping bar while the API HEADs and magic-byte-sniffs the stored object. That phase has no percentage to report, and a bar parked at a full 100% read as finished-but-stuck
- On success: toast notification, green checkmark, and a "View in Files" link through to the browser
- On failure: red status icon with error message
- User can clear completed uploads
- The queue lives in an app-wide provider: navigating to another page keeps the upload running, shows an "Uploading N files" indicator in the header, and keeps the duplicate-upload guard armed
- Reloading or closing mid-upload asks for confirmation first; if the upload dies anyway, the next load says which file didn't finish
- See: [File Upload](features/file-upload.md)

## Browse and Manage Files

- User navigates to `/files`
- Page loads the 100 most recent objects from the API (sorted most recent first). While it loads, the page says so on screen and escalates the wording if the wait runs long — a full bucket listing measured 2.8s-21s cold
- If that limit was hit, a notice states how many objects the bucket actually holds — the page never claims to show everything
- Files displayed in tree view with folders and type-specific icons
- Folders auto-expand on load until the *majority* of the listed files are reachable without clicking, so the page's own "click a file" instruction is always actionable. Stopping at the first visible file was not enough: one stray top-level object left the other 99 sealed in collapsed folders while the page claimed to show 100
- Clicking a file row opens its preview; the per-row actions menu (preview / download / delete) is always visible, on every viewport
- Arriving at `/files?preview=<key>` expands that file's folders and opens its preview directly. This is how the ⌘K palette and the dashboard's recent-uploads rows hand off a *specific* file; the param is consumed on arrival so it doesn't re-fire later
- **Preview**: opens dialog with image/PDF preview + metadata panel, and the file's Download / Delete actions — the advertised "click a file" path offers everything the row menu does. The loading state holds until the media paints; a failure offers "Open in a new tab". The preview URL is signed with `Content-Disposition: inline` so PDFs render in place
- **Download**: shows a pending state on the row plus a toast while the presigned URL is fetched, then starts the download via an anchor click (which, unlike a popup, still works if the click's user activation expired during a slow presign). Failures are reported; the click can never silently do nothing
- **Delete**: the confirmation dialog stays open showing "Deleting..." until the request settles, then the row disappears with the toast (optimistic cache update) and the list reconciles with the server. The dialog is held deliberately — Radix closes on action click by default, which dismissed the only pending state and left the row looking untouched while the delete was still in flight
- Empty bucket shows "No files found" with upload prompt
- See: [File Browser](features/file-browser.md)

## View Dashboard

- User navigates to `/` (home)
- `useMissions()` and `useFileStats()` load in parallel
- Metric cards show: total missions, completed reconstructions, bucket storage used, and the overall **write amplification** (Σ output ÷ Σ input bytes)
- The amplification chart plots input vs output MB per reconstructed mission
- The recent-missions table links each row to its `/missions/<id>` detail page
- Empty state: "No missions yet" messages
- See: [Dashboard](features/dashboard.md)

## Change Preferences

- User navigates to `/settings`
- A banner at the top states that the page is mostly a demonstration: only Theme is wired up for real, the rest showcases what a settings page can look like when you adapt the kit
- **Theme** (real): editing it and saving applies it immediately and persists it (`next-themes`), and the header's theme toggle drives the same state
- **Profile and preference fields** (demo): Display name, Bio, Default file view (Tree/List/Grid), Email me on every upload, Warn me when approaching quota + threshold. Each is labelled "Demo field", persists to `localStorage` only, and drives no behaviour — there is no account system, mailer, quota banner, activity log, or List/Grid view behind them yet
- Saving reports honestly: a success toast that separates the real theme change from the locally-stored demo values, or a warning toast if the browser blocked storage (theme still changes). It never claims a save that did not happen — the original page toasted "Settings saved" for fields that changed nothing
- Danger Zone actions are a demo — no real delete runs
- See: [Settings](features/settings.md)

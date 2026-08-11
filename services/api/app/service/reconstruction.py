"""OpenDroneMap reconstruction pipeline — the marquee action.

Runs a real pipeline against the local NodeODM engine and B2:
download the mission's image set from B2 → submit to NodeODM → poll progress →
download the result assets → write the (far larger) outputs back to B2 →
persist the terminal status onto the manifest.

Live progress is tracked in a module-local, ``threading.Lock``-guarded in-memory
registry (mirrors the starter's counter/cache pattern). Milestone and terminal
states are additionally persisted to the B2 manifest so status survives a
restart.
"""

import logging
import tempfile
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

from app.repo import (
    OdmEngineError,
    download_assets,
    download_prefix_to_dir,
    odm_status,
    outputs_prefix,
    submit,
    upload_dir_to_prefix,
)
from app.service import missions as missions_service
from app.types import Mission, MissionState, MissionStatus, OutputProduct

logger = logging.getLogger(__name__)

# How often the pipeline polls NodeODM for task progress.
POLL_INTERVAL_SECONDS = 3.0

_lock = threading.Lock()
_registry: dict[str, MissionStatus] = {}


class ReconstructionConflictError(Exception):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


def _now() -> datetime:
    return datetime.now(UTC)


def _reset_state() -> None:
    """Test helper: forget every tracked job."""
    with _lock:
        _registry.clear()


def _record(mission_id: str, status: MissionStatus, *, persist: bool = False) -> None:
    with _lock:
        _registry[mission_id] = status
    if persist:
        try:
            missions_service.set_status(mission_id, status)
        except Exception:
            # Persistence is best-effort; the live registry stays authoritative.
            logger.warning("Failed to persist mission status", exc_info=True)


def _status(state: MissionState, stage: str, **kw) -> MissionStatus:
    return MissionStatus(state=state, stage=stage, updated_at=_now(), **kw)


def build_odm_options(mission: Mission) -> dict:
    """Map the mission's quality preset + products to NodeODM options.

    Draft uses the fast/low presets so a demo run finishes in minutes; higher
    presets trade time for quality. Everything is CPU-based — no GPU flags.
    """
    presets = {
        "draft": {"fast-orthophoto": True, "pc-quality": "lowest", "feature-quality": "low"},
        "standard": {"pc-quality": "medium", "feature-quality": "medium"},
        "high": {"pc-quality": "high", "feature-quality": "high"},
    }
    options: dict = dict(presets.get(mission.quality.value, presets["standard"]))
    products = set(mission.products)
    options["dsm"] = OutputProduct.dem in products
    options["skip-3dmodel"] = OutputProduct.mesh not in products
    if mission.dem_resolution_cm:
        options["dem-resolution"] = mission.dem_resolution_cm
    return options


def get_status(mission_id: str) -> MissionStatus:
    """Live status from the registry, falling back to the persisted manifest."""
    with _lock:
        live = _registry.get(mission_id)
    if live is not None:
        return live
    return missions_service.get_mission(mission_id).status


def start_run(mission_id: str) -> MissionStatus:
    """Validate and kick off a background reconstruction. Returns queued status."""
    mission = missions_service.get_mission(mission_id)
    if mission.status.state in (MissionState.queued, MissionState.running):
        raise ReconstructionConflictError("Mission is already running")
    if mission.stats is None or mission.stats.input_count == 0:
        raise ReconstructionConflictError(
            "Mission has no input images — upload drone JPEGs first"
        )
    queued = _status(MissionState.queued, "Queued for reconstruction")
    _record(mission_id, queued, persist=True)
    threading.Thread(
        target=run_pipeline, args=(mission,), name=f"odm-run:{mission_id}", daemon=True
    ).start()
    return queued


def run_pipeline(mission: Mission) -> None:
    """Execute the full pipeline. Runs in a background thread (or directly in tests)."""
    mission_id = mission.id
    tmp = Path(tempfile.mkdtemp(prefix=f"odm-{mission_id}-"))
    try:
        _record(mission_id, _status(MissionState.running, "Downloading images from B2"))
        image_dir = tmp / "images"
        images = download_prefix_to_dir(mission.image_prefix, str(image_dir))
        if not images:
            raise OdmEngineError("No input images found in the mission prefix")

        _record(mission_id, _status(MissionState.running, "Submitting to NodeODM"))
        task_uuid = submit(images, build_odm_options(mission), mission.name)
        _record(
            mission_id,
            _status(MissionState.running, "Reconstructing", task_uuid=task_uuid),
            persist=True,
        )

        _poll_until_done(mission_id, task_uuid)
        _finalize(mission_id, task_uuid, tmp)
    except (OdmEngineError, RuntimeError) as e:
        logger.warning("Reconstruction failed for %s: %s", mission_id, e)
        _record(
            mission_id,
            _status(MissionState.failed, "Failed", error=str(e)),
            persist=True,
        )
    finally:
        _cleanup(tmp)


def _poll_until_done(mission_id: str, task_uuid: str) -> None:
    """Poll NodeODM until the task leaves the running/queued states."""
    while True:
        info = odm_status(task_uuid)
        state_name = info["status"].upper()
        progress = info["progress"]
        if state_name in ("COMPLETED",):
            _record(
                mission_id,
                _status(MissionState.running, "Downloading outputs", progress=100.0,
                        task_uuid=task_uuid),
            )
            return
        if state_name in ("FAILED", "CANCELED"):
            raise OdmEngineError(info.get("last_error") or f"NodeODM task {state_name}")
        _record(
            mission_id,
            _status(MissionState.running, "Reconstructing", progress=progress,
                    task_uuid=task_uuid),
        )
        time.sleep(POLL_INTERVAL_SECONDS)


def _finalize(mission_id: str, task_uuid: str, tmp: Path) -> None:
    """Download assets and write them back to B2 under the outputs prefix."""
    out_dir = tmp / "outputs"
    download_assets(task_uuid, str(out_dir))
    written = upload_dir_to_prefix(str(out_dir), outputs_prefix(mission_id))
    _record(
        mission_id,
        _status(
            MissionState.completed,
            f"Completed — {len(written)} artifacts written to B2",
            progress=100.0,
            task_uuid=task_uuid,
        ),
        persist=True,
    )


def _cleanup(tmp: Path) -> None:
    import shutil

    shutil.rmtree(tmp, ignore_errors=True)

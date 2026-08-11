"""Mission lifecycle orchestration.

The Mission is the primary entity; its manifest in B2 is the only datastore.
This module owns create/read/update/delete plus the write-amplification stats
and the mission-scoped artifact listing. It never touches boto3 or pyodm
directly — those stay behind the repo adapters.
"""

import logging
import re
import uuid
from datetime import UTC, datetime

from app.repo import (
    delete_mission_objects,
    get_manifest,
    images_prefix,
    list_manifests,
    list_objects_under,
    mission_prefix,
    outputs_prefix,
    put_manifest,
)
from app.types import (
    Artifact,
    ArtifactKind,
    Mission,
    MissionCreate,
    MissionState,
    MissionStats,
    MissionStatus,
    MissionUpdate,
)
from app.types.formatting import humanize_bytes

logger = logging.getLogger(__name__)

_MANIFEST_NAME = "mission.json"
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_ACTIVE_STATES = {MissionState.queued, MissionState.running}


class MissionKeyError(Exception):
    def __init__(self, detail: str = "Invalid mission id"):
        self.detail = detail
        super().__init__(detail)


class MissionNotFoundError(Exception):
    def __init__(self, detail: str = "Mission not found"):
        self.detail = detail
        super().__init__(detail)


class MissionConflictError(Exception):
    """Raised when an edit/delete is attempted on a running mission."""

    def __init__(self, detail: str = "Mission is running"):
        self.detail = detail
        super().__init__(detail)


def _now() -> datetime:
    return datetime.now(UTC)


def validate_mission_id(mission_id: str) -> None:
    if not mission_id or not _ID_RE.match(mission_id) or ".." in mission_id:
        raise MissionKeyError()


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:40] or "mission"


def generate_id(name: str) -> str:
    return f"{_slugify(name)}-{uuid.uuid4().hex[:8]}"


def classify_artifact(key: str) -> ArtifactKind:
    """Best-effort geospatial artifact classification from the object key."""
    lower = key.lower()
    name = lower.rsplit("/", 1)[-1]
    ext = name.rsplit(".", 1)[-1] if "." in name else ""
    if "/images/" in lower:
        return ArtifactKind.image
    if "orthophoto" in name or "orthomosaic" in name:
        return ArtifactKind.orthomosaic
    if "dsm" in name or "dtm" in name or name.startswith("dem") or "_dem" in name:
        return ArtifactKind.dem
    if ext in ("las", "laz", "ply"):
        return ArtifactKind.point_cloud
    if ext in ("obj", "glb", "gltf", "mtl", "b3dm"):
        return ArtifactKind.mesh
    if "texture" in name or (ext in ("png", "jpg", "jpeg") and "model" in lower):
        return ArtifactKind.texture
    if ext in ("tif", "tiff"):
        return ArtifactKind.orthomosaic
    if ext in ("pdf", "html", "json", "txt", "log", "csv"):
        return ArtifactKind.report
    return ArtifactKind.other


def compute_stats(mission_id: str) -> MissionStats:
    """Input vs output byte accounting straight from the bucket."""
    inputs = list_objects_under(images_prefix(mission_id))
    outputs = list_objects_under(outputs_prefix(mission_id))
    in_bytes = sum(o["Size"] for o in inputs)
    out_bytes = sum(o["Size"] for o in outputs)
    ratio = round(out_bytes / in_bytes, 2) if in_bytes else 0.0
    return MissionStats(
        input_count=len(inputs),
        input_bytes=in_bytes,
        input_human=humanize_bytes(in_bytes),
        output_count=len(outputs),
        output_bytes=out_bytes,
        output_human=humanize_bytes(out_bytes),
        amplification_ratio=ratio,
    )


def _hydrate(data: dict) -> Mission:
    """Build a Mission from a manifest, refreshing stats from live bucket sizes."""
    mission = Mission(**data)
    mission.stats = compute_stats(mission.id)
    return mission


def _save(mission: Mission) -> None:
    put_manifest(mission.id, mission.model_dump(mode="json"))


def create_mission(payload: MissionCreate) -> Mission:
    mission_id = generate_id(payload.name)
    now = _now()
    prefix = payload.image_prefix or images_prefix(mission_id)
    mission = Mission(
        id=mission_id,
        name=payload.name,
        description=payload.description,
        capture_date=payload.capture_date,
        quality=payload.quality,
        products=payload.products,
        dem_resolution_cm=payload.dem_resolution_cm,
        image_prefix=prefix,
        status=MissionStatus(state=MissionState.draft, stage="Created", updated_at=now),
        stats=compute_stats(mission_id),
        created_at=now,
        updated_at=now,
    )
    _save(mission)
    logger.info("Mission created: id=%s", mission_id)
    return mission


def get_mission(mission_id: str) -> Mission:
    validate_mission_id(mission_id)
    data = get_manifest(mission_id)
    if data is None:
        raise MissionNotFoundError()
    return _hydrate(data)


def list_missions() -> list[Mission]:
    missions = [_hydrate(data) for data in list_manifests()]
    missions.sort(key=lambda m: m.created_at, reverse=True)
    return missions


def update_mission(mission_id: str, payload: MissionUpdate) -> Mission:
    mission = get_mission(mission_id)
    if mission.status.state in _ACTIVE_STATES:
        raise MissionConflictError("Cannot edit a mission while it is running")
    fields = payload.model_dump(exclude_unset=True)
    updated = mission.model_copy(update=fields)
    updated.updated_at = _now()
    _save(updated)
    logger.info("Mission updated: id=%s fields=%s", mission_id, list(fields))
    return _hydrate(updated.model_dump(mode="json"))


def delete_mission(mission_id: str) -> int:
    validate_mission_id(mission_id)
    # Confirm it exists (surfaces a clean 404 instead of a silent no-op delete).
    if get_manifest(mission_id) is None:
        raise MissionNotFoundError()
    deleted = delete_mission_objects(mission_id)
    logger.info("Mission deleted: id=%s objects=%d", mission_id, deleted)
    return deleted


def set_status(mission_id: str, status: MissionStatus) -> None:
    """Persist a milestone/terminal status onto the manifest (survives restart).

    Only the status block is rewritten; live per-tick progress lives in the
    reconstruction job registry, not in B2.
    """
    data = get_manifest(mission_id)
    if data is None:
        raise MissionNotFoundError()
    data["status"] = status.model_dump(mode="json")
    data["updated_at"] = _now().isoformat()
    put_manifest(mission_id, data)


def list_artifacts(mission_id: str) -> list[Artifact]:
    """Every object under the mission prefix except the manifest itself."""
    validate_mission_id(mission_id)
    if get_manifest(mission_id) is None:
        raise MissionNotFoundError()
    manifest_key = f"{mission_prefix(mission_id)}{_MANIFEST_NAME}"
    artifacts: list[Artifact] = []
    for obj in list_objects_under(mission_prefix(mission_id)):
        key = obj["Key"]
        if key == manifest_key or key.endswith("/"):
            continue
        artifacts.append(
            Artifact(
                key=key,
                filename=key.rsplit("/", 1)[-1],
                kind=classify_artifact(key),
                size_bytes=obj["Size"],
                size_human=humanize_bytes(obj["Size"]),
            )
        )
    artifacts.sort(key=lambda a: a.key)
    return artifacts

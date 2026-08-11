"""Domain models for the Mission entity — the primary resource.

A Mission is a photogrammetry job whose sole datastore is a JSON manifest in B2
at ``missions/<id>/mission.json`` (no database). Inputs live under
``missions/<id>/images/`` and generated artifacts under
``missions/<id>/outputs/``.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class QualityPreset(StrEnum):
    """Finite reconstruction quality presets → ODM flag bundles."""

    draft = "draft"
    standard = "standard"
    high = "high"


class OutputProduct(StrEnum):
    """Finite set of products a reconstruction can emit."""

    orthomosaic = "orthomosaic"
    dem = "dem"
    point_cloud = "point_cloud"
    mesh = "mesh"


class MissionState(StrEnum):
    draft = "draft"  # created, no run yet
    queued = "queued"  # run requested, inputs downloading / submitting
    running = "running"  # NodeODM is processing
    completed = "completed"  # outputs written back to B2
    failed = "failed"  # engine or transfer error


class ArtifactKind(StrEnum):
    image = "image"
    orthomosaic = "orthomosaic"
    dem = "dem"
    point_cloud = "point_cloud"
    mesh = "mesh"
    texture = "texture"
    report = "report"
    other = "other"


class Artifact(BaseModel):
    key: str
    filename: str
    kind: ArtifactKind
    size_bytes: int
    size_human: str
    url: str | None = None


class MissionStats(BaseModel):
    """Write-amplification analytics computed from real bucket sizes."""

    input_count: int
    input_bytes: int
    input_human: str
    output_count: int
    output_bytes: int
    output_human: str
    # output_bytes / input_bytes — the whole point of the sample. 0.0 when there
    # are no inputs yet.
    amplification_ratio: float


class MissionStatus(BaseModel):
    state: MissionState
    progress: float = 0.0  # 0..100
    stage: str = ""  # human-readable current stage
    task_uuid: str | None = None
    error: str | None = None
    updated_at: datetime


class Mission(BaseModel):
    id: str
    name: str
    description: str = ""
    capture_date: str | None = None  # ISO date (YYYY-MM-DD)
    quality: QualityPreset
    products: list[OutputProduct]
    dem_resolution_cm: int | None = None
    image_prefix: str  # missions/<id>/images/
    status: MissionStatus
    stats: MissionStats | None = None
    created_at: datetime
    updated_at: datetime


class MissionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = ""
    capture_date: str | None = None
    quality: QualityPreset = QualityPreset.standard
    products: list[OutputProduct] = Field(
        default_factory=lambda: [OutputProduct.orthomosaic, OutputProduct.dem]
    )
    dem_resolution_cm: int | None = None
    # Optional: point the mission at an existing bucket prefix that already
    # holds the drone JPEGs. Defaults to the mission's own images/ prefix.
    image_prefix: str | None = None


class MissionUpdate(BaseModel):
    """Partial update — only applied while the mission is not running."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    capture_date: str | None = None
    quality: QualityPreset | None = None
    products: list[OutputProduct] | None = None
    dem_resolution_cm: int | None = None

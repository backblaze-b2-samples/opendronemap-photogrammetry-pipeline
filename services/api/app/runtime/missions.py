import logging

# Sync `def` handlers on purpose: the service calls are blocking boto3, so
# Starlette runs them in its threadpool (see runtime/files.py rationale).
from fastapi import APIRouter, HTTPException, status

from app.service.missions import (
    MissionConflictError,
    MissionKeyError,
    MissionNotFoundError,
    create_mission,
    delete_mission,
    get_mission,
    images_prefix,
    list_artifacts,
    list_missions,
    update_mission,
    validate_mission_id,
)
from app.service.upload import UploadError, create_presigned_upload, verify_upload
from app.types import (
    Artifact,
    Mission,
    MissionCreate,
    MissionUpdate,
    PresignUploadRequest,
    PresignUploadResponse,
    VerifyUploadRequest,
)
from app.types.upload import FileUploadResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def _raise_for(exc: Exception) -> None:
    """Translate a mission service error to the right HTTP status."""
    if isinstance(exc, MissionKeyError):
        raise HTTPException(status_code=400, detail=exc.detail) from None
    if isinstance(exc, MissionNotFoundError):
        raise HTTPException(status_code=404, detail=exc.detail) from None
    if isinstance(exc, MissionConflictError):
        raise HTTPException(status_code=409, detail=exc.detail) from None
    raise HTTPException(status_code=502, detail="Storage backend error") from None


@router.get("/missions", response_model=list[Mission])
def list_missions_endpoint():
    try:
        return list_missions()
    except RuntimeError as e:
        _raise_for(e)


@router.post("/missions", response_model=Mission, status_code=status.HTTP_201_CREATED)
def create_mission_endpoint(payload: MissionCreate):
    try:
        return create_mission(payload)
    except RuntimeError as e:
        _raise_for(e)


@router.get("/missions/{mission_id}", response_model=Mission)
def get_mission_endpoint(mission_id: str):
    try:
        return get_mission(mission_id)
    except (MissionKeyError, MissionNotFoundError, RuntimeError) as e:
        _raise_for(e)


@router.patch("/missions/{mission_id}", response_model=Mission)
def update_mission_endpoint(mission_id: str, payload: MissionUpdate):
    try:
        return update_mission(mission_id, payload)
    except (
        MissionKeyError,
        MissionNotFoundError,
        MissionConflictError,
        RuntimeError,
    ) as e:
        _raise_for(e)


@router.delete("/missions/{mission_id}")
def delete_mission_endpoint(mission_id: str):
    try:
        deleted = delete_mission(mission_id)
    except (MissionKeyError, MissionNotFoundError, RuntimeError) as e:
        _raise_for(e)
    logger.info("Mission deleted via API: id=%s objects=%d", mission_id, deleted)
    return {"deleted": True, "id": mission_id, "objects_deleted": deleted}


@router.get("/missions/{mission_id}/artifacts", response_model=list[Artifact])
def list_artifacts_endpoint(mission_id: str):
    try:
        return list_artifacts(mission_id)
    except (MissionKeyError, MissionNotFoundError, RuntimeError) as e:
        _raise_for(e)


@router.post("/missions/{mission_id}/images/presign", response_model=PresignUploadResponse)
def presign_mission_image(mission_id: str, req: PresignUploadRequest):
    """Presigned PUT that lands a drone JPEG under the mission's images prefix."""
    try:
        get_mission(mission_id)  # 404s a non-existent mission before signing
    except (MissionKeyError, MissionNotFoundError, RuntimeError) as e:
        _raise_for(e)
    try:
        return create_presigned_upload(
            filename=req.filename,
            content_type=req.content_type,
            size_bytes=req.size_bytes,
            key_prefix=images_prefix(mission_id),
        )
    except UploadError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None


@router.post("/missions/{mission_id}/images/verify", response_model=FileUploadResponse)
def verify_mission_image(mission_id: str, req: VerifyUploadRequest):
    """Confirm a drone JPEG just uploaded directly to the mission's prefix."""
    validate_mission_id(mission_id)
    try:
        return verify_upload(req.key, key_prefix=images_prefix(mission_id))
    except UploadError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    except MissionKeyError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None

import logging

from fastapi import APIRouter, HTTPException, status

from app.service.missions import MissionKeyError, MissionNotFoundError
from app.service.reconstruction import (
    ReconstructionConflictError,
    get_status,
    start_run,
)
from app.types import MissionStatus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/missions/{mission_id}/run",
    response_model=MissionStatus,
    status_code=status.HTTP_202_ACCEPTED,
)
def run_mission_endpoint(mission_id: str):
    """Kick off the reconstruction (the marquee action). Returns 202 + queued status."""
    try:
        result = start_run(mission_id)
    except MissionKeyError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except MissionNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    except ReconstructionConflictError as e:
        raise HTTPException(status_code=409, detail=e.detail) from None
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Storage backend error") from None
    logger.info("Reconstruction queued: id=%s", mission_id)
    return result


@router.get("/missions/{mission_id}/status", response_model=MissionStatus)
def mission_status_endpoint(mission_id: str):
    try:
        return get_status(mission_id)
    except MissionKeyError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except MissionNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Storage backend error") from None

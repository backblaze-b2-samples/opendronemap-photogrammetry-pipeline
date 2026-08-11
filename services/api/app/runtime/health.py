from fastapi import APIRouter

from app.config import settings
from app.repo import check_connectivity

router = APIRouter()


# Sync `def` so the blocking B2 connectivity check runs in Starlette's
# threadpool rather than on the event loop (see runtime/files.py rationale).
@router.get("/health")
def health():
    b2_ok = check_connectivity()
    return {
        "status": "healthy" if b2_ok else "degraded",
        "b2_connected": b2_ok,
    }


@router.get("/config")
def config():
    """Non-secret bucket coordinates the UI needs to build S3 URIs for artifacts.

    Bucket name and region are not credentials; they let the mission artifact
    explorer render a copy-able ``s3://<bucket>/<key>`` URI for downstream GIS
    pipelines without hardcoding the bucket in the frontend.
    """
    return {
        "bucket_name": settings.b2_bucket_name,
        "region": settings.b2_region,
    }

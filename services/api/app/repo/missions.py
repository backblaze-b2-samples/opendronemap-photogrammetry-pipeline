"""B2-backed persistence for Mission manifests and their artifacts.

The mission manifest is the ONLY datastore (no database): one JSON object per
mission at ``missions/<id>/mission.json``. boto3 stays confined to this repo
layer; the cached S3 client is reused from ``b2_client`` for connection pooling.
"""

import json

from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings
from app.repo.b2_client import get_s3_client
from app.repo.list_cache import invalidate as _invalidate_list_cache

MISSIONS_PREFIX = "missions/"
MANIFEST_NAME = "mission.json"


def mission_prefix(mission_id: str) -> str:
    return f"{MISSIONS_PREFIX}{mission_id}/"


def images_prefix(mission_id: str) -> str:
    return f"{mission_prefix(mission_id)}images/"


def outputs_prefix(mission_id: str) -> str:
    return f"{mission_prefix(mission_id)}outputs/"


def manifest_key(mission_id: str) -> str:
    return f"{mission_prefix(mission_id)}{MANIFEST_NAME}"


def put_manifest(mission_id: str, data: dict) -> None:
    """Write (or overwrite) a mission manifest as JSON. Raises RuntimeError."""
    client = get_s3_client()
    body = json.dumps(data, indent=2, sort_keys=True, default=str).encode("utf-8")
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=manifest_key(mission_id),
            Body=body,
            ContentType="application/json",
        )
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 manifest write failed for '{mission_id}': {e}") from e
    _invalidate_list_cache()


def get_manifest(mission_id: str) -> dict | None:
    """Read a mission manifest. Returns None if it does not exist."""
    client = get_s3_client()
    try:
        response = client.get_object(
            Bucket=settings.b2_bucket_name, Key=manifest_key(mission_id)
        )
        return json.loads(response["Body"].read())
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return None
        raise RuntimeError(f"B2 manifest read failed for '{mission_id}': {e}") from e


def list_objects_under(prefix: str) -> list[dict]:
    """Every object under `prefix` (paginated). Raises RuntimeError on failure."""
    client = get_s3_client()
    contents: list[dict] = []
    kwargs: dict = {"Bucket": settings.b2_bucket_name, "Prefix": prefix, "MaxKeys": 1000}
    try:
        while True:
            response = client.list_objects_v2(**kwargs)
            contents.extend(response.get("Contents", []))
            if not response.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = response["NextContinuationToken"]
    except ClientError as e:
        raise RuntimeError(f"B2 list failed for '{prefix}': {e}") from e
    return contents


def list_manifests() -> list[dict]:
    """Load every mission manifest in the bucket (one object per mission)."""
    manifests: list[dict] = []
    for obj in list_objects_under(MISSIONS_PREFIX):
        key = obj["Key"]
        if not key.endswith(f"/{MANIFEST_NAME}"):
            continue
        # key == missions/<id>/mission.json → id is the middle segment.
        mission_id = key[len(MISSIONS_PREFIX) : -(len(MANIFEST_NAME) + 1)]
        data = get_manifest(mission_id)
        if data is not None:
            manifests.append(data)
    return manifests


def delete_mission_objects(mission_id: str) -> int:
    """Delete every object under ``missions/<id>/`` — and NOTHING else.

    The sweep is confined to the single mission prefix: it lists only that
    prefix and issues ``delete_objects`` for exactly those keys. It can never
    widen into a bucket-wide wipe. Returns the number of objects deleted.
    """
    prefix = mission_prefix(mission_id)
    contents = list_objects_under(prefix)
    keys = [{"Key": obj["Key"]} for obj in contents]
    if not keys:
        return 0
    client = get_s3_client()
    deleted = 0
    try:
        for batch_start in range(0, len(keys), 1000):
            batch = keys[batch_start : batch_start + 1000]
            client.delete_objects(
                Bucket=settings.b2_bucket_name, Delete={"Objects": batch}
            )
            deleted += len(batch)
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 delete failed for '{prefix}': {e}") from e
    _invalidate_list_cache()
    return deleted

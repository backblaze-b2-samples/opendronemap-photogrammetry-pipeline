"""Bulk B2 transfer helpers for the reconstruction pipeline.

The write-amplification workhorse: streams a mission's image set down to a temp
dir for OpenDroneMap, and writes the (far larger) GeoTIFF/DEM/LAS/mesh outputs
back to B2 with boto3's managed multipart transfer (``upload_file`` +
``TransferConfig``). boto3 stays confined to this repo layer; the cached S3
client is reused from ``b2_client``.
"""

import mimetypes
from pathlib import Path

from boto3.s3.transfer import TransferConfig
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings
from app.repo.b2_client import get_s3_client
from app.repo.list_cache import invalidate as _invalidate_list_cache
from app.repo.missions import list_objects_under

# Managed multipart: parts above the threshold upload in parallel chunks, which
# is what makes the large output artifacts (orthomosaics, point clouds) write
# efficiently to B2.
_CHUNK_BYTES = 16 * 1024 * 1024
_TRANSFER = TransferConfig(
    multipart_threshold=_CHUNK_BYTES,
    multipart_chunksize=_CHUNK_BYTES,
    max_concurrency=4,
    use_threads=True,
)


def download_prefix_to_dir(prefix: str, dest_dir: str) -> list[str]:
    """Stream every object under `prefix` to `dest_dir`. Returns local paths.

    Only leaf objects are downloaded (keys ending in ``/`` — folder markers —
    are skipped). Raises RuntimeError on any S3 failure.
    """
    client = get_s3_client()
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    try:
        for obj in list_objects_under(prefix):
            key = obj["Key"]
            if key.endswith("/"):
                continue
            local = dest / Path(key).name
            client.download_file(settings.b2_bucket_name, key, str(local))
            paths.append(str(local))
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 download failed for prefix '{prefix}': {e}") from e
    return paths


def upload_file_managed(local_path: str, key: str) -> int:
    """Upload one file to B2 via managed multipart. Returns bytes written."""
    client = get_s3_client()
    content_type, _ = mimetypes.guess_type(key)
    extra = {"ContentType": content_type} if content_type else None
    try:
        client.upload_file(
            local_path,
            settings.b2_bucket_name,
            key,
            ExtraArgs=extra,
            Config=_TRANSFER,
        )
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 upload failed for '{key}': {e}") from e
    return Path(local_path).stat().st_size


def upload_dir_to_prefix(src_dir: str, prefix: str) -> list[dict]:
    """Upload every file under `src_dir` to B2 under `prefix`.

    Preserves the relative directory layout in the key. Returns one
    ``{"key", "size_bytes"}`` dict per uploaded object. Raises RuntimeError.
    """
    src = Path(src_dir)
    written: list[dict] = []
    for path in sorted(src.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(src).as_posix()
        key = f"{prefix}{rel}"
        size = upload_file_managed(str(path), key)
        written.append({"key": key, "size_bytes": size})
    if written:
        _invalidate_list_cache()
    return written

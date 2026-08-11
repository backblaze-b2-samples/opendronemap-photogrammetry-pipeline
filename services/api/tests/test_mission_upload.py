"""Mission-scoped image ingest (presigned PUT under missions/<id>/images/)."""

import pytest

from app.repo.missions import images_prefix
from app.runtime import missions as missions_runtime
from app.service import missions as missions_service
from app.service import upload as upload_service
from tests.test_missions import FakeBucket


@pytest.fixture
def fake_b2(monkeypatch):
    bucket = FakeBucket()
    for name in ("put_manifest", "get_manifest", "list_manifests",
                 "list_objects_under", "delete_mission_objects"):
        monkeypatch.setattr(missions_service, name, getattr(bucket, name))
    return bucket


@pytest.mark.asyncio
async def test_presign_scopes_key_to_mission_images(client, fake_b2, monkeypatch):
    created = (await client.post("/missions", json={"name": "ingest"})).json()
    mid = created["id"]
    monkeypatch.setattr(
        missions_runtime, "create_presigned_upload", upload_service.create_presigned_upload
    )
    monkeypatch.setattr(
        upload_service, "generate_presigned_upload",
        lambda key, ct, size, expires: f"https://b2.example/{key}",
    )

    resp = await client.post(
        f"/missions/{mid}/images/presign",
        json={"filename": "DJI_0001.jpg", "content_type": "image/jpeg", "size_bytes": 1234},
    )
    assert resp.status_code == 200
    key = resp.json()["key"]
    assert key.startswith(images_prefix(mid))
    assert key.endswith("DJI_0001.jpg")


@pytest.mark.asyncio
async def test_verify_rejects_key_outside_mission_prefix(client, fake_b2):
    created = (await client.post("/missions", json={"name": "guard"})).json()
    resp = await client.post(
        f"/missions/{created['id']}/images/verify",
        json={"key": "uploads/somewhere-else.jpg"},
    )
    assert resp.status_code == 400

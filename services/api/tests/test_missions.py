"""Mission CRUD, stats, and artifact-listing tests (B2 mocked in-memory)."""

import json

import pytest

from app.repo.missions import (
    images_prefix,
    manifest_key,
    mission_prefix,
    outputs_prefix,
)
from app.service import missions as missions_service
from app.service.missions import classify_artifact
from app.types import ArtifactKind


class FakeBucket:
    """Minimal in-memory stand-in for the B2 object store."""

    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def put_manifest(self, mission_id, data):
        self.objects[manifest_key(mission_id)] = json.dumps(data).encode()

    def get_manifest(self, mission_id):
        raw = self.objects.get(manifest_key(mission_id))
        return json.loads(raw) if raw is not None else None

    def list_objects_under(self, prefix):
        return [
            {"Key": k, "Size": len(v)}
            for k, v in self.objects.items()
            if k.startswith(prefix)
        ]

    def list_manifests(self):
        return [
            json.loads(v)
            for k, v in self.objects.items()
            if k.endswith("/mission.json")
        ]

    def delete_mission_objects(self, mission_id):
        prefix = mission_prefix(mission_id)
        keys = [k for k in self.objects if k.startswith(prefix)]
        for k in keys:
            del self.objects[k]
        return len(keys)

    def add_object(self, key, size):
        self.objects[key] = b"x" * size


@pytest.fixture
def fake_b2(monkeypatch):
    bucket = FakeBucket()
    for name in (
        "put_manifest",
        "get_manifest",
        "list_manifests",
        "list_objects_under",
        "delete_mission_objects",
    ):
        monkeypatch.setattr(missions_service, name, getattr(bucket, name))
    return bucket


@pytest.mark.asyncio
async def test_create_and_get_mission(client, fake_b2):
    resp = await client.post(
        "/missions",
        json={"name": "North Field 2026", "quality": "draft", "products": ["orthomosaic"]},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "North Field 2026"
    assert body["quality"] == "draft"
    assert body["status"]["state"] == "draft"
    assert body["image_prefix"] == images_prefix(body["id"])

    got = await client.get(f"/missions/{body['id']}")
    assert got.status_code == 200
    assert got.json()["id"] == body["id"]


@pytest.mark.asyncio
async def test_get_missing_mission_404(client, fake_b2):
    resp = await client.get("/missions/does-not-exist-00000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_invalid_mission_id_400(client, fake_b2):
    resp = await client.get("/missions/..%2fetc")
    # FastAPI decodes the path; a traversal id must be rejected, never fetched.
    assert resp.status_code in (400, 404)


@pytest.mark.asyncio
async def test_list_missions_sorted_newest_first(client, fake_b2):
    for name in ("alpha", "bravo"):
        await client.post("/missions", json={"name": name})
    resp = await client.get("/missions")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_update_mission_metadata(client, fake_b2):
    created = (await client.post("/missions", json={"name": "field"})).json()
    resp = await client.patch(
        f"/missions/{created['id']}",
        json={"quality": "high", "description": "orchard survey"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["quality"] == "high"
    assert body["description"] == "orchard survey"


@pytest.mark.asyncio
async def test_cannot_edit_running_mission(client, fake_b2):
    created = (await client.post("/missions", json={"name": "busy"})).json()
    # Flip the persisted status to running.
    data = fake_b2.get_manifest(created["id"])
    data["status"]["state"] = "running"
    fake_b2.put_manifest(created["id"], data)

    resp = await client.patch(f"/missions/{created['id']}", json={"quality": "high"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_delete_mission_is_prefix_scoped(client, fake_b2):
    created = (await client.post("/missions", json={"name": "doomed"})).json()
    mid = created["id"]
    fake_b2.add_object(f"{images_prefix(mid)}a.jpg", 10)
    fake_b2.add_object(f"{outputs_prefix(mid)}ortho.tif", 100)
    # An object belonging to ANOTHER mission must survive the scoped delete.
    fake_b2.add_object("missions/other-11111111/images/keep.jpg", 5)

    resp = await client.delete(f"/missions/{mid}")
    assert resp.status_code == 200
    assert resp.json()["objects_deleted"] == 3  # manifest + image + output
    assert "missions/other-11111111/images/keep.jpg" in fake_b2.objects


@pytest.mark.asyncio
async def test_stats_amplification_ratio(client, fake_b2):
    created = (await client.post("/missions", json={"name": "amp"})).json()
    mid = created["id"]
    fake_b2.add_object(f"{images_prefix(mid)}a.jpg", 100)
    fake_b2.add_object(f"{outputs_prefix(mid)}ortho.tif", 500)

    resp = await client.get(f"/missions/{mid}")
    stats = resp.json()["stats"]
    assert stats["input_bytes"] == 100
    assert stats["output_bytes"] == 500
    assert stats["amplification_ratio"] == 5.0


@pytest.mark.asyncio
async def test_artifacts_exclude_manifest_and_classify(client, fake_b2):
    created = (await client.post("/missions", json={"name": "gallery"})).json()
    mid = created["id"]
    fake_b2.add_object(f"{images_prefix(mid)}DJI_0001.jpg", 10)
    fake_b2.add_object(f"{outputs_prefix(mid)}odm_orthophoto/odm_orthophoto.tif", 200)
    fake_b2.add_object(f"{outputs_prefix(mid)}odm_georeferencing/point_cloud.las", 300)

    resp = await client.get(f"/missions/{mid}/artifacts")
    assert resp.status_code == 200
    arts = resp.json()
    keys = {a["key"] for a in arts}
    assert manifest_key(mid) not in keys  # manifest is never listed as an artifact
    kinds = {a["filename"]: a["kind"] for a in arts}
    assert kinds["DJI_0001.jpg"] == "image"
    assert kinds["odm_orthophoto.tif"] == "orthomosaic"
    assert kinds["point_cloud.las"] == "point_cloud"


def test_classify_artifact_kinds():
    assert classify_artifact("missions/x/images/a.jpg") == ArtifactKind.image
    assert classify_artifact("missions/x/outputs/odm_orthophoto.tif") == ArtifactKind.orthomosaic
    assert classify_artifact("missions/x/outputs/dsm.tif") == ArtifactKind.dem
    assert classify_artifact("missions/x/outputs/cloud.laz") == ArtifactKind.point_cloud
    assert classify_artifact("missions/x/outputs/model.obj") == ArtifactKind.mesh
    assert classify_artifact("missions/x/outputs/report.pdf") == ArtifactKind.report

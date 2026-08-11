"""Reconstruction pipeline + run/status endpoint tests (pyodm + B2 mocked)."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.repo import OdmEngineError
from app.service import reconstruction
from app.types import (
    Mission,
    MissionState,
    MissionStats,
    MissionStatus,
    OutputProduct,
    QualityPreset,
)


def _mission(*, input_count=3, state=MissionState.draft, products=None) -> Mission:
    now = datetime.now(UTC)
    return Mission(
        id="field-abcd1234",
        name="field",
        quality=QualityPreset.draft,
        products=products or [OutputProduct.orthomosaic, OutputProduct.dem],
        image_prefix="missions/field-abcd1234/images/",
        status=MissionStatus(state=state, stage="", updated_at=now),
        stats=MissionStats(
            input_count=input_count,
            input_bytes=input_count * 100,
            input_human="x",
            output_count=0,
            output_bytes=0,
            output_human="0 B",
            amplification_ratio=0.0,
        ),
        created_at=now,
        updated_at=now,
    )


@pytest.fixture(autouse=True)
def reset_registry():
    reconstruction._reset_state()
    yield
    reconstruction._reset_state()


def test_build_odm_options_draft_maps_fast_presets():
    opts = reconstruction.build_odm_options(_mission())
    assert opts["fast-orthophoto"] is True
    assert opts["pc-quality"] == "lowest"
    assert opts["feature-quality"] == "low"
    assert opts["dsm"] is True  # dem requested → dsm on


def test_build_odm_options_skips_3dmodel_without_mesh():
    opts = reconstruction.build_odm_options(
        _mission(products=[OutputProduct.orthomosaic])
    )
    assert opts["skip-3dmodel"] is True


def test_run_pipeline_happy_path(monkeypatch):
    mission = _mission()
    persisted = []
    monkeypatch.setattr(reconstruction.missions_service, "set_status",
                        lambda mid, status: persisted.append(status.state))
    monkeypatch.setattr(reconstruction, "download_prefix_to_dir",
                        lambda prefix, dest: ["/tmp/a.jpg", "/tmp/b.jpg"])
    monkeypatch.setattr(reconstruction, "submit", lambda paths, opts, name: "task-1")
    monkeypatch.setattr(reconstruction, "odm_status",
                        lambda uuid: {"status": "COMPLETED", "progress": 100.0, "last_error": ""})

    def fake_download_assets(uuid, dest):
        Path(dest).mkdir(parents=True, exist_ok=True)
        (Path(dest) / "ortho.tif").write_bytes(b"x" * 500)
        return dest

    monkeypatch.setattr(reconstruction, "download_assets", fake_download_assets)
    monkeypatch.setattr(reconstruction, "upload_dir_to_prefix",
                        lambda src, prefix: [{"key": f"{prefix}ortho.tif", "size_bytes": 500}])

    reconstruction.run_pipeline(mission)

    assert reconstruction.get_status(mission.id).state == MissionState.completed
    assert MissionState.completed in persisted


def test_run_pipeline_engine_failure_marks_failed(monkeypatch):
    mission = _mission()
    monkeypatch.setattr(reconstruction.missions_service, "set_status", lambda mid, s: None)
    monkeypatch.setattr(reconstruction, "download_prefix_to_dir",
                        lambda prefix, dest: ["/tmp/a.jpg"])

    def boom(paths, opts, name):
        raise OdmEngineError("node offline")

    monkeypatch.setattr(reconstruction, "submit", boom)

    reconstruction.run_pipeline(mission)
    status = reconstruction.get_status(mission.id)
    assert status.state == MissionState.failed
    assert "node offline" in (status.error or "")


@pytest.mark.asyncio
async def test_run_endpoint_returns_202(client, monkeypatch):
    mission = _mission(input_count=5)
    monkeypatch.setattr(reconstruction.missions_service, "get_mission", lambda mid: mission)
    monkeypatch.setattr(reconstruction.missions_service, "set_status", lambda mid, s: None)
    # Don't spawn a real reconstruction thread against a live node.
    monkeypatch.setattr(reconstruction, "run_pipeline", lambda m: None)

    resp = await client.post(f"/missions/{mission.id}/run")
    assert resp.status_code == 202
    assert resp.json()["state"] == "queued"


@pytest.mark.asyncio
async def test_run_endpoint_409_without_images(client, monkeypatch):
    mission = _mission(input_count=0)
    monkeypatch.setattr(reconstruction.missions_service, "get_mission", lambda mid: mission)
    monkeypatch.setattr(reconstruction.missions_service, "set_status", lambda mid, s: None)

    resp = await client.post(f"/missions/{mission.id}/run")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_status_endpoint_reads_registry(client, monkeypatch):
    mission = _mission(input_count=5)
    monkeypatch.setattr(reconstruction.missions_service, "get_mission", lambda mid: mission)
    monkeypatch.setattr(reconstruction.missions_service, "set_status", lambda mid, s: None)
    monkeypatch.setattr(reconstruction, "run_pipeline", lambda m: None)

    await client.post(f"/missions/{mission.id}/run")
    resp = await client.get(f"/missions/{mission.id}/status")
    assert resp.status_code == 200
    assert resp.json()["state"] == "queued"

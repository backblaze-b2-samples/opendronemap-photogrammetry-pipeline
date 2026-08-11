"""Seed one runnable demo mission into B2.

Creates a Mission (a JSON manifest in B2) and uploads a small set of overlapping
drone JPEGs into its ``missions/<id>/images/`` prefix, so a fresh clone has
something to run a reconstruction against.

Default dataset: the OpenDroneMap "aukerman" sample (aerial drone imagery),
published by the OpenDroneMap project under CC-BY-SA 4.0
(https://github.com/OpenDroneMap/odm_data_aukerman). It is fetched as a GitHub
archive zip. The full set is large, so ``--limit`` caps how many images are
uploaded (default 30) to keep the demo small and fast. You can instead point at
a local folder of JPEGs with ``--images-dir`` or any other zip with
``--dataset-url``.

Requires B2 credentials in ``.env`` and network access for the default download.
It is optional and never run by ``pnpm verify``. Run it with the venv Python:

    services/api/.venv/bin/python services/api/scripts/seed_mission.py
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

# Load the repo-root .env so B2 credentials are available, matching main.py.
from dotenv import load_dotenv  # noqa: E402

load_dotenv(API_ROOT.parent.parent / ".env")

from app.repo import images_prefix, upload_file_managed  # noqa: E402
from app.service.missions import create_mission  # noqa: E402
from app.types import MissionCreate, OutputProduct, QualityPreset  # noqa: E402

DEFAULT_DATASET_URL = (
    "https://github.com/OpenDroneMap/odm_data_aukerman/archive/refs/heads/master.zip"
)
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def _out(message: str) -> None:
    sys.stdout.write(f"{message}\n")


def _collect_from_dir(images_dir: Path) -> list[Path]:
    return sorted(
        p for p in images_dir.rglob("*") if p.suffix.lower() in IMAGE_SUFFIXES
    )


def _collect_from_zip(url: str, workdir: Path) -> list[Path]:
    _out(f"Downloading dataset: {url}")
    archive = workdir / "dataset.zip"
    urllib.request.urlretrieve(url, archive)
    extract_dir = workdir / "extracted"
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(extract_dir)
    return _collect_from_dir(extract_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed a demo photogrammetry mission.")
    parser.add_argument("--name", default="demo-aukerman-field")
    parser.add_argument("--images-dir", type=Path, default=None)
    parser.add_argument("--dataset-url", default=DEFAULT_DATASET_URL)
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument(
        "--quality", choices=[q.value for q in QualityPreset], default="draft"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with tempfile.TemporaryDirectory(prefix="seed-mission-") as tmp:
        workdir = Path(tmp)
        if args.images_dir is not None:
            images = _collect_from_dir(args.images_dir)
        else:
            images = _collect_from_zip(args.dataset_url, workdir)

        if not images:
            _out("No images found — nothing to seed.")
            return 1
        images = images[: args.limit]

        mission = create_mission(
            MissionCreate(
                name=args.name,
                description="Seeded demo mission (OpenDroneMap aukerman sample).",
                quality=QualityPreset(args.quality),
                products=[OutputProduct.orthomosaic, OutputProduct.dem],
            )
        )
        _out(f"Created mission {mission.id}; uploading {len(images)} images...")

        prefix = images_prefix(mission.id)
        for image in images:
            upload_file_managed(str(image), f"{prefix}{image.name}")

        _out(f"Seeded mission '{mission.id}' with {len(images)} images.")
        _out(f"Open it at /missions/{mission.id}, then run the reconstruction.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

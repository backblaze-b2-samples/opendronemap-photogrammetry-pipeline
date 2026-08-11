"""Adapter for the OpenDroneMap engine via the ``pyodm`` NodeODM client.

This is the ONE place ``pyodm`` is imported: it is an external SDK, so — like
boto3 — it lives behind a repo adapter and never leaks into service/runtime.
``pyodm`` is a thin HTTP client that imports cleanly without a live node; unit
tests mock ``Node``. The engine is CPU-based and containerised (see the root
``docker-compose.yml``); there is no GPU/MPS path and none is required.
"""

from pyodm import Node

from app.config import settings


class OdmEngineError(RuntimeError):
    """Raised when the NodeODM engine is unreachable or rejects a request."""


def _node() -> Node:
    """Build a client for the configured NodeODM URL (e.g. http://localhost:3001)."""
    return Node.from_url(settings.odm_node_url)


def engine_online() -> bool:
    """True if the NodeODM engine answers. Never raises."""
    try:
        _node().info()
        return True
    except Exception:
        return False


def submit(image_paths: list[str], options: dict, name: str) -> str:
    """Upload an image set to NodeODM and start a reconstruction task.

    Blocking (uploads the images), so callers run it off the event loop.
    Returns the task UUID. Raises OdmEngineError on any engine failure.
    """
    try:
        task = _node().create_task(files=image_paths, options=options, name=name)
    except Exception as e:  # pyodm raises NodeConnectionError / NodeResponseError
        raise OdmEngineError(f"NodeODM task submission failed: {e}") from e
    return task.uuid


def status(task_uuid: str) -> dict:
    """Poll a task's status/progress. Raises OdmEngineError on engine failure.

    Returns a plain dict: ``status`` (QUEUED/RUNNING/COMPLETED/FAILED/CANCELED),
    ``progress`` (0-100 float), and ``last_error`` (str, may be empty).
    """
    try:
        info = _node().get_task(task_uuid).info()
    except Exception as e:
        raise OdmEngineError(f"NodeODM status poll failed for {task_uuid}: {e}") from e
    status_name = getattr(info.status, "name", str(info.status))
    return {
        "status": status_name,
        "progress": float(getattr(info, "progress", 0.0) or 0.0),
        "last_error": getattr(info, "last_error", "") or "",
    }


def download_assets(task_uuid: str, dest_dir: str) -> str:
    """Download every result asset for a completed task into ``dest_dir``.

    Returns the directory the assets were extracted into. Raises OdmEngineError.
    """
    try:
        task = _node().get_task(task_uuid)
        return task.download_assets(dest_dir)
    except Exception as e:
        raise OdmEngineError(f"NodeODM asset download failed for {task_uuid}: {e}") from e

"""Run-directory management: creation, manifest bookkeeping, hashing."""

from __future__ import annotations

import hashlib
import platform
import re
from datetime import UTC, datetime
from pathlib import Path

from graphdig import __version__
from graphdig.artifacts import ImageRef, Manifest, StageStatus, load_artifact, save_artifact

MANIFEST_NAME = "manifest.json"


def sha256_file(path: Path | str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while data := f.read(chunk):
            h.update(data)
    return h.hexdigest()


def natural_sort_key(s: str) -> list:
    """Sort '2' before '10' (ported from HistOrniGraph utils)."""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def slugify(name: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", name).strip("-")
    return slug[:max_len] or "run"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def create_run_dir(parent: Path, input_name: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = Path(parent) / f"{stamp}-{slugify(input_name)}"
    run_dir.mkdir(parents=True, exist_ok=False)
    for sub in ("pages", "panels", "tiles", "overlays", "series", "review"):
        (run_dir / sub).mkdir()
    return run_dir


def init_manifest(run_dir: Path, profile: str, config_dump: dict,
                  inputs: list[ImageRef]) -> Manifest:
    manifest = Manifest(
        run_id=run_dir.name,
        graphdig_version=__version__,
        profile=profile,
        config=config_dump,
        inputs=inputs,
        environment={
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
    )
    save_artifact(manifest, run_dir / MANIFEST_NAME)
    return manifest


def load_manifest(run_dir: Path) -> Manifest:
    return load_artifact(Manifest, Path(run_dir) / MANIFEST_NAME)


def save_manifest(run_dir: Path, manifest: Manifest) -> None:
    save_artifact(manifest, Path(run_dir) / MANIFEST_NAME)


def stage_started(run_dir: Path, manifest: Manifest, stage: str) -> None:
    manifest.stages[stage] = StageStatus(status="running", started=_now())
    save_manifest(run_dir, manifest)


def stage_done(run_dir: Path, manifest: Manifest, stage: str) -> None:
    st = manifest.stages.get(stage) or StageStatus()
    st.status, st.ended, st.error = "done", _now(), None
    manifest.stages[stage] = st
    save_manifest(run_dir, manifest)


def stage_error(run_dir: Path, manifest: Manifest, stage: str, error: str) -> None:
    st = manifest.stages.get(stage) or StageStatus()
    st.status, st.ended, st.error = "error", _now(), error
    manifest.stages[stage] = st
    save_manifest(run_dir, manifest)


def stage_is_done(manifest: Manifest, stage: str) -> bool:
    st = manifest.stages.get(stage)
    return st is not None and st.status == "done"

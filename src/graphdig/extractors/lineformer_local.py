"""Local LineFormer backend: runs scripts/lineformer_infer.py inside the pinned venv.

The pinned environment (.venvs/lineformer: Python 3.10, torch 1.13.1 CPU, mmdet 2.x) is
created by scripts/setup_lineformer_env.ps1|.sh. CPU-only on this machine by design:
Blackwell GPUs cannot run the cu117 binaries LineFormer needs; use the Colab path for GPU.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from graphdig.artifacts import LinesArtifact, Tile
from graphdig.extractors.base import ExtractParams, LineExtractor
from graphdig.extractors.colab_bundle import results_to_artifact, write_job_dir

REPO_ROOT = Path(__file__).resolve().parents[3]


def _venv_python() -> Path:
    override = os.environ.get("GRAPHDIG_LINEFORMER_PYTHON")
    if override:
        return Path(override)
    venv = REPO_ROOT / ".venvs" / "lineformer"
    return venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


class LineFormerLocal(LineExtractor):
    name = "lineformer_local"

    def extract(self, tiles: list[Tile], run_dir: Path,
                params: ExtractParams) -> LinesArtifact:
        python = _venv_python()
        if not python.exists():
            raise RuntimeError(
                f"LineFormer venv not found at {python}.\n"
                "Create it with scripts/setup_lineformer_env.ps1 (or .sh), or use "
                "--extractor colab_bundle / stub."
            )
        job_dir = Path(run_dir) / "extract_job"
        write_job_dir(run_dir, tiles, params, job_dir)
        results_path = job_dir / "results.json"
        cmd = [str(python), str(REPO_ROOT / "scripts" / "lineformer_infer.py"),
               "--job", str(job_dir), "--out", str(results_path),
               "--device", params.device]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        if proc.returncode != 0:
            raise RuntimeError(
                f"lineformer_infer.py failed (rc={proc.returncode}):\n"
                f"stdout:\n{proc.stdout[-2000:]}\nstderr:\n{proc.stderr[-2000:]}")
        results = json.loads(results_path.read_text(encoding="utf-8"))
        return results_to_artifact(results, backend=self.name)

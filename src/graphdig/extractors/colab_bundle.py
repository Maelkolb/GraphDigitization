"""Detached extraction via job bundles (the Colab GPU path).

`export_job` zips the run's tiles + a job.json; the Colab notebook (or any machine with
the pinned LineFormer env) runs scripts/lineformer_infer.py on the bundle and produces a
results zip; `import_results` validates and merges it back as lines.json. The local CPU
backend uses the exact same job format, just executed in-process via subprocess.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from graphdig.artifacts import (
    LineCandidate,
    LinesArtifact,
    Tile,
    TileLines,
    TilesArtifact,
    load_artifact,
    save_artifact,
)
from graphdig.extractors.base import ExtractParams, LineExtractor
from graphdig.runs import load_manifest, sha256_file, stage_done

JOB_VERSION = 1
REPO_ROOT = Path(__file__).resolve().parents[3]


def write_job_dir(run_dir: Path, tiles: list[Tile], params: ExtractParams,
                  job_dir: Path) -> Path:
    """Materialize the shared job format: job.json + tiles/ copies + the worker script
    (so the bundle is self-contained on Colab)."""
    run_dir, job_dir = Path(run_dir), Path(job_dir)
    (job_dir / "tiles").mkdir(parents=True, exist_ok=True)
    worker = REPO_ROOT / "scripts" / "lineformer_infer.py"
    if worker.exists():
        (job_dir / "lineformer_infer.py").write_bytes(worker.read_bytes())
    entries = []
    for tile in tiles:
        src = run_dir / tile.path
        dest = job_dir / "tiles" / f"{tile.tile_id}.png"
        dest.write_bytes(src.read_bytes())
        entries.append({"tile_id": tile.tile_id, "file": f"tiles/{tile.tile_id}.png",
                        "sha256": tile.sha256 or sha256_file(src)})
    job = {"job_version": JOB_VERSION, "run_id": run_dir.name,
           "params": {"max_per_image": params.max_per_image, "device": params.device},
           "tiles": entries}
    (job_dir / "job.json").write_text(json.dumps(job, indent=2), encoding="utf-8")
    return job_dir


def results_to_artifact(results: dict, backend: str) -> LinesArtifact:
    art = LinesArtifact(backend=backend,
                        backend_meta={k: str(v) for k, v in
                                      results.get("backend_meta", {}).items()},
                        params={k: float(v) for k, v in results.get("params", {}).items()
                                if isinstance(v, (int, float))})
    for tile_id, payload in results.get("tiles", {}).items():
        if payload.get("error"):
            art.tiles[tile_id] = TileLines(error=str(payload["error"]))
            continue
        cands = [LineCandidate(cand_id=int(c.get("cand_id", i)),
                               confidence=float(c.get("confidence", 0.0)),
                               n_points=len(c.get("points", [])),
                               points_px_tile=c.get("points", []))
                 for i, c in enumerate(payload.get("candidates", []))]
        art.tiles[tile_id] = TileLines(candidates=cands)
    return art


def export_job(run_dir: str | Path) -> Path:
    run_dir = Path(run_dir)
    tiles_art = load_artifact(TilesArtifact, run_dir / "tiles.json")
    manifest = load_manifest(run_dir)
    max_per_image = int(manifest.config.get("lineformer_max_per_image", 100))
    job_dir = run_dir / "colab" / "job"
    write_job_dir(run_dir, tiles_art.tiles, ExtractParams(max_per_image=max_per_image,
                                                          device="cuda:0"), job_dir)
    bundle = run_dir / "colab" / f"job_bundle_{run_dir.name}.zip"
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(job_dir.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(job_dir).as_posix())
    return bundle


def import_results(run_dir: str | Path, results_zip: str | Path) -> Path:
    run_dir = Path(run_dir)
    with zipfile.ZipFile(results_zip) as zf:
        results = json.loads(zf.read("results.json").decode("utf-8"))
    if results.get("run_id") != run_dir.name:
        raise ValueError(f"results are for run {results.get('run_id')!r}, "
                         f"not {run_dir.name!r}")
    art = results_to_artifact(results, backend="lineformer_colab")
    path = save_artifact(art, run_dir / "lines.json")
    manifest = load_manifest(run_dir)
    stage_done(run_dir, manifest, "extract")
    return path


class ColabBundle(LineExtractor):
    """In-pipeline behavior: export the bundle, then stop and wait for import-results."""

    name = "colab_bundle"

    def extract(self, tiles: list[Tile], run_dir: Path,
                params: ExtractParams) -> LinesArtifact:
        job_dir = Path(run_dir) / "colab" / "job"
        write_job_dir(run_dir, tiles, params, job_dir)
        bundle = Path(run_dir) / "colab" / f"job_bundle_{Path(run_dir).name}.zip"
        with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(job_dir.rglob("*")):
                if path.is_file():
                    zf.write(path, path.relative_to(job_dir).as_posix())
        raise SystemExit(
            f"job bundle exported: {bundle}\n"
            "Run it on Colab (notebooks/lineformer_colab.ipynb), then continue with:\n"
            f"  graphdig import-results {run_dir} <results zip>\n"
            f"  graphdig run --run-dir {run_dir} --stages select,series,qc,report"
        )

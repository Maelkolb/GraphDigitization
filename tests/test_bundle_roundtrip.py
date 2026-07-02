"""export-job -> (simulated remote worker) -> import-results round trip."""

from __future__ import annotations

import json
import zipfile

import pytest
from PIL import Image

from graphdig.artifacts import (
    ImageRef,
    LinesArtifact,
    Tile,
    TilesArtifact,
    load_artifact,
    save_artifact,
)
from graphdig.extractors.colab_bundle import export_job, import_results
from graphdig.runs import create_run_dir, init_manifest, sha256_file


@pytest.fixture
def run_with_tiles(tmp_path):
    run_dir = create_run_dir(tmp_path, "roundtrip")
    init_manifest(run_dir, "generic", {"lineformer_max_per_image": 7},
                  [ImageRef(path="pages/x.png", width=10, height=10)])
    tiles = []
    for pid in ("p01", "p02"):
        path = run_dir / "tiles" / f"{pid}.png"
        Image.new("RGB", (60, 40), (200, 200, 200)).save(path)
        tiles.append(Tile(tile_id=pid, path=f"tiles/{pid}.png", panel_id=pid,
                          width=60, height=40, sha256=sha256_file(path)))
    save_artifact(TilesArtifact(tiles=tiles), run_dir / "tiles.json")
    return run_dir


def _fake_remote_worker(bundle_path, out_zip):
    """Pretend to be the Colab notebook: read job.json, emit results.json."""
    with zipfile.ZipFile(bundle_path) as zf:
        job = json.loads(zf.read("job.json"))
        names = zf.namelist()
    assert "lineformer_infer.py" in names  # bundle must be self-contained
    results = {"run_id": job["run_id"], "params": job["params"],
               "backend_meta": {"device": "cuda:0", "torch": "1.13.1+cu117"},
               "tiles": {t["tile_id"]: {"candidates": [
                   {"cand_id": 0, "confidence": 0.9,
                    "points": [[0.0, 1.0], [5.0, 2.0], [10.0, 1.5]]}]}
                   for t in job["tiles"]}}
    with zipfile.ZipFile(out_zip, "w") as zf:
        zf.writestr("results.json", json.dumps(results))


def test_roundtrip(run_with_tiles, tmp_path):
    bundle = export_job(run_with_tiles)
    assert bundle.exists()
    with zipfile.ZipFile(bundle) as zf:
        job = json.loads(zf.read("job.json"))
    assert job["params"]["max_per_image"] == 7  # from the manifest config
    assert {t["tile_id"] for t in job["tiles"]} == {"p01", "p02"}

    results_zip = tmp_path / "results.zip"
    _fake_remote_worker(bundle, results_zip)
    import_results(run_with_tiles, results_zip)

    lines = load_artifact(LinesArtifact, run_with_tiles / "lines.json")
    assert lines.backend == "lineformer_colab"
    assert lines.tiles["p02"].candidates[0].n_points == 3
    # extract stage must now be marked done so the pipeline resumes at select
    from graphdig.runs import load_manifest, stage_is_done

    assert stage_is_done(load_manifest(run_with_tiles), "extract")


def test_import_rejects_wrong_run(run_with_tiles, tmp_path):
    bundle = export_job(run_with_tiles)
    results_zip = tmp_path / "results.zip"
    with zipfile.ZipFile(results_zip, "w") as zf:
        zf.writestr("results.json", json.dumps({"run_id": "someone-else", "tiles": {}}))
    with pytest.raises(ValueError, match="someone-else"):
        import_results(run_with_tiles, results_zip)
    assert bundle.exists()

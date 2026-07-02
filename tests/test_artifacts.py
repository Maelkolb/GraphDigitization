import json

from graphdig.artifacts import (
    ImageRef,
    LineCandidate,
    LinesArtifact,
    Panel,
    PanelsArtifact,
    TileLines,
    load_artifact,
    save_artifact,
)
from graphdig.geometry import BoxPx
from graphdig.runs import (
    create_run_dir,
    init_manifest,
    load_manifest,
    stage_done,
    stage_is_done,
    stage_started,
)


def _panels_artifact() -> PanelsArtifact:
    return PanelsArtifact(
        page_id="test_page",
        image=ImageRef(path="pages/test.png", width=1000, height=800),
        panels=[Panel(panel_id="p01", bbox_px=BoxPx(x=10, y=10, w=200, h=100),
                      confidence=0.9)],
    )


def test_artifact_roundtrip(tmp_path):
    art = _panels_artifact()
    path = save_artifact(art, tmp_path / "panels.json")
    loaded = load_artifact(PanelsArtifact, path)
    assert loaded == art


def test_unknown_fields_tolerated(tmp_path):
    art = _panels_artifact()
    raw = json.loads(art.model_dump_json())
    raw["added_in_future_version"] = {"x": 1}
    raw["panels"][0]["novel_field"] = True
    p = tmp_path / "panels.json"
    p.write_text(json.dumps(raw), encoding="utf-8")
    loaded = load_artifact(PanelsArtifact, p)
    assert loaded.panels[0].panel_id == "p01"


def test_lines_artifact_shape(tmp_path):
    art = LinesArtifact(
        backend="stub",
        tiles={"p01": TileLines(candidates=[
            LineCandidate(cand_id=0, confidence=0.9, n_points=3,
                          points_px_tile=[[0.0, 1.0], [1.0, 2.0], [2.0, 1.5]]),
        ])},
    )
    loaded = load_artifact(LinesArtifact, save_artifact(art, tmp_path / "lines.json"))
    assert loaded.tiles["p01"].candidates[0].n_points == 3


def test_manifest_stage_lifecycle(tmp_path):
    run_dir = create_run_dir(tmp_path, "My Chart (1848).png")
    assert (run_dir / "pages").is_dir()
    manifest = init_manifest(run_dir, "generic", {"x_stretch": 2.0},
                             [ImageRef(path="in.png", width=10, height=10)])
    stage_started(run_dir, manifest, "panels")
    assert load_manifest(run_dir).stages["panels"].status == "running"
    stage_done(run_dir, manifest, "panels")
    reloaded = load_manifest(run_dir)
    assert stage_is_done(reloaded, "panels")
    assert not stage_is_done(reloaded, "calibrate")

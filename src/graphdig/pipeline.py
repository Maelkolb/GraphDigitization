"""Stage orchestration: the Runner executes stages against a run directory.

Every stage is a function `stage(ctx: Context) -> None` that reads its input artifacts from
the run dir and writes its outputs back (see graphdig.artifacts). The manifest tracks stage
status, which makes runs resumable (`--run-dir ... --stages select,series`) and lets the
extract stage run remotely in between.
"""

from __future__ import annotations

import sys
import threading
import traceback
from pathlib import Path

from PIL import Image

from graphdig.artifacts import (
    ReviewArtifact,
    ReviewFlag,
    load_artifact,
    save_artifact,
)
from graphdig.config import DEFAULT_STAGES, RunConfig
from graphdig.runs import (
    load_manifest,
    stage_done,
    stage_error,
    stage_is_done,
    stage_started,
)

Image.MAX_IMAGE_PIXELS = 300_000_000  # archival scans are large; trust local inputs


class Context:
    """Everything a stage needs: config, run dir, manifest, lazy Gemini client."""

    def __init__(self, cfg: RunConfig, run_dir: Path, manifest, gemini_client=None):
        self.cfg = cfg
        self.run_dir = Path(run_dir)
        self.manifest = manifest
        self._gemini = gemini_client
        self._flag_lock = threading.Lock()

    @property
    def gemini(self):
        if self._gemini is None:
            from graphdig.gemini.client import GeminiClient

            self._gemini = GeminiClient(self.cfg.gemini)
        return self._gemini

    # ---- artifact paths -------------------------------------------------
    def path(self, name: str) -> Path:
        return self.run_dir / name

    def load(self, cls, name: str):
        return load_artifact(cls, self.run_dir / name)

    def save(self, model, name: str) -> Path:
        return save_artifact(model, self.run_dir / name)

    def page_image(self) -> Image.Image:
        from graphdig.artifacts import PanelsArtifact

        panels_path = self.run_dir / "panels.json"
        if panels_path.exists():
            art = load_artifact(PanelsArtifact, panels_path)
            return Image.open(self.run_dir / art.image.path)
        # before the panels stage: the ingested page
        pages = sorted((self.run_dir / "pages").glob("*.png"))
        if not pages:
            raise FileNotFoundError("no ingested page image; run the ingest stage first")
        return Image.open(pages[0])

    # ---- review flags ----------------------------------------------------
    def add_flag(self, stage: str, reason: str, panel_id: str = "",
                 severity: str = "warning", artifact_ref: str = "") -> None:
        path = self.run_dir / "review" / "flags.json"
        with self._flag_lock:
            review = load_artifact(ReviewArtifact, path) if path.exists() else ReviewArtifact()
            review.flags.append(ReviewFlag(stage=stage, panel_id=panel_id, reason=reason,
                                           severity=severity, artifact_ref=artifact_ref))
            save_artifact(review, path)
        print(f"  [flag/{severity}] {stage}{f' {panel_id}' if panel_id else ''}: {reason}")


def get_stage(name: str):
    import importlib

    module = importlib.import_module(f"graphdig.stages.{name}")
    return getattr(module, "run")


class Runner:
    def __init__(self, cfg: RunConfig, gemini_client=None):
        self.cfg = cfg
        self._gemini_client = gemini_client

    def run(self) -> int:
        inputs = self._resolve_inputs()
        rc = 0
        for run_dir, input_path in inputs:
            rc = max(rc, self._run_one(run_dir, input_path))
        return rc

    def _resolve_inputs(self) -> list[tuple[Path | None, Path | None]]:
        """(run_dir, input) pairs: resume an existing run, or one new run per input image."""
        if self.cfg.run_dir is not None:
            return [(self.cfg.run_dir, None)]
        if self.cfg.input is None:
            raise SystemExit("either an input image/directory or --run-dir is required")
        inp = self.cfg.input
        if inp.is_dir():
            images = sorted(p for p in inp.iterdir()
                            if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".tif", ".tiff"))
            if not images:
                raise SystemExit(f"no images found in {inp}")
            return [(None, p) for p in images]
        return [(None, inp)]

    def _run_one(self, run_dir: Path | None, input_path: Path | None) -> int:
        from graphdig.runs import create_run_dir, init_manifest

        if run_dir is None:
            run_dir = create_run_dir(self.cfg.out_parent, input_path.stem)
            manifest = init_manifest(run_dir, self.cfg.profile_name,
                                     self.cfg.model_dump(mode="json"), inputs=[])
            (run_dir / "input.txt").write_text(str(input_path.resolve()), encoding="utf-8")
        else:
            manifest = load_manifest(run_dir)
        print(f"run: {run_dir}")

        ctx = Context(self.cfg, run_dir, manifest, gemini_client=self._gemini_client)
        stages = self.cfg.stages or DEFAULT_STAGES
        for name in stages:
            if name == "baseline" and not self.cfg.use_baseline:
                continue
            if stage_is_done(manifest, name) and not self.cfg.force:
                print(f"  [skip] {name} (done)")
                continue
            print(f"  [run ] {name}")
            stage_started(run_dir, manifest, name)
            try:
                get_stage(name)(ctx)
            except Exception as exc:
                stage_error(run_dir, manifest, name, f"{exc}\n{traceback.format_exc()}")
                print(f"  [FAIL] {name}: {exc}", file=sys.stderr)
                return 1
            stage_done(run_dir, manifest, name)
        return 0

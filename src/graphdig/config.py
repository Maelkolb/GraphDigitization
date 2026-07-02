"""Run configuration (pydantic models; serialized verbatim into the run manifest)."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from graphdig.profiles import PROFILES, Profile

DEFAULT_STAGES = [
    "ingest", "triage", "calibrate", "baseline",
    "preprocess", "extract", "select", "series", "qc", "report",
]


class GeminiConfig(BaseModel):
    model_id: str = "gemini-3.5-flash"
    retries: int = 2  # schema-validation retry loop (HistOrniGraph region_detector pattern)
    max_output_tokens: int = 16384
    # Gemini 3.x guidance: never set temperature/top_p/top_k; steer with thinking_level.
    thinking_panels: str = "high"
    thinking_calibrate: str = "high"
    thinking_metadata: str = "low"
    thinking_baseline: str = "medium"
    thinking_qc: str = "medium"
    thinking_pick: str = "low"


class Gates(BaseModel):
    """Confidence gates; failures land in review/flags.json, not silent errors."""

    panel_conf_min: float = 0.5
    cal_min_ticks: int = 3  # below this, two-anchor fallback + flag
    cal_r2_min: float = 0.995
    cal_max_rel_residual: float = 0.02
    coverage_viable: float = 0.985  # paper Sect. 4.5.4
    alpha_coverage: float = 0.69  # paper Eq. 12
    pick_margin: float = 0.05  # invoke Gemini pick when top-2 s_alpha closer than this
    qc_block_on: tuple[str, ...] = ("major",)
    qc_auto_reselect: bool = True  # major verdict -> reject candidate, reselect, re-judge
    qc_max_reselect: int = 1  # bounded retries per panel


class RunConfig(BaseModel):
    input: Path | None = None
    run_dir: Path | None = None
    out_parent: Path = Path("outputs/runs")
    profile_name: Literal["danube", "generic"] = "generic"
    stages: list[str] | None = None  # None = all
    force: bool = False
    extractor: Literal["lineformer_local", "colab_bundle", "stub"] = "lineformer_local"
    x_stretch: float = 2.0  # paper Sect. 4.5.2, fixed s=2.0
    lineformer_max_per_image: int = 100
    baseline_enabled: bool | None = None  # None = profile default
    hints_path: Path | None = None  # user metadata hints (see graphdig.hints)
    workers: int = 4
    gemini: GeminiConfig = Field(default_factory=GeminiConfig)
    gates: Gates = Field(default_factory=Gates)

    @property
    def profile(self) -> Profile:
        return PROFILES[self.profile_name]

    @property
    def use_baseline(self) -> bool:
        if self.baseline_enabled is not None:
            return self.baseline_enabled
        return self.profile.baseline_enabled

    @classmethod
    def from_cli(cls, args: argparse.Namespace) -> RunConfig:
        stages = args.stages.split(",") if args.stages else None
        return cls(
            input=Path(args.input) if args.input else None,
            run_dir=Path(args.run_dir) if args.run_dir else None,
            out_parent=Path(args.out),
            profile_name=args.profile,
            stages=stages,
            force=args.force,
            extractor=args.extractor or "lineformer_local",
            hints_path=Path(args.hints) if getattr(args, "hints", None) else None,
            workers=args.workers,
        )

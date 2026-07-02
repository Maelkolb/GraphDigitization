"""Head-to-head extraction backend benchmark (lineformer_local vs gemini_points).

Danube gauge-months run seeded (annotation calibration) so ONLY the extraction backend
differs; scores come from the pixel ground truth. Charts without GT (the known-weak
material) get qualitative rows: QC verdict + coverage + overlays for eyeballing.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BenchRow:
    source: str  # "danube:210018:1839-02" | image stem
    backend: str
    peak_score: float = math.nan
    rmse: float = math.nan
    mae: float = math.nan
    pearson_r: float = math.nan
    coverage: float = math.nan
    qc_verdicts: str = ""
    wall_s: float = 0.0
    tokens: int = 0
    error: str = ""
    run_dir: str = ""
    extra: dict = field(default_factory=dict)


def parse_gauge_months(spec: str) -> list[tuple[str, int, int]]:
    """'210018:1839:1-3,290022:1844:6' -> [(scan, year, month), ...]"""
    out: list[tuple[str, int, int]] = []
    for part in spec.split(","):
        scan, year, months = part.strip().split(":")
        for chunk in months.split("+"):
            if "-" in chunk:
                a, b = chunk.split("-")
                out.extend((scan, int(year), m) for m in range(int(a), int(b) + 1))
            else:
                out.append((scan, int(year), int(chunk)))
    return out


def _collect_run_diag(run_dir: Path) -> tuple[float, str, int]:
    """(selected coverage, qc verdicts, gemini tokens) from a finished run."""
    from graphdig.artifacts import LinesArtifact, QcArtifact, load_artifact

    coverage, verdicts, tokens = math.nan, [], 0
    lines_path = run_dir / "lines.json"
    if lines_path.exists():
        lines = load_artifact(LinesArtifact, lines_path)
        covs = []
        for tl in lines.tiles.values():
            for sel in (tl.selections or ([tl.selected] if tl.selected else [])):
                cand = next((c for c in tl.candidates if c.cand_id == sel.cand_id), None)
                if cand and cand.coverage is not None:
                    covs.append(cand.coverage)
        if covs:
            coverage = sum(covs) / len(covs)
        for k, v in lines.backend_meta.items():
            if k.startswith("tokens:"):
                tokens += int(v or 0)
    qc_path = run_dir / "qc.json"
    if qc_path.exists():
        qc = load_artifact(QcArtifact, qc_path)
        verdicts = [f"{k}:{q.verdict}" for k, q in sorted(qc.panels.items())]
    return coverage, " ".join(verdicts), tokens


def bench_danube(gauge_months: list[tuple[str, int, int]], backends: list[str],
                 out_parent: Path) -> list[BenchRow]:
    from graphdig.config import RunConfig
    from graphdig.data.danube_prep import prepare_run
    from graphdig.eval.series_eval import evaluate_month
    from graphdig.pipeline import Runner

    rows: list[BenchRow] = []
    for backend in backends:
        for scan, year, month in gauge_months:
            source = f"danube:{scan}:{year}-{month:02d}"
            cfg = RunConfig(out_parent=Path(out_parent) / f"runs_{backend}",
                            profile_name="danube", extractor=backend,
                            baseline_enabled=False, workers=2)
            t0 = time.time()
            row = BenchRow(source=source, backend=backend)
            try:
                run_dir = prepare_run(scan, month, year, cfg)
                run_cfg = cfg.model_copy(update={
                    "run_dir": run_dir,
                    "stages": ["preprocess", "extract", "select", "series", "qc"]})
                rc = Runner(run_cfg).run()
                row.run_dir = str(run_dir)
                if rc != 0:
                    row.error = "run failed"
                else:
                    ev = evaluate_month(run_dir, scan, month)
                    if ev:
                        row.peak_score, row.rmse = ev.peak_score, ev.rmse
                        row.mae, row.pearson_r = ev.mae, ev.pearson_r
                row.coverage, row.qc_verdicts, row.tokens = _collect_run_diag(Path(run_dir))
            except Exception as exc:
                row.error = f"{type(exc).__name__}: {exc}"
            row.wall_s = time.time() - t0
            rows.append(row)
            print(f"  [{backend}] {source}: peak={row.peak_score:.3f} "
                  f"qc={row.qc_verdicts or '-'} ({row.wall_s:.0f}s) {row.error}")
    return rows


def bench_images(images: list[Path], backends: list[str],
                 out_parent: Path) -> list[BenchRow]:
    from graphdig.config import RunConfig
    from graphdig.pipeline import Runner
    from graphdig.runs import natural_sort_key  # noqa: F401  (stable import point)

    rows: list[BenchRow] = []
    for backend in backends:
        for image in images:
            t0 = time.time()
            row = BenchRow(source=Path(image).stem, backend=backend)
            try:
                out = Path(out_parent) / f"runs_{backend}"
                cfg = RunConfig(input=Path(image), out_parent=out,
                                profile_name="generic", extractor=backend, workers=2)
                before = {p.name for p in out.glob("*")} if out.exists() else set()
                rc = Runner(cfg).run()
                new = [p for p in out.glob("*") if p.name not in before]
                if new:
                    row.run_dir = str(new[0])
                    row.coverage, row.qc_verdicts, row.tokens = _collect_run_diag(new[0])
                if rc != 0:
                    row.error = "run failed"
            except Exception as exc:
                row.error = f"{type(exc).__name__}: {exc}"
            row.wall_s = time.time() - t0
            rows.append(row)
            print(f"  [{backend}] {row.source}: qc={row.qc_verdicts or '-'} "
                  f"({row.wall_s:.0f}s) {row.error}")
    return rows


def comparison_table(rows: list[BenchRow], metric: str = "peak_score") -> str:
    """Markdown: one row per source, one column per backend."""
    backends = sorted({r.backend for r in rows})
    by_source: dict[str, dict[str, BenchRow]] = {}
    for r in rows:
        by_source.setdefault(r.source, {})[r.backend] = r
    lines = ["| source | " + " | ".join(backends) + " |",
             "|---" * (len(backends) + 1) + "|"]
    for source in sorted(by_source):
        cells = []
        for b in backends:
            r = by_source[source].get(b)
            if r is None:
                cells.append("-")
            elif r.error:
                cells.append("ERR")
            elif not math.isnan(getattr(r, metric)):
                cells.append(f"{getattr(r, metric):.3f}")
            else:
                cells.append(r.qc_verdicts or "-")
        lines.append(f"| {source} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def bench_cli(args) -> int:
    import pandas as pd

    out = Path(args.out or "outputs/eval/extractor-bench")
    out.mkdir(parents=True, exist_ok=True)
    backends = [b.strip() for b in args.backends.split(",")]
    rows: list[BenchRow] = []
    if args.gauge_months:
        rows += bench_danube(parse_gauge_months(args.gauge_months), backends, out)
    if args.images:
        rows += bench_images([Path(p.strip()) for p in args.images.split(",")],
                             backends, out)
    if not rows:
        print("nothing to benchmark: pass --gauge-months and/or --images")
        return 2
    pd.DataFrame([{k: v for k, v in r.__dict__.items() if k != "extra"}
                  for r in rows]).to_csv(out / "extractor_bench.csv", index=False)
    table = comparison_table(rows)
    (out / "comparison.md").write_text(table + "\n", encoding="utf-8")
    print(table)
    print(f"\nbench artifacts: {out}")
    return 0

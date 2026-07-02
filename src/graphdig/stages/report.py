"""Report stage: human-readable run summary (report.md) plus per-panel series plots."""

from __future__ import annotations

import csv
import math
from pathlib import Path

from graphdig.artifacts import (
    CalibrationArtifact,
    LinesArtifact,
    PanelsArtifact,
    QcArtifact,
    ReviewArtifact,
    SeriesArtifact,
    load_artifact,
)
from graphdig.pipeline import Context


def _load_optional(ctx: Context, cls, name: str):
    path = ctx.run_dir / name
    return load_artifact(cls, path) if path.exists() else None


def _series_plot(ctx: Context, pid: str, csv_rel: str) -> str | None:
    """Reconstruction figure: scan on top, digitized series below, shared x-axis."""
    from PIL import Image

    from graphdig.render import reconstruction_figure

    xs, values, unit = [], [], ""
    with open(ctx.run_dir / csv_rel, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            v = row["value_native"]
            values.append(float(v) if v else math.nan)
            xs.append(row["x_key"])
            unit = unit or row["native_unit"]
    if not values:
        return None
    tile_path = ctx.run_dir / "tiles" / f"{pid}.png"
    if not tile_path.exists():
        return None
    rel = f"overlays/reconstruction_{pid}.png"
    reconstruction_figure(Image.open(tile_path), values, xs, unit or "?",
                          ctx.run_dir / rel,
                          title=f"{ctx.manifest.run_id} — {pid}")
    return rel


def run(ctx: Context) -> None:
    panels = _load_optional(ctx, PanelsArtifact, "panels.json")
    cal = _load_optional(ctx, CalibrationArtifact, "calibration.json")
    lines = _load_optional(ctx, LinesArtifact, "lines.json")
    series = _load_optional(ctx, SeriesArtifact, "series.json")
    qc = _load_optional(ctx, QcArtifact, "qc.json")
    review_path = ctx.run_dir / "review" / "flags.json"
    review = load_artifact(ReviewArtifact, review_path) if review_path.exists() else None

    lines_out: list[str] = [f"# Run report: {ctx.manifest.run_id}", ""]
    lines_out += [f"- profile: **{ctx.manifest.profile}**",
                  f"- graphdig: {ctx.manifest.graphdig_version}"]
    if ctx.manifest.inputs:
        img = ctx.manifest.inputs[0]
        lines_out.append(f"- input: `{img.path}` ({img.width}x{img.height})")
    lines_out.append("")

    if panels:
        lines_out += ["## Panels", "",
                      "| panel | label | bbox (x,y,w,h) | conf | flags |",
                      "|---|---|---|---|---|"]
        for p in panels.panels:
            b = p.bbox_px
            lines_out.append(f"| {p.panel_id} | {p.label} | {b.x},{b.y},{b.w},{b.h} "
                             f"| {p.confidence:.2f} | {', '.join(p.flags)} |")
        lines_out += ["", "![panels](overlays/panels.png)", ""]

    if cal:
        lines_out += ["## Calibration", "",
                      "| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |",
                      "|---|---|---|---|---|---|---|"]
        for pid, pc in sorted(cal.panels.items()):
            f = pc.y_axis.fit
            fit_txt = (f"{f.slope:.5g} | {f.r2:.4f} | {f.n_used}/{f.n_ticks}"
                       if f else "- | - | -")
            lines_out.append(f"| {pid} | {pc.y_axis.unit.canonical} | {pc.y_axis.scale} "
                             f"| {fit_txt} | {', '.join(pc.y_axis.flags)} |")
        lines_out.append("")

    if lines:
        lines_out += [f"## Extraction ({lines.backend})", "",
                      "| panel | candidates | selected | conf | coverage | s_alpha | method |",
                      "|---|---|---|---|---|---|---|"]
        for tid, tl in sorted(lines.tiles.items()):
            if tl.error:
                lines_out.append(f"| {tid} | ERROR: {tl.error} | | | | | |")
                continue
            sel = tl.selected
            chosen = next((c for c in tl.candidates
                           if sel and c.cand_id == sel.cand_id), None)
            if chosen:
                lines_out.append(
                    f"| {tid} | {len(tl.candidates)} | {chosen.cand_id} "
                    f"| {chosen.confidence:.3f} | {(chosen.coverage or 0):.3f} "
                    f"| {(chosen.s_alpha or 0):.3f} | {sel.method} |")
            else:
                lines_out.append(f"| {tid} | {len(tl.candidates)} | none | | | | |")
        lines_out.append("")

    if series:
        lines_out += ["## Series", ""]
        for pid, ps in sorted(series.panels.items()):
            plot_rel = _series_plot(ctx, pid, ps.csv_path)
            lines_out.append(f"### {pid}")
            lines_out.append(f"- csv: `{ps.csv_path}` ({ps.n} samples, "
                             f"{len(ps.gaps)} gaps, baseline "
                             f"{'applied' if ps.baseline_applied else 'off'})")
            chain = ", ".join(f"{k}={v:.2f}" for k, v in ps.confidence_chain.items())
            lines_out.append(f"- confidence chain: {chain}")
            if qc and pid in qc.panels:
                q = qc.panels[pid]
                lines_out.append(f"- QC: **{q.verdict}** {q.reason}")
            lines_out.append(f"\n![curve](overlays/curve_{pid}.png)")
            if plot_rel:
                lines_out.append(f"![series]({plot_rel})")
            lines_out.append("")

    if review and review.flags:
        lines_out += ["## Review flags", "",
                      "| severity | stage | panel | reason |", "|---|---|---|---|"]
        for fl in review.flags:
            lines_out.append(f"| {fl.severity} | {fl.stage} | {fl.panel_id} | {fl.reason} |")
        lines_out.append("")

    Path(ctx.run_dir / "report.md").write_text("\n".join(lines_out), encoding="utf-8")

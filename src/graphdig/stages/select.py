"""Select stage: turn LineFormer's candidate pile into one polyline PER DATA SERIES.

Single-series charts keep the paper's recipe (Sect. 4.5.4): coverage, s_alpha =
0.31*confidence + 0.69*coverage (Eq. 12), near-tie Gemini visual pick.

Multi-series charts (triage reports n_series > 1) generalize it:
1. score all candidates as usual;
2. greedily accept the best-scoring candidates that are MUTUALLY DISTINCT (median
   vertical separation above a threshold - candidates tracing the same stroke or a
   gridline collapse onto an already-accepted one);
3. Gemini assigns each accepted candidate to a named series from the legend (and calls
   out artifacts, which are replaced by the next distinct candidate).

Every selection carries its series id/label; downstream stages digitize each one.
"""

from __future__ import annotations

import numpy as np
from PIL import Image

from graphdig.artifacts import (
    CalibrationArtifact,
    LineCandidate,
    LinesArtifact,
    PanelsArtifact,
    Selection,
    Tile,
    TilesArtifact,
)
from graphdig.gemini.prompts import PROMPTS
from graphdig.gemini.schemas import AssignResponse, PickResponse
from graphdig.pipeline import Context
from graphdig.render import draw_candidates
from graphdig.series.resample import coverage, s_alpha

FALLBACK_SLICES = 100
SEPARATION_FRACTION = 0.015  # of tile height; below this two candidates are "the same line"
MAX_ASSIGN_CANDIDATES = 6


def _n_slices(cal, tile_id: str) -> int:
    panel_cal = cal.panels.get(tile_id)
    if panel_cal and panel_cal.x_axis.n_samples:
        return panel_cal.x_axis.n_samples
    return FALLBACK_SLICES


def _viable_gate(ctx: Context) -> float:
    if ctx.cfg.profile.coverage_viable is not None:
        return ctx.cfg.profile.coverage_viable
    return ctx.cfg.gates.coverage_viable


def separation(a: np.ndarray, b: np.ndarray) -> float:
    """Median |Δy| between two polylines on their overlapping x-range (crossings-robust)."""
    a = np.asarray(a, dtype=float).reshape(-1, 2)
    b = np.asarray(b, dtype=float).reshape(-1, 2)
    lo = max(a[:, 0].min(), b[:, 0].min())
    hi = min(a[:, 0].max(), b[:, 0].max())
    if hi <= lo:
        return float("inf")  # disjoint x-ranges: trivially distinct
    xs = np.linspace(lo, hi, 64)
    ao = np.argsort(a[:, 0])
    bo = np.argsort(b[:, 0])
    ya = np.interp(xs, a[ao, 0], a[ao, 1])
    yb = np.interp(xs, b[bo, 0], b[bo, 1])
    return float(np.median(np.abs(ya - yb)))


def distinct_candidates(ranked: list[LineCandidate], n: int, tile_height: int,
                        exclude: set[int] = frozenset()) -> list[LineCandidate]:
    """Greedy top-s_alpha selection of up to n mutually distinct candidates."""
    threshold = max(3.0, SEPARATION_FRACTION * tile_height)
    accepted: list[LineCandidate] = []
    for c in ranked:
        if len(accepted) >= n:
            break
        if c.cand_id in exclude:
            continue
        pts = np.asarray(c.points_px_tile, dtype=float)
        if all(separation(pts, np.asarray(a.points_px_tile, dtype=float)) > threshold
               for a in accepted):
            accepted.append(c)
    return accepted


def gemini_pick(ctx: Context, tile: Tile, viable) -> int | None:
    tile_img = Image.open(ctx.run_dir / tile.path)
    overlay_path = ctx.run_dir / "overlays" / f"pick_{tile.tile_id}.png"
    draw_candidates(tile_img,
                    [(c.cand_id, np.array(c.points_px_tile)) for c in viable[:6]],
                    overlay_path)
    result = ctx.gemini.generate_json(
        images=[overlay_path], prompt=PROMPTS["PICK_V1"], schema=PickResponse,
        prompt_id="PICK_V1", thinking_level=ctx.cfg.gemini.thinking_pick,
        media_resolution="high",
    )
    if result.ok and any(c.cand_id == result.data.best_cand_id for c in viable):
        return result.data.best_cand_id
    return None


def gemini_assign(ctx: Context, tile: Tile, accepted: list[LineCandidate],
                  labels: list[str]) -> dict[int, str] | None:
    """Map accepted candidates to series labels; 'artifact' marks non-data lines."""
    tile_img = Image.open(ctx.run_dir / tile.path)
    overlay_path = ctx.run_dir / "overlays" / f"assign_{tile.tile_id}.png"
    draw_candidates(tile_img,
                    [(c.cand_id, np.array(c.points_px_tile))
                     for c in accepted[:MAX_ASSIGN_CANDIDATES]], overlay_path)
    prompt = PROMPTS["ASSIGN_V1"].format(series_list=", ".join(labels))
    result = ctx.gemini.generate_json(
        images=[overlay_path], prompt=prompt, schema=AssignResponse,
        prompt_id="ASSIGN_V1", thinking_level=ctx.cfg.gemini.thinking_pick,
        media_resolution="high",
    )
    if not result.ok:
        return None
    return {a.cand_id: a.series_label for a in result.data.assignments}


def _select_single(ctx: Context, tile: Tile, ranked, viable, gates) -> Selection:
    best = ranked[0]
    selection = Selection(cand_id=best.cand_id, method="s_alpha",
                          alpha_coverage=gates.alpha_coverage)
    near_tie = (len(viable) >= 2
                and (viable[0].s_alpha or 0) - (viable[1].s_alpha or 0) < gates.pick_margin)
    if near_tie:
        try:
            pick = gemini_pick(ctx, tile, viable)
        except Exception as exc:  # no API key / network: score selection stands
            ctx.add_flag("select", f"Gemini pick unavailable ({exc}); using s_alpha",
                         panel_id=tile.tile_id, severity="info")
            pick = None
        if pick is not None:
            selection.gemini_pick = pick
            selection.agreement = pick == best.cand_id
            if pick != best.cand_id:
                selection = Selection(cand_id=pick, method="gemini_pick",
                                      alpha_coverage=gates.alpha_coverage,
                                      gemini_pick=pick, agreement=False)
    return selection


def _select_multi(ctx: Context, tile: Tile, ranked, n_series: int,
                  labels: list[str], gates) -> list[Selection]:
    accepted = distinct_candidates(ranked, n_series, tile.height)
    label_by_cand: dict[int, str] = {}
    method = "s_alpha_distinct"
    if len(accepted) >= 1 and labels:
        try:
            assignment = gemini_assign(ctx, tile, accepted, labels)
        except Exception as exc:
            ctx.add_flag("select", f"Gemini assignment unavailable ({exc})",
                         panel_id=tile.tile_id, severity="info")
            assignment = None
        if assignment is not None:
            method = "gemini_assign"
            # drop artifacts, refill once with the next distinct candidates
            keep = [c for c in accepted
                    if assignment.get(c.cand_id, "").lower() != "artifact"]
            if len(keep) < len(accepted):
                exclude = {c.cand_id for c in accepted}
                refill = distinct_candidates(
                    [c for c in ranked if c.cand_id not in exclude],
                    n_series - len(keep), tile.height)
                keep += refill
            accepted = keep or accepted
            label_by_cand = assignment

    if len(accepted) < n_series:
        ctx.add_flag("select", f"found {len(accepted)} distinct curve(s) for "
                     f"{n_series} expected series", panel_id=tile.tile_id)

    used_labels: set[str] = set()
    selections = []
    for i, c in enumerate(accepted):
        label = label_by_cand.get(c.cand_id, "")
        if not label or label.lower() == "artifact" or label in used_labels:
            remaining = [lb for lb in labels if lb not in used_labels]
            label = remaining[0] if remaining else f"series {i + 1}"
        used_labels.add(label)
        selections.append(Selection(cand_id=c.cand_id, method=method,
                                    alpha_coverage=gates.alpha_coverage,
                                    series_id=f"s{i + 1}", series_label=label))
    return selections


def run(ctx: Context) -> None:
    lines = ctx.load(LinesArtifact, "lines.json")
    tiles_art = ctx.load(TilesArtifact, "tiles.json")
    cal = ctx.load(CalibrationArtifact, "calibration.json")
    panels_art = ctx.load(PanelsArtifact, "panels.json")
    cls = panels_art.classification
    gates = ctx.cfg.gates
    viable_gate = _viable_gate(ctx)
    tiles_by_id = {t.tile_id: t for t in tiles_art.tiles}
    n_series = max(1, cls.n_series)
    labels = cls.series_labels or [f"series {i + 1}" for i in range(n_series)]

    for tile_id, tl in lines.tiles.items():
        if tl.error or not tl.candidates:
            continue
        tile = tiles_by_id[tile_id]
        n = _n_slices(cal, tile_id)
        for c in tl.candidates:
            pts = np.asarray(c.points_px_tile, dtype=float).reshape(-1, 2)
            c.coverage = coverage(pts, 0.0, float(tile.width), n)
            c.s_alpha = s_alpha(c.confidence, c.coverage, gates.alpha_coverage)
            c.viable = c.coverage >= viable_gate

        ranked = sorted(tl.candidates, key=lambda c: -(c.s_alpha or 0.0))
        viable = [c for c in ranked if c.viable]
        pool = viable or ranked

        if n_series == 1:
            selection = _select_single(ctx, tile, ranked, viable, gates)
            selection.series_label = labels[0] if cls.series_labels else ""
            tl.selections = [selection]
        else:
            tl.selections = _select_multi(ctx, tile, pool, n_series, labels, gates)
        tl.selected = tl.selections[0] if tl.selections else None

        best = ranked[0]
        if not best.viable and n_series == 1 and tl.selected.method == "s_alpha":
            ctx.add_flag("select",
                         f"best candidate coverage {best.coverage:.3f} below viability "
                         f"gate {viable_gate}", panel_id=tile_id, severity="warning")
    ctx.save(lines, "lines.json")

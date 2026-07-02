"""QC stage: Gemini judges every extracted series - and can veto and reselect.

Replaces the paper's human visual inspection (inspector.py, Sect. 4.5.4): verdicts
ok / minor / major with issue tags, one judgement per digitized series (multi-series
charts get one per curve, each told which series it represents). `qc_auto_reselect`
closes the loop the paper left manual: a "major / wrong line" verdict rejects the
offending candidate, selection reruns over the remaining viable candidates (excluding
those already assigned to sibling series), the series is rebuilt, and the new curve is
judged again (bounded by qc_max_reselect). Unrecoverable majors stay as blocking flags.
"""

from __future__ import annotations

from graphdig.artifacts import PanelQc, Provenance, QcArtifact, SeriesArtifact
from graphdig.gemini.client import GeminiUnavailable
from graphdig.gemini.prompts import PROMPTS, QC_SERIES_SUFFIX
from graphdig.gemini.schemas import QcResponse
from graphdig.pipeline import Context
from graphdig.stages.select import distinct_candidates, gemini_pick
from graphdig.stages.series import build_panel_series, load_context_artifacts

_ACTION = {"ok": "accept", "minor": "review", "major": "reextract"}


def _judge(ctx: Context, key: str, series_label: str) -> tuple[PanelQc | None, Provenance | None]:
    overlay_rel = f"overlays/curve_{key}.png"
    overlay_path = ctx.run_dir / overlay_rel
    tile_key = key.split("_s")[0] if "_s" in key else key
    tile_path = ctx.run_dir / "tiles" / f"{tile_key}.png"
    if not overlay_path.exists() or not tile_path.exists():
        return None, None
    prompt = PROMPTS["QC_V1"]
    if series_label:
        prompt += QC_SERIES_SUFFIX.format(series_label=series_label)
    result = ctx.gemini.generate_json(
        images=[tile_path, overlay_path], prompt=prompt, schema=QcResponse,
        prompt_id="QC_V1", thinking_level=ctx.cfg.gemini.thinking_qc,
        media_resolution="high",
    )
    if not result.ok:
        ctx.add_flag("qc", f"Gemini call failed: {result.error}", panel_id=key)
        return None, None
    r = result.data
    qc = PanelQc(verdict=r.verdict, issues=r.issues, reason=r.reason,
                 suggested_action=_ACTION.get(r.verdict, "review"),
                 confidence=r.confidence, overlay=overlay_rel)
    prov = Provenance(model=result.model, prompt_id=result.prompt_id,
                      thinking_level=result.thinking_level,
                      attempts=result.attempts, usage=result.usage)
    return qc, prov


def _fallback_extract(ctx: Context, tile, panel, cal_art, lines) -> bool:
    """Merge candidates from the fallback backend into this tile's pool (once)."""
    import numpy as np

    from graphdig.extractors import ExtractParams, get_extractor
    from graphdig.series.resample import coverage, s_alpha
    from graphdig.stages.select import _n_slices, _plot_extent_in_tile, _viable_gate

    tl = lines.tiles[tile.tile_id]
    if tl.fallback_used or not ctx.cfg.extractor_fallback:
        return False
    tl.fallback_used = True
    try:
        backend = get_extractor(ctx.cfg.extractor_fallback, ctx)
        sub = backend.extract([tile], ctx.run_dir,
                              ExtractParams(max_per_image=ctx.cfg.lineformer_max_per_image))
    except Exception as exc:
        ctx.add_flag("qc", f"fallback extractor failed: {exc}", panel_id=tile.tile_id)
        return False
    sub_tl = sub.tiles.get(tile.tile_id)
    if sub_tl is None or sub_tl.error or not sub_tl.candidates:
        ctx.add_flag("qc", "fallback extractor returned no candidates",
                     panel_id=tile.tile_id, severity="info")
        return False

    offset = max((c.cand_id for c in tl.candidates), default=-1) + 1
    n = _n_slices(cal_art, tile.tile_id)
    x_lo, x_hi = _plot_extent_in_tile(tile, panel)
    gate = _viable_gate(ctx)
    for c in sub_tl.candidates:
        c.cand_id += offset
        pts = np.asarray(c.points_px_tile, dtype=float).reshape(-1, 2)
        c.coverage = coverage(pts, x_lo, x_hi, n)
        c.s_alpha = s_alpha(c.confidence, c.coverage, ctx.cfg.gates.alpha_coverage)
        c.viable = c.coverage >= gate
        tl.candidates.append(c)
    lines.backend_meta[f"fallback:{tile.tile_id}"] = ctx.cfg.extractor_fallback
    ctx.add_flag("qc", f"merged {len(sub_tl.candidates)} candidate(s) from fallback "
                 f"backend {ctx.cfg.extractor_fallback}", panel_id=tile.tile_id,
                 severity="info")
    return True


def _reselect(ctx: Context, lines, tile, series_id: str) -> int | None:
    """Reject this series' candidate and pick an alternative; None if none remains.

    Alternatives must be distinct from candidates assigned to sibling series and from
    everything already rejected on this tile.
    """
    tl = lines.tiles[tile.tile_id]
    current = next((s for s in tl.selections if s.series_id == series_id), tl.selected)
    if current is None:
        return None
    tl.rejected.append(current.cand_id)
    sibling_ids = {s.cand_id for s in tl.selections if s.series_id != series_id}
    exclude = set(tl.rejected) | sibling_ids
    ranked = sorted((c for c in tl.candidates if c.cand_id not in exclude),
                    key=lambda c: -(c.s_alpha or 0.0))
    ranked = [c for c in ranked if c.viable] or ranked
    if not ranked:
        return None
    siblings = [next(c for c in tl.candidates if c.cand_id == sid)
                for sid in sibling_ids]
    # keep the replacement visually distinct from sibling series' curves
    pool = distinct_candidates(siblings + ranked, len(siblings) + 1, tile.height,
                               exclude=set())
    pool = [c for c in pool if c.cand_id not in sibling_ids]
    candidates = pool or ranked
    chosen, method = candidates[0].cand_id, "qc_reselect_s_alpha"
    if len(candidates) >= 2:
        try:
            pick = gemini_pick(ctx, tile, candidates[:6])
        except Exception:
            pick = None
        if pick is not None:
            chosen, method = pick, "qc_reselect_gemini_pick"
    current.cand_id, current.method = chosen, method
    if tl.selected and tl.selected.series_id == series_id:
        tl.selected = current
    return chosen


def run(ctx: Context) -> None:
    series_art = ctx.load(SeriesArtifact, "series.json")
    panels_art, cal_art, lines, tiles_art, baseline_art = load_context_artifacts(ctx)
    panels_by_id = {p.panel_id: p for p in panels_art.panels}
    tiles_by_id = {t.tile_id: t for t in tiles_art.tiles}
    gates = ctx.cfg.gates

    art = QcArtifact()
    for key in list(series_art.panels):
        ps = series_art.panels[key]
        pid = ps.panel_id or key
        if pid not in tiles_by_id:  # stitched entries ("annual") have no tile to judge
            continue
        budget = gates.qc_max_reselect + (1 if ctx.cfg.extractor_fallback else 0)
        for attempt in range(budget + 1):
            try:
                qc, prov = _judge(ctx, key, ps.series_label)
            except GeminiUnavailable as exc:
                ctx.add_flag("qc", f"skipped: {exc}", severity="info")
                ctx.save(art, "qc.json")
                return
            if qc is None:
                break
            art.panels[key] = qc
            if prov:
                art.provenance = prov
            if qc.verdict not in gates.qc_block_on or not gates.qc_auto_reselect:
                break
            if attempt >= budget:
                break
            tile = tiles_by_id[pid]
            new_cand = _reselect(ctx, lines, tile, ps.series_id)
            if new_cand is None and _fallback_extract(ctx, tile,
                                                      panels_by_id[pid], cal_art, lines):
                new_cand = _reselect(ctx, lines, tile, ps.series_id)
            if new_cand is None:
                ctx.add_flag("qc", "major verdict but no alternative candidate left",
                             panel_id=key, severity="blocking")
                break
            ctx.add_flag("qc", f"QC rejected candidate; reselected cand {new_cand}",
                         panel_id=key, severity="info")
            cand = next(c for c in lines.tiles[pid].candidates if c.cand_id == new_cand)
            baseline = baseline_art.panels.get(pid) if baseline_art else None
            series_art.panels[key] = ps = build_panel_series(
                ctx, tile, panels_by_id[pid], cal_art.panels[pid], cand, baseline,
                key=key, series_id=ps.series_id, series_label=ps.series_label)
            ctx.save(lines, "lines.json")
            ctx.save(series_art, "series.json")

        final = art.panels.get(key)
        if final is None:
            continue
        if final.verdict in gates.qc_block_on:
            ctx.add_flag("qc", f"major deviation persists: {final.reason}", panel_id=key,
                         severity="blocking", artifact_ref=final.overlay)
        elif final.verdict == "minor":
            ctx.add_flag("qc", f"minor deviation: {final.reason}", panel_id=key,
                         artifact_ref=final.overlay)
    ctx.save(art, "qc.json")

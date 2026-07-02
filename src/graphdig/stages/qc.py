"""QC stage: Gemini judges the extracted curve - and can veto and reselect.

Replaces the paper's human visual inspection (inspector.py, Sect. 4.5.4): verdicts
ok / minor / major with issue tags. New in this stage: `qc_auto_reselect` closes the loop
the paper left manual - a "major / wrong line" verdict rejects the offending candidate,
selection reruns over the remaining viable candidates (Gemini pick when available), the
series is rebuilt, and the new curve is judged again (bounded by qc_max_reselect).
Unrecoverable majors stay as blocking review flags.
"""

from __future__ import annotations

from graphdig.artifacts import PanelQc, Provenance, QcArtifact, Selection, SeriesArtifact
from graphdig.gemini.client import GeminiUnavailable
from graphdig.gemini.prompts import PROMPTS
from graphdig.gemini.schemas import QcResponse
from graphdig.pipeline import Context
from graphdig.stages.series import build_panel_series, load_context_artifacts

_ACTION = {"ok": "accept", "minor": "review", "major": "reextract"}


def _judge(ctx: Context, pid: str) -> tuple[PanelQc | None, Provenance | None]:
    tile_path = ctx.run_dir / "tiles" / f"{pid}.png"
    overlay_rel = f"overlays/curve_{pid}.png"
    overlay_path = ctx.run_dir / overlay_rel
    if not overlay_path.exists():
        return None, None
    result = ctx.gemini.generate_json(
        images=[tile_path, overlay_path], prompt=PROMPTS["QC_V1"], schema=QcResponse,
        prompt_id="QC_V1", thinking_level=ctx.cfg.gemini.thinking_qc,
        media_resolution="high",
    )
    if not result.ok:
        ctx.add_flag("qc", f"Gemini call failed: {result.error}", panel_id=pid)
        return None, None
    r = result.data
    qc = PanelQc(verdict=r.verdict, issues=r.issues, reason=r.reason,
                 suggested_action=_ACTION.get(r.verdict, "review"),
                 confidence=r.confidence, overlay=overlay_rel)
    prov = Provenance(model=result.model, prompt_id=result.prompt_id,
                      thinking_level=result.thinking_level,
                      attempts=result.attempts, usage=result.usage)
    return qc, prov


def _reselect(ctx: Context, lines, tile) -> int | None:
    """Reject the current candidate and pick an alternative; None if none remains."""
    from graphdig.stages.select import gemini_pick

    tl = lines.tiles[tile.tile_id]
    tl.rejected.append(tl.selected.cand_id)
    alternatives = [c for c in tl.candidates
                    if c.cand_id not in tl.rejected and (c.viable or not tl.rejected)]
    alternatives = [c for c in alternatives if c.viable] or alternatives
    if not alternatives:
        return None
    alternatives.sort(key=lambda c: -(c.s_alpha or 0.0))
    chosen = alternatives[0].cand_id
    method = "qc_reselect_s_alpha"
    if len(alternatives) >= 2:
        try:
            pick = gemini_pick(ctx, tile, alternatives[:6])
        except Exception:
            pick = None
        if pick is not None:
            chosen, method = pick, "qc_reselect_gemini_pick"
    tl.selected = Selection(cand_id=chosen, method=method,
                            alpha_coverage=ctx.cfg.gates.alpha_coverage)
    return chosen


def run(ctx: Context) -> None:
    series_art = ctx.load(SeriesArtifact, "series.json")
    panels_art, cal_art, lines, tiles_art, baseline_art = load_context_artifacts(ctx)
    panels_by_id = {p.panel_id: p for p in panels_art.panels}
    tiles_by_id = {t.tile_id: t for t in tiles_art.tiles}
    gates = ctx.cfg.gates

    art = QcArtifact()
    for pid in list(series_art.panels):
        for attempt in range(gates.qc_max_reselect + 1):
            try:
                qc, prov = _judge(ctx, pid)
            except GeminiUnavailable as exc:
                ctx.add_flag("qc", f"skipped: {exc}", severity="info")
                ctx.save(art, "qc.json")
                return
            if qc is None:
                break
            art.panels[pid] = qc
            if prov:
                art.provenance = prov
            if qc.verdict not in gates.qc_block_on or not gates.qc_auto_reselect:
                break
            if attempt >= gates.qc_max_reselect:
                break
            tile = tiles_by_id[pid]
            new_cand = _reselect(ctx, lines, tile)
            if new_cand is None:
                ctx.add_flag("qc", "major verdict but no alternative candidate left",
                             panel_id=pid, severity="blocking")
                break
            ctx.add_flag("qc", f"QC rejected candidate; reselected cand {new_cand}",
                         panel_id=pid, severity="info")
            cand = next(c for c in lines.tiles[pid].candidates if c.cand_id == new_cand)
            baseline = baseline_art.panels.get(pid) if baseline_art else None
            series_art.panels[pid] = build_panel_series(
                ctx, tile, panels_by_id[pid], cal_art.panels[pid], cand, baseline)
            ctx.save(lines, "lines.json")
            ctx.save(series_art, "series.json")

        final = art.panels.get(pid)
        if final is None:
            continue
        if final.verdict in gates.qc_block_on:
            ctx.add_flag("qc", f"major deviation persists: {final.reason}", panel_id=pid,
                         severity="blocking", artifact_ref=final.overlay)
        elif final.verdict == "minor":
            ctx.add_flag("qc", f"minor deviation: {final.reason}", panel_id=pid,
                         artifact_ref=final.overlay)
    ctx.save(art, "qc.json")

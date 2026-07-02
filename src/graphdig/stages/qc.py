"""QC stage: Gemini judges the extracted curve against the original tile.

Replaces the paper's human visual inspection with inspector.py (Sect. 4.5.4): verdicts
ok / minor / major with issue tags. Majors are blocking review flags; the run still
completes so a human can triage from review/flags.json and the overlays.
"""

from __future__ import annotations

from graphdig.artifacts import PanelQc, Provenance, QcArtifact, SeriesArtifact
from graphdig.gemini.client import GeminiUnavailable
from graphdig.gemini.prompts import PROMPTS
from graphdig.gemini.schemas import QcResponse
from graphdig.pipeline import Context

_ACTION = {"ok": "accept", "minor": "review", "major": "reextract"}


def run(ctx: Context) -> None:
    series_art = ctx.load(SeriesArtifact, "series.json")
    art = QcArtifact()
    for pid in series_art.panels:
        tile_path = ctx.run_dir / "tiles" / f"{pid}.png"
        overlay_rel = f"overlays/curve_{pid}.png"
        overlay_path = ctx.run_dir / overlay_rel
        if not overlay_path.exists():
            continue
        try:
            result = ctx.gemini.generate_json(
                images=[tile_path, overlay_path], prompt=PROMPTS["QC_V1"],
                schema=QcResponse, prompt_id="QC_V1",
                thinking_level=ctx.cfg.gemini.thinking_qc, media_resolution="high",
            )
        except GeminiUnavailable as exc:
            ctx.add_flag("qc", f"skipped: {exc}", severity="info")
            ctx.save(art, "qc.json")
            return
        if not result.ok:
            ctx.add_flag("qc", f"Gemini call failed: {result.error}", panel_id=pid,
                         severity="warning")
            continue
        r = result.data
        art.panels[pid] = PanelQc(verdict=r.verdict, issues=r.issues, reason=r.reason,
                                  suggested_action=_ACTION.get(r.verdict, "review"),
                                  confidence=r.confidence, overlay=overlay_rel)
        art.provenance = Provenance(model=result.model, prompt_id=result.prompt_id,
                                    thinking_level=result.thinking_level,
                                    attempts=result.attempts, usage=result.usage)
        if r.verdict in ctx.cfg.gates.qc_block_on:
            ctx.add_flag("qc", f"major deviation: {r.reason}", panel_id=pid,
                         severity="blocking", artifact_ref=overlay_rel)
        elif r.verdict == "minor":
            ctx.add_flag("qc", f"minor deviation: {r.reason}", panel_id=pid,
                         severity="warning", artifact_ref=overlay_rel)
    ctx.save(art, "qc.json")

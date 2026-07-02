"""Metadata stage: page-level document metadata (station, year, units, notes)."""

from __future__ import annotations

from PIL import Image

from graphdig.artifacts import MetadataArtifact, PanelsArtifact, Provenance, UnitTransition
from graphdig.gemini.prompts import metadata_prompt
from graphdig.gemini.schemas import MetadataResponse
from graphdig.pipeline import Context


def run(ctx: Context) -> None:
    panels_art = ctx.load(PanelsArtifact, "panels.json")
    page = Image.open(ctx.run_dir / panels_art.image.path)

    prompt_id, prompt = metadata_prompt(ctx.cfg.profile.panel_prompt_variant)
    result = ctx.gemini.generate_json(
        images=[page], prompt=prompt, schema=MetadataResponse, prompt_id=prompt_id,
        thinking_level=ctx.cfg.gemini.thinking_metadata, media_resolution="high",
    )
    if not result.ok:
        ctx.add_flag("metadata", f"Gemini call failed: {result.error}", severity="warning")
        ctx.save(MetadataArtifact(), "metadata.json")
        return

    r = result.data
    art = MetadataArtifact(
        title=r.title, station=r.station, year=r.year or None, date_range=r.date_range,
        y_unit_declared=r.y_unit,
        unit_transition=UnitTransition(present=r.unit_transition_present,
                                       date=r.unit_transition_date or None),
        language=r.language, handwritten_annotations=r.handwritten_annotations,
        notes=r.notes, confidence=r.confidence,
        provenance=Provenance(model=result.model, prompt_id=result.prompt_id,
                              thinking_level=result.thinking_level,
                              attempts=result.attempts, usage=result.usage),
    )
    ctx.save(art, "metadata.json")

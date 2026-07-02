"""Extract stage: dispatch tiles to the configured line-extraction backend."""

from __future__ import annotations

from graphdig.artifacts import TilesArtifact
from graphdig.extractors import ExtractParams, get_extractor
from graphdig.pipeline import Context


def run(ctx: Context) -> None:
    tiles_art = ctx.load(TilesArtifact, "tiles.json")
    extractor = get_extractor(ctx.cfg.extractor, ctx)
    params = ExtractParams(max_per_image=ctx.cfg.lineformer_max_per_image)
    art = extractor.extract(tiles_art.tiles, ctx.run_dir, params)
    for tile_id, tl in art.tiles.items():
        if tl.error:
            ctx.add_flag("extract", f"extraction failed: {tl.error}",
                         panel_id=tile_id, severity="blocking")
        elif not tl.candidates:
            ctx.add_flag("extract", "no polyline candidates returned",
                         panel_id=tile_id, severity="blocking")
    ctx.save(art, "lines.json")

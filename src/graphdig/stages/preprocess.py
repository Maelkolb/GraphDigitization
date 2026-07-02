"""Preprocess stage: cut panel tiles and stretch the time axis.

Paper Sect. 4.5.1-4.5.2: per-panel cropping to the plot area removes empty vertical space,
and a purely horizontal anisotropic stretch (s = 2.0, bicubic) widens steep strokes for the
line extractor without touching the y calibration. The Transform2D recorded per tile maps
extracted points back to page space exactly.
"""

from __future__ import annotations

from PIL import Image

from graphdig.artifacts import PanelsArtifact, Tile, TilesArtifact
from graphdig.geometry import Transform2D
from graphdig.pipeline import Context
from graphdig.runs import sha256_file


def run(ctx: Context) -> None:
    panels_art = ctx.load(PanelsArtifact, "panels.json")
    page = Image.open(ctx.run_dir / panels_art.image.path)
    stretch = ctx.cfg.x_stretch

    art = TilesArtifact()
    for panel in panels_art.panels:
        area = panel.plot_area_px or panel.bbox_px
        crop = page.crop((area.x, area.y, area.right, area.bottom))
        if stretch != 1.0:
            crop = crop.resize((max(1, round(crop.width * stretch)), crop.height),
                               Image.BICUBIC)
        tile_path = ctx.run_dir / "tiles" / f"{panel.panel_id}.png"
        crop.convert("RGB").save(tile_path)
        art.tiles.append(Tile(
            tile_id=panel.panel_id,
            path=f"tiles/{panel.panel_id}.png",
            panel_id=panel.panel_id,
            transform=Transform2D(crop_x=area.x, crop_y=area.y,
                                  x_scale=stretch, y_scale=1.0),
            width=crop.width, height=crop.height,
            sha256=sha256_file(tile_path),
        ))
    ctx.save(art, "tiles.json")

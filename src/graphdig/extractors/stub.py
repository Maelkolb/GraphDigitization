"""Stub backend: candidates come from sidecar JSON files or an injected mapping.

Used in tests and dry runs so the whole pipeline can execute without the pinned
LineFormer environment. Sidecar format: `<tile>.lines.json` next to the tile PNG,
containing `[{"confidence": 0.9, "points": [[x, y], ...]}, ...]` in tile coordinates.
"""

from __future__ import annotations

import json
from pathlib import Path

from graphdig.artifacts import LineCandidate, LinesArtifact, Tile, TileLines
from graphdig.extractors.base import ExtractParams, LineExtractor


class StubExtractor(LineExtractor):
    name = "stub"

    def __init__(self, candidates: dict[str, list[LineCandidate]] | None = None):
        self._injected = candidates or {}

    def extract(self, tiles: list[Tile], run_dir: Path,
                params: ExtractParams) -> LinesArtifact:
        art = LinesArtifact(backend=self.name,
                            params={"max_per_image": params.max_per_image})
        for tile in tiles:
            if tile.tile_id in self._injected:
                art.tiles[tile.tile_id] = TileLines(candidates=self._injected[tile.tile_id])
                continue
            sidecar = Path(run_dir) / (tile.path + ".lines.json")
            if sidecar.exists():
                raw = json.loads(sidecar.read_text(encoding="utf-8"))
                cands = [LineCandidate(cand_id=i, confidence=c.get("confidence", 1.0),
                                       n_points=len(c["points"]),
                                       points_px_tile=c["points"])
                         for i, c in enumerate(raw)]
                art.tiles[tile.tile_id] = TileLines(candidates=cands)
            else:
                art.tiles[tile.tile_id] = TileLines(
                    error="stub backend: no sidecar candidates provided")
        return art

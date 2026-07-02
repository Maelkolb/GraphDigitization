"""Line-extraction backend interface.

Backends receive preprocessed tiles and return candidate polylines in TILE pixel
coordinates with per-candidate confidence. Everything else (coverage, s_alpha, selection,
mapping back to page space) happens in the select/series stages, identically for every
backend - which is what makes local CPU, Colab GPU, and the test stub interchangeable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from graphdig.artifacts import LinesArtifact, Tile


@dataclass(frozen=True)
class ExtractParams:
    max_per_image: int = 100
    device: str = "cpu"


class LineExtractor(ABC):
    name: str = "base"

    @abstractmethod
    def extract(self, tiles: list[Tile], run_dir: Path,
                params: ExtractParams) -> LinesArtifact:
        """Return a LinesArtifact with candidates for every tile (tile coordinates)."""

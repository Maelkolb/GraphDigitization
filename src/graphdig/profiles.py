"""Pipeline profiles: bundled defaults for known chart families."""

from __future__ import annotations

from pydantic import BaseModel


class Profile(BaseModel):
    name: str
    expected_panels: int | None = None  # validated when set (danube: 12 monthly panels)
    baseline_enabled: bool = False
    daily_sampling: bool = False  # x is calendar time, resample to one point per day
    danube_units: bool = False  # enforce foot/mm transition rule by date
    panel_prompt_variant: str = "generic"  # selects prompt flavor in gemini/prompts.py
    refine_x_edges: bool = False  # snap panel x-edges to printed gridlines (day grids)
    check_orientation: bool = True  # dedicated 4-way upright check before triage
    coverage_viable: float | None = None  # None = use Gates default (danube-tuned 0.985)
    extract_margin: float = 0.03  # tile safety margin around the plot area


DANUBE = Profile(
    name="danube",
    expected_panels=12,
    baseline_enabled=True,
    daily_sampling=True,
    danube_units=True,
    panel_prompt_variant="danube",
    refine_x_edges=True,
    check_orientation=False,  # archival tiles/sheets are consistently upright
    extract_margin=0.0,  # dataset tiles already carry a margin; more would expose
    #                      slivers of the neighboring months' curves
)

# arbitrary charts: curves legitimately start/end inside the plot area, so the
# danube-tuned coverage bound (full-month curves) is far too strict
GENERIC = Profile(name="generic", coverage_viable=0.90)

PROFILES: dict[str, Profile] = {p.name: p for p in (DANUBE, GENERIC)}

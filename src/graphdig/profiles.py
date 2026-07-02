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


DANUBE = Profile(
    name="danube",
    expected_panels=12,
    baseline_enabled=True,
    daily_sampling=True,
    danube_units=True,
    panel_prompt_variant="danube",
)

GENERIC = Profile(name="generic")

PROFILES: dict[str, Profile] = {p.name: p for p in (DANUBE, GENERIC)}

"""Live Gemini smoke tests - structure and plausibility only, never exact values.

Run with: uv run pytest -m live   (skipped automatically without GEMINI_API_KEY)
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.live

SAMPLES = Path(__file__).parents[1] / "data" / "samples"


def _client():
    from graphdig.config import GeminiConfig
    from graphdig.gemini.client import GeminiClient, GeminiUnavailable

    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            or (Path(".env").exists() and "GEMINI_API_KEY" in Path(".env").read_text())):
        pytest.skip("no GEMINI_API_KEY configured")
    try:
        return GeminiClient(GeminiConfig())
    except GeminiUnavailable as exc:
        pytest.skip(str(exc))


def test_panels_on_forestry_chart():
    from graphdig.gemini.prompts import panels_prompt
    from graphdig.gemini.schemas import PanelsResponse

    client = _client()
    prompt_id, prompt = panels_prompt("generic")
    result = client.generate_json(images=[SAMPLES / "forestry_A382_019.jpeg"],
                                  prompt=prompt, schema=PanelsResponse,
                                  prompt_id=prompt_id, thinking_level="high",
                                  media_resolution="high")
    assert result.ok, result.error
    assert len(result.data.panels) >= 1
    for p in result.data.panels:
        assert 0 <= p.box.x0 <= 1000 and 0 <= p.box.y1 <= 1000
        assert 0.0 <= p.confidence <= 1.0


def test_calibration_on_synthetic_chart(tmp_path):
    from conftest import make_synthetic_chart
    from graphdig.calibration.fit import Tick, fit_axis
    from graphdig.gemini.prompts import PROMPTS
    from graphdig.gemini.schemas import AxisCalResponse

    client = _client()
    img, spec = make_synthetic_chart()
    result = client.generate_json(images=[img], prompt=PROMPTS["CALIB_V1"],
                                  schema=AxisCalResponse, prompt_id="CALIB_V1",
                                  thinking_level="high", media_resolution="ultra_high")
    assert result.ok, result.error
    ticks = [Tick(pixel=t.pos_1000 / 1000.0 * img.height, value=t.value)
             for t in result.data.y_ticks if t.legible]
    assert len(ticks) >= 3, f"expected >=3 legible ticks, got {len(ticks)}"
    fit = fit_axis(ticks)
    assert fit.r2 > 0.99
    # slope must match the analytic mapping within 5 % (whole-image coordinates)
    assert abs(fit.slope - spec.y_slope) / abs(spec.y_slope) < 0.05


def test_qc_verdict_schema(tmp_path):
    from conftest import make_synthetic_chart
    from graphdig.gemini.prompts import PROMPTS
    from graphdig.gemini.schemas import QcResponse

    client = _client()
    img, _spec = make_synthetic_chart()
    tile = img.crop((150, 150, 1050, 750))
    result = client.generate_json(images=[tile, tile], prompt=PROMPTS["QC_V1"],
                                  schema=QcResponse, prompt_id="QC_V1",
                                  thinking_level="medium")
    assert result.ok, result.error
    assert result.data.verdict in ("ok", "minor", "major")

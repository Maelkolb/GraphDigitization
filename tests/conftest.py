"""Shared fixtures: FakeGeminiClient and a synthetic chart with analytic ground truth."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest
from PIL import Image, ImageDraw
from pydantic import BaseModel

from graphdig.gemini.client import GeminiResult


class FakeGeminiClient:
    """Canned responses keyed by prompt_id; a list is consumed call-by-call (last repeats)."""

    def __init__(self, responses: dict[str, BaseModel | list[BaseModel]]):
        self.responses = {k: list(v) if isinstance(v, list) else [v]
                          for k, v in responses.items()}
        self.calls: list[str] = []

    def generate_json(self, *, images, prompt, schema, prompt_id,
                      thinking_level="medium", media_resolution=None) -> GeminiResult:
        self.calls.append(prompt_id)
        queue = self.responses.get(prompt_id)
        if not queue:
            return GeminiResult(data=None, error=f"no canned response for {prompt_id}",
                                prompt_id=prompt_id, model="fake")
        data = queue.pop(0) if len(queue) > 1 else queue[0]
        assert isinstance(data, schema), f"canned response type mismatch for {prompt_id}"
        return GeminiResult(data=data, raw_text=data.model_dump_json(), attempts=1,
                            prompt_id=prompt_id, model="fake", thinking_level=thinking_level)


@dataclass(frozen=True)
class SynthChart:
    """Ground truth of the synthetic chart image."""

    width: int = 1200
    height: int = 900
    # outer panel bbox and inner plot area, pixel coords
    bbox: tuple[int, int, int, int] = (100, 100, 1100, 800)
    plot: tuple[int, int, int, int] = (150, 150, 1050, 750)
    # y calibration: value = (750 - y) / 10  -> slope -0.1, zero at pixel y=750
    y_slope: float = -0.1
    y_zero_pixel: float = 750.0
    baseline_y: float = 750.0

    def value_at(self, y_px: float) -> float:
        return (self.y_zero_pixel - y_px) * (-self.y_slope)

    def pixel_at(self, value: float) -> float:
        return self.y_zero_pixel - value / (-self.y_slope)

    def curve_y(self, x_px: np.ndarray) -> np.ndarray:
        """Smooth known curve inside the plot area (values 5..55)."""
        x0, _, x1, _ = self.plot
        t = (np.asarray(x_px, dtype=float) - x0) / (x1 - x0)
        values = 30 + 25 * np.sin(2 * np.pi * t) * np.exp(-t)
        return self.y_zero_pixel - values * 10


def make_synthetic_chart(spec: SynthChart | None = None) -> tuple[Image.Image, SynthChart]:
    spec = spec or SynthChart()
    img = Image.new("RGB", (spec.width, spec.height), (245, 240, 228))
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = spec.plot

    # grid + y ticks with labels every 10 units (values 0..60)
    for value in range(0, 61, 10):
        y = spec.pixel_at(value)
        d.line([(x0, y), (x1, y)], fill=(200, 195, 185), width=1)
        d.line([(x0 - 12, y), (x0, y)], fill=(60, 60, 60), width=2)
        d.text((x0 - 48, y - 7), f"{value}", fill=(60, 60, 60))
    for gx in np.linspace(x0, x1, 31):
        d.line([(gx, y0), (gx, y1)], fill=(210, 205, 195), width=1)

    # axes box
    d.rectangle([x0, y0, x1, y1], outline=(60, 60, 60), width=2)
    # printed zero/reference line (thicker, darker) at value 0
    d.line([(x0, spec.baseline_y), (x1, spec.baseline_y)], fill=(20, 20, 20), width=4)

    # the data curve
    xs = np.arange(x0, x1)
    ys = spec.curve_y(xs)
    d.line(list(zip(xs.tolist(), ys.tolist(), strict=False)), fill=(40, 40, 120), width=3)

    d.text((spec.width // 2 - 60, 40), "Synthetic Gauge 1848", fill=(30, 30, 30))
    return img, spec


@pytest.fixture
def synth_chart(tmp_path):
    img, spec = make_synthetic_chart()
    path = tmp_path / "synth_chart.png"
    img.save(path)
    return path, spec


GERMAN_MONTH_NAMES = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
                      "August", "September", "Oktober", "November", "Dezember"]


@dataclass(frozen=True)
class SynthYearPage:
    """Analytic ground truth of the synthetic 12-panel annual sheet."""

    year: int = 1849
    margin_left: int = 80
    plot_top: int = 60
    plot_h: int = 300
    ppd: float = 6.0  # pixels per day
    y_zero: float = 360.0  # pixel row of value 0; value = (y_zero - y) / 10
    y_slope: float = -0.1

    def value_at(self, y_px: float) -> float:
        return (self.y_zero - y_px) / 10.0

    def pixel_at(self, value: float) -> float:
        return self.y_zero - value * 10.0

    def month_value(self, month: int, t: float) -> float:
        """Analytic per-month curve, t in [0, 1] across the month."""
        return 12.0 + 8.0 * np.sin(2 * np.pi * t) + 0.5 * month

    def panel_boxes(self) -> list[tuple[int, int, int, int]]:
        """Plot-area (x0, y0, x1, y1) per month, left to right."""
        import calendar

        out = []
        x = self.margin_left
        for m in range(1, 13):
            w = round(self.ppd * calendar.monthrange(self.year, m)[1])
            out.append((x, self.plot_top, x + w, self.plot_top + self.plot_h))
            x += w
        return out

    @property
    def width(self) -> int:
        return self.panel_boxes()[-1][2] + 20

    @property
    def height(self) -> int:
        return self.plot_top + self.plot_h + 60


def make_synthetic_year_page(spec: SynthYearPage | None = None):
    spec = spec or SynthYearPage()
    img = Image.new("RGB", (spec.width, spec.height), (246, 241, 230))
    d = ImageDraw.Draw(img)

    for value in range(0, 31, 5):  # margin value labels + shared gridlines
        y = spec.pixel_at(value)
        d.line([(spec.margin_left, y), (spec.width - 20, y)], fill=(205, 200, 190))
        d.text((10, y - 6), f"{value}", fill=(60, 60, 60))

    for m, (x0, y0, x1, y1) in enumerate(spec.panel_boxes(), start=1):
        d.rectangle([x0, y0, x1, y1], outline=(70, 70, 70), width=2)
        d.text((x0 + 4, 30), GERMAN_MONTH_NAMES[m - 1], fill=(40, 40, 40))
        xs = np.arange(x0, x1)
        ts = (xs - x0) / (x1 - x0)
        ys = spec.pixel_at(spec.month_value(m, ts))
        d.line(list(zip(xs.tolist(), ys.tolist(), strict=False)), fill=(40, 40, 120), width=2)
    d.text((spec.width // 2 - 40, 8), f"Pegel Synthetic {spec.year}", fill=(30, 30, 30))
    return img, spec


@pytest.fixture
def synth_year_page(tmp_path):
    img, spec = make_synthetic_year_page()
    path = tmp_path / "synth_year.png"
    img.save(path)
    return path, spec

"""Calibrate stage: Gemini reads axis ticks, local math fits the pixel->value mapping.

Automates the paper's manual y-axis anchor extraction (Sect. 4.4.2) and generalizes it:
instead of two hand-picked anchors, Gemini reports every legible tick and an IRLS/MAD fit
with R^2 / residual gates provides self-verification. The paper's two-anchor form is kept
as `anchor_equivalent` for provenance and evaluation.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from PIL import Image

from graphdig.artifacts import (
    AnchorEquivalent,
    CalibrationArtifact,
    FitModel,
    Panel,
    PanelCalibration,
    PanelsArtifact,
    Provenance,
    TickModel,
    UnitModel,
    XAxisCal,
    YAxisCal,
)
from graphdig.calibration.fit import Tick, fit_axis, value_at
from graphdig.dates import days_in_month, parse_date_label
from graphdig.gemini.prompts import PROMPTS
from graphdig.gemini.schemas import AxisCalResponse
from graphdig.pipeline import Context
from graphdig.render import draw_calibration

CROP_MARGIN = 0.08  # fraction of panel size added around the bbox for the calibration crop


def crop_box_for(panel: Panel, width: int, height: int):
    b = panel.bbox_px
    return b.expand(int(CROP_MARGIN * b.w), int(CROP_MARGIN * b.h), width, height)


def _calibrate_panel(ctx: Context, page: Image.Image, panel: Panel) -> tuple[str, PanelCalibration, Provenance]:
    gates = ctx.cfg.gates
    crop_box = crop_box_for(panel, page.width, page.height)
    crop = page.crop((crop_box.x, crop_box.y, crop_box.right, crop_box.bottom))
    crop_path = ctx.run_dir / "panels" / f"{panel.panel_id}.png"
    crop.save(crop_path)

    result = ctx.gemini.generate_json(
        images=[crop], prompt=PROMPTS["CALIB_V1"], schema=AxisCalResponse,
        prompt_id="CALIB_V1", thinking_level=ctx.cfg.gemini.thinking_calibrate,
        media_resolution="ultra_high",
    )
    provenance = Provenance(model=result.model, prompt_id=result.prompt_id,
                            thinking_level=result.thinking_level,
                            attempts=result.attempts, usage=result.usage)
    if not result.ok:
        ctx.add_flag("calibrate", f"Gemini call failed: {result.error}",
                     panel_id=panel.panel_id, severity="blocking")
        return panel.panel_id, PanelCalibration(review_required=True), provenance

    resp = result.data
    y_axis, fit = _build_y_axis(ctx, resp, crop_box, panel.panel_id, gates)
    x_axis = _build_x_axis(resp, panel)

    cal = PanelCalibration(y_axis=y_axis, x_axis=x_axis,
                           review_required="unusable" in y_axis.flags)
    draw_calibration(page, panel, cal, fit,
                     ctx.run_dir / "overlays" / f"cal_{panel.panel_id}.png")
    return panel.panel_id, cal, provenance


def _build_y_axis(ctx: Context, resp: AxisCalResponse, crop_box, panel_id: str, gates):
    from graphdig.units import canonicalize

    ticks_in = [t for t in resp.y_ticks if t.legible]
    seen: set[tuple[int, float]] = set()
    ticks: list[Tick] = []
    for t in ticks_in:
        page_y = crop_box.y + t.pos_1000 / 1000.0 * crop_box.h
        key = (round(page_y), t.value)
        if key in seen:
            continue
        seen.add(key)
        ticks.append(Tick(pixel=page_y, value=t.value, label_text=t.label_text))

    unit = canonicalize(resp.y_unit_text)
    flags: list[str] = []
    fit = None
    if len(ticks) >= 2:
        try:
            fit = fit_axis(ticks, scale=resp.y_scale)
        except ValueError as exc:
            flags.append(f"fit failed: {exc}")
    if fit is None:
        flags.append("unusable")
        ctx.add_flag("calibrate", f"no usable axis fit ({len(ticks)} ticks)",
                     panel_id=panel_id, severity="blocking")
        y = YAxisCal(scale=resp.y_scale, unit=UnitModel(raw=resp.y_unit_text,
                                                        canonical=unit.canonical,
                                                        to_mm=unit.to_mm),
                     ticks=[TickModel(pixel=t.pixel, value=t.value, label_text=t.label_text)
                            for t in ticks],
                     confidence=resp.confidence, flags=flags)
        return y, None

    if fit.method == "two_anchor" and gates.cal_min_ticks > 2:
        flags.append("two_anchor_only")
        ctx.add_flag("calibrate", "only 2 legible ticks; using two-anchor mapping",
                     panel_id=panel_id, severity="warning")
    if fit.r2 < gates.cal_r2_min:
        flags.append(f"low_r2:{fit.r2:.4f}")
        ctx.add_flag("calibrate", f"axis fit r2={fit.r2:.4f} below gate {gates.cal_r2_min}",
                     panel_id=panel_id, severity="warning")
    values = [t.value for t in fit.ticks if t.used]
    vrange = max(values) - min(values) if len(values) > 1 else 0.0
    if vrange > 0 and fit.rmse_value / vrange > gates.cal_max_rel_residual:
        flags.append("high_residual")
        ctx.add_flag("calibrate",
                     f"relative fit residual {fit.rmse_value / vrange:.3f} above gate",
                     panel_id=panel_id, severity="warning")

    used_pixels = [t.pixel for t in fit.ticks if t.used]
    c_low, c_high = max(used_pixels), min(used_pixels)  # low value sits lower on the page
    anchor = AnchorEquivalent(c_low=c_low, v_low=float(value_at(fit, c_low)),
                              c_high=c_high, v_high=float(value_at(fit, c_high)))

    y = YAxisCal(
        scale=resp.y_scale,
        unit=UnitModel(raw=resp.y_unit_text, canonical=unit.canonical, to_mm=unit.to_mm),
        ticks=[TickModel(pixel=t.pixel, value=t.value, label_text=t.label_text,
                         used=t.used, residual=t.residual) for t in fit.ticks],
        fit=FitModel(method=fit.method, slope=fit.slope, intercept=fit.intercept,
                     scale=fit.scale, r2=fit.r2, rmse_value=fit.rmse_value,
                     n_ticks=fit.n_ticks, n_used=fit.n_used, n_rejected=fit.n_rejected),
        anchor_equivalent=anchor,
        confidence=resp.confidence,
        flags=flags,
    )
    return y, fit


def _build_x_axis(resp: AxisCalResponse, panel: Panel) -> XAxisCal:
    start_label = resp.x_start_label or panel.x_extent_hint.start_label
    end_label = resp.x_end_label or panel.x_extent_hint.end_label
    x = XAxisCal(kind=resp.x_kind, start=start_label, end=end_label,
                 confidence=resp.confidence)
    if resp.x_kind == "date":
        d0 = parse_date_label(start_label)
        d1 = parse_date_label(end_label, default_year=d0.year if d0 else None)
        if d0 and d1 and d1 >= d0:
            x.start, x.end = d0.isoformat(), d1.isoformat()
            x.n_samples = (d1 - d0).days + 1
        elif d0 and not d1:
            # single month label: assume the panel spans that whole month (danube tiles)
            n = days_in_month(d0.year, d0.month)
            x.start = d0.replace(day=1).isoformat()
            x.end = d0.replace(day=n).isoformat()
            x.n_samples = n
        else:
            x.flags.append("dates_unparsed")
    elif resp.x_kind == "numeric":
        try:
            n0, n1 = float(start_label), float(end_label)
            if n1 > n0 and float(n1 - n0).is_integer():
                x.n_samples = int(n1 - n0) + 1
        except ValueError:
            x.flags.append("numeric_extent_unparsed")
    return x


def run(ctx: Context) -> None:
    panels_art = ctx.load(PanelsArtifact, "panels.json")
    page = Image.open(ctx.run_dir / panels_art.image.path)

    art = CalibrationArtifact()
    with ThreadPoolExecutor(max_workers=ctx.cfg.workers) as pool:
        futures = [pool.submit(_calibrate_panel, ctx, page, p) for p in panels_art.panels]
        for fut in futures:
            panel_id, cal, provenance = fut.result()
            art.panels[panel_id] = cal
            art.provenance = provenance
    ctx.save(art, "calibration.json")

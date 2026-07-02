"""Calibrate stage: pixel -> physical value mapping, chosen by what the chart offers.

Three calibration paths, selected by the triage classification:
1. AXIS TICKS (default): Gemini reads every legible y-axis tick, local IRLS/MAD
   least-squares fit with R^2/residual gates. Generalizes the paper's manual two-anchor
   extraction (Sect. 4.4.2) with self-verification the 2-anchor method cannot do.
   If the first pass finds nothing although triage saw labels, one retry with an
   emphasized prompt runs before giving up.
2. CURVE LABELS (fallback for axis-less charts): when values are written directly along
   the curve, Gemini reads each (point, value) pair and the same least-squares machinery
   fits the axis from those - the labels ARE calibration points.
3. NONE: neither axis nor labels -> the panel is flagged for external calibration
   (e.g. danube-prep annotations) instead of pretending.

The paper's two-anchor form is kept as `anchor_equivalent` for provenance and evaluation.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from PIL import Image

from graphdig.artifacts import (
    AnchorEquivalent,
    CalibrationArtifact,
    FitModel,
    PageClassification,
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
from graphdig.gemini.schemas import AxisCalResponse, CurveLabelsResponse
from graphdig.pipeline import Context
from graphdig.render import draw_calibration

CROP_MARGIN = 0.08  # fraction of panel size added around the bbox for the calibration crop


def crop_box_for(panel: Panel, width: int, height: int):
    b = panel.bbox_px
    return b.expand(int(CROP_MARGIN * b.w), int(CROP_MARGIN * b.h), width, height)


def _provenance(result) -> Provenance:
    return Provenance(model=result.model, prompt_id=result.prompt_id,
                      thinking_level=result.thinking_level,
                      attempts=result.attempts, usage=result.usage)


# ------------------------------------------------------------------ tick collection

def _ticks_from_axis(ctx: Context, crop, crop_box, expect_labels: bool):
    """Axis-tick reading, with one emphasized retry when triage promised labels."""
    for prompt_id in ("CALIB_V1", "CALIB_V1_RETRY"):
        result = ctx.gemini.generate_json(
            images=[crop], prompt=PROMPTS[prompt_id], schema=AxisCalResponse,
            prompt_id=prompt_id, thinking_level=ctx.cfg.gemini.thinking_calibrate,
            media_resolution="ultra_high",
        )
        if not result.ok:
            return None, [], result
        ticks = _dedupe([
            Tick(pixel=crop_box.y + t.pos_1000 / 1000.0 * crop_box.h,
                 value=t.value, label_text=t.label_text)
            for t in result.data.y_ticks if t.legible
        ])
        if ticks or not expect_labels:
            return result.data, ticks, result
    return result.data, [], result  # retried and still empty


def _ticks_from_curve_labels(ctx: Context, crop, crop_box):
    """Axis fit derived from values written along the curve (axis-less charts)."""
    result = ctx.gemini.generate_json(
        images=[crop], prompt=PROMPTS["CURVE_LABELS_V1"], schema=CurveLabelsResponse,
        prompt_id="CURVE_LABELS_V1", thinking_level=ctx.cfg.gemini.thinking_calibrate,
        media_resolution="ultra_high",
    )
    if not result.ok:
        return None, [], result
    ticks = _dedupe([
        Tick(pixel=crop_box.y + lab.y_1000 / 1000.0 * crop_box.h,
             value=lab.value, label_text=lab.label_text)
        for lab in result.data.labels if lab.legible
    ])
    return result.data, ticks, result


def _dedupe(ticks: list[Tick]) -> list[Tick]:
    seen: set[tuple[int, float]] = set()
    out = []
    for t in ticks:
        key = (round(t.pixel), t.value)
        if key not in seen:
            seen.add(key)
            out.append(t)
    return out


# ------------------------------------------------------------------------- fitting

def _fit_y_axis(ctx: Context, ticks: list[Tick], scale: str, unit_text: str,
                confidence: float, panel_id: str, method_flag: str | None):
    from graphdig.units import canonicalize

    gates = ctx.cfg.gates
    unit = canonicalize(unit_text)
    flags: list[str] = [method_flag] if method_flag else []
    fit = None
    if len(ticks) >= 2:
        try:
            fit = fit_axis(ticks, scale=scale)
        except ValueError as exc:
            flags.append(f"fit failed: {exc}")

    unit_model = UnitModel(raw=unit_text, canonical=unit.canonical, to_mm=unit.to_mm)
    if fit is None:
        flags.append("unusable")
        ctx.add_flag("calibrate", f"no usable axis fit ({len(ticks)} calibration points)",
                     panel_id=panel_id, severity="blocking")
        return YAxisCal(scale="linear" if scale == "unknown" else scale, unit=unit_model,
                        ticks=[TickModel(pixel=t.pixel, value=t.value,
                                         label_text=t.label_text) for t in ticks],
                        confidence=confidence, flags=flags), None

    if fit.method == "two_anchor" and gates.cal_min_ticks > 2:
        flags.append("two_anchor_only")
        ctx.add_flag("calibrate", "only 2 calibration points; using two-anchor mapping",
                     panel_id=panel_id)
    if fit.r2 < gates.cal_r2_min:
        flags.append(f"low_r2:{fit.r2:.4f}")
        ctx.add_flag("calibrate", f"axis fit r2={fit.r2:.4f} below gate {gates.cal_r2_min}",
                     panel_id=panel_id)
    values = [t.value for t in fit.ticks if t.used]
    vrange = max(values) - min(values) if len(values) > 1 else 0.0
    if vrange > 0 and fit.rmse_value / vrange > gates.cal_max_rel_residual:
        flags.append("high_residual")
        ctx.add_flag("calibrate",
                     f"relative fit residual {fit.rmse_value / vrange:.3f} above gate",
                     panel_id=panel_id)

    used_pixels = [t.pixel for t in fit.ticks if t.used]
    c_low, c_high = max(used_pixels), min(used_pixels)
    anchor = AnchorEquivalent(c_low=c_low, v_low=float(value_at(fit, c_low)),
                              c_high=c_high, v_high=float(value_at(fit, c_high)))
    y = YAxisCal(
        scale=fit.scale, unit=unit_model,
        ticks=[TickModel(pixel=t.pixel, value=t.value, label_text=t.label_text,
                         used=t.used, residual=t.residual) for t in fit.ticks],
        fit=FitModel(method=fit.method, slope=fit.slope, intercept=fit.intercept,
                     scale=fit.scale, r2=fit.r2, rmse_value=fit.rmse_value,
                     n_ticks=fit.n_ticks, n_used=fit.n_used, n_rejected=fit.n_rejected),
        anchor_equivalent=anchor, confidence=confidence, flags=flags,
    )
    return y, fit


def _build_x_axis(kind: str, start_label: str, end_label: str, panel: Panel,
                  confidence: float) -> XAxisCal:
    start_label = start_label or panel.x_extent_hint.start_label
    end_label = end_label or panel.x_extent_hint.end_label
    x = XAxisCal(kind=kind if kind in ("date", "numeric") else "unknown",
                 start=start_label, end=end_label, confidence=confidence)
    if x.kind == "date":
        d0 = parse_date_label(start_label)
        d1 = parse_date_label(end_label, default_year=d0.year if d0 else None)
        if d0 and d1 and d1 >= d0:
            x.start, x.end = d0.isoformat(), d1.isoformat()
            x.n_samples = (d1 - d0).days + 1
        elif d0 and not d1:
            n = days_in_month(d0.year, d0.month)  # single month label (danube tiles)
            x.start = d0.replace(day=1).isoformat()
            x.end = d0.replace(day=n).isoformat()
            x.n_samples = n
        else:
            x.flags.append("dates_unparsed")
    elif x.kind == "numeric":
        n0, n1 = _lenient_float(start_label), _lenient_float(end_label)
        if n0 is not None and n1 is not None and n0 != n1:
            x.start, x.end = f"{n0:g}", f"{n1:g}"
            if float(abs(n1 - n0)).is_integer():
                x.n_samples = int(abs(n1 - n0)) + 1  # descending extents supported
            if n1 < n0:
                x.flags.append("descending")
        else:
            x.flags.append("numeric_extent_unparsed")
    return x


def _lenient_float(label: str) -> float | None:
    """First number in a label, tolerating unit marks like '30"' or '34 Zoll'."""
    import re

    m = re.search(r"-?\d+(?:[.,]\d+)?", label)
    return float(m.group(0).replace(",", ".")) if m else None


# --------------------------------------------------------------------------- stage

def _calibrate_panel(ctx: Context, page: Image.Image, panel: Panel,
                     cls: PageClassification):
    crop_box = crop_box_for(panel, page.width, page.height)
    crop = page.crop((crop_box.x, crop_box.y, crop_box.right, crop_box.bottom))
    crop.save(ctx.run_dir / "panels" / f"{panel.panel_id}.png")

    use_curve_labels = cls.value_labels_on_curve and not cls.y_axis_labels_present
    if use_curve_labels:
        resp, ticks, result = _ticks_from_curve_labels(ctx, crop, crop_box)
        unit_text = resp.unit_text if resp else ""
        scale = cls.y_scale_guess
        confidence = resp.confidence if resp else 0.0
        method_flag = "curve_labels"
        x_axis = _build_x_axis("unknown", "", "", panel, confidence)
    else:
        resp, ticks, result = _ticks_from_axis(ctx, crop, crop_box,
                                               expect_labels=cls.y_axis_labels_present)
        unit_text = resp.y_unit_text if resp else ""
        scale = resp.y_scale if resp else "linear"
        confidence = resp.confidence if resp else 0.0
        method_flag = None
        x_axis = (_build_x_axis(resp.x_kind, resp.x_start_label, resp.x_end_label,
                                panel, confidence) if resp
                  else _build_x_axis("unknown", "", "", panel, 0.0))
        # axis empty but chart carries curve labels -> use them instead of giving up
        if not ticks and cls.value_labels_on_curve:
            resp2, ticks2, result2 = _ticks_from_curve_labels(ctx, crop, crop_box)
            if ticks2:
                ticks, result = ticks2, result2
                unit_text = unit_text or (resp2.unit_text if resp2 else "")
                confidence = max(confidence, resp2.confidence if resp2 else 0.0)
                method_flag = "curve_labels"

    if result is not None and not result.ok:
        ctx.add_flag("calibrate", f"Gemini call failed: {result.error}",
                     panel_id=panel.panel_id, severity="blocking")
        return panel.panel_id, PanelCalibration(review_required=True), _provenance(result)

    y_axis, fit = _fit_y_axis(ctx, ticks, scale, unit_text, confidence,
                              panel.panel_id, method_flag)
    cal = PanelCalibration(y_axis=y_axis, x_axis=x_axis,
                           review_required="unusable" in y_axis.flags)
    draw_calibration(page, panel, cal, fit,
                     ctx.run_dir / "overlays" / f"cal_{panel.panel_id}.png")
    return panel.panel_id, cal, _provenance(result)


def run(ctx: Context) -> None:
    panels_art = ctx.load(PanelsArtifact, "panels.json")
    page = Image.open(ctx.run_dir / panels_art.image.path)
    page.load()  # decode now: lazy loading is not thread-safe across panel workers

    art = CalibrationArtifact()
    with ThreadPoolExecutor(max_workers=ctx.cfg.workers) as pool:
        futures = [pool.submit(_calibrate_panel, ctx, page, p, panels_art.classification)
                   for p in panels_art.panels]
        for fut in futures:
            panel_id, cal, provenance = fut.result()
            art.panels[panel_id] = cal
            art.provenance = provenance
    ctx.save(art, "calibration.json")

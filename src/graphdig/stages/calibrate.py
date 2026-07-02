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

CROP_MARGIN = 0.12  # fraction of panel size added around the bbox for the calibration crop
#                     (generous: axis labels often sit well outside the detected panel box)


def crop_box_for(panel: Panel, width: int, height: int):
    b = panel.bbox_px
    return b.expand(int(CROP_MARGIN * b.w), int(CROP_MARGIN * b.h), width, height)


def _margin_crop_box(panel: Panel, width: int, height: int, edge: str):
    """Edge panels retry with a crop extended to the page margin, where full sheets
    carry their value labels (outside every panel bbox)."""
    from graphdig.geometry import BoxPx

    b = panel.bbox_px
    my = int(0.12 * b.h)
    y0, y1 = max(0, b.y - my), min(height, b.bottom + my)
    if edge == "left":
        x1 = min(width, b.right + int(0.05 * b.w))
        return BoxPx(x=0, y=y0, w=x1, h=y1 - y0)
    x0 = max(0, b.x - int(0.05 * b.w))
    return BoxPx(x=x0, y=y0, w=width - x0, h=y1 - y0)


def _provenance(result) -> Provenance:
    return Provenance(model=result.model, prompt_id=result.prompt_id,
                      thinking_level=result.thinking_level,
                      attempts=result.attempts, usage=result.usage)


# ------------------------------------------------------------------ tick collection

def _ticks_from_axis(ctx: Context, crop, crop_box, expect_labels: bool):
    """Axis-tick reading, with one emphasized retry when triage promised labels.

    Returns ticks together with their reported panel side ('left'/'right'/'unknown') so
    dual-scale charts can be fitted per side.
    """
    for prompt_id in ("CALIB_V1", "CALIB_V1_RETRY"):
        result = ctx.gemini.generate_json(
            images=[crop], prompt=PROMPTS[prompt_id], schema=AxisCalResponse,
            prompt_id=prompt_id, thinking_level=ctx.cfg.gemini.thinking_calibrate,
            media_resolution="ultra_high",
        )
        if not result.ok:
            return None, [], result
        pairs = _dedupe_sided([
            (Tick(pixel=crop_box.y + t.pos_1000 / 1000.0 * crop_box.h,
                  value=t.value, label_text=t.label_text), t.side)
            for t in result.data.y_ticks if t.legible
        ])
        if pairs or not expect_labels:
            return result.data, pairs, result
    return result.data, [], result  # retried and still empty


def _dedupe_sided(pairs):
    seen: set[tuple[int, float]] = set()
    out = []
    for tick, side in pairs:
        key = (round(tick.pixel), tick.value)
        if key not in seen:
            seen.add(key)
            out.append((tick, side))
    return out


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

def _fit_with_scale_fallback(ticks: list[Tick], scale: str, gates,
                             flags: list[str]):
    """Fit with the declared scale; when unknown or clearly failing, try the other."""
    candidates: list = []
    primary = scale if scale in ("linear", "log") else "linear"
    for s in dict.fromkeys([primary, "log" if primary == "linear" else "linear"]):
        if s == "log" and any(t.value <= 0 for t in ticks):
            continue
        try:
            candidates.append(fit_axis(ticks, scale=s))
        except ValueError as exc:
            flags.append(f"fit failed ({s}): {exc}")
    if not candidates:
        return None
    best = max(candidates, key=lambda f: f.r2)
    # keep the declared scale unless the alternative is clearly better
    declared = next((f for f in candidates if f.scale == primary), None)
    if (declared is not None and scale in ("linear", "log")
            and best.scale != primary and best.r2 - declared.r2 < 0.05):
        best = declared
    if best.scale != primary and scale in ("linear", "log"):
        flags.append(f"scale_auto:{best.scale}")
    return best


def _pick_axis_side(pairs, dual_expected: bool, flags: list[str]):
    """On dual-scale charts fit each side separately and keep the better one.

    Mixing ticks from two different scales is what breaks charts like the 1890s medical
    diagrams (percent left, absolute counts right): one linear map cannot satisfy both,
    so the fit collapses. Fitting per side and keeping the better-supported scale keeps
    the calibration valid (values then refer to that scale, recorded in the flags).
    """
    lefts = [t for t, s in pairs if s == "left"]
    rights = [t for t, s in pairs if s == "right"]
    unknowns = [t for t, s in pairs if s not in ("left", "right")]
    two_sided = len(lefts) >= 2 and len(rights) >= 2
    if dual_expected and not two_sided:
        # fallback: two scales usually differ by orders of magnitude (percent vs counts);
        # split at the largest log10 gap and fit the clusters separately
        split = _magnitude_split([t for t, _ in pairs])
        if split is not None:
            lefts, rights = split
            unknowns = []
            two_sided = True
            flags.append("dual_axis:magnitude_split")
        else:
            flags.append("dual_axis_expected_but_sides_untagged")
    if two_sided:
        best_side, best_ticks, best_fit = None, None, None
        for side, group in (("left", lefts + unknowns), ("right", rights + unknowns)):
            try:
                fit = fit_axis(group)
            except ValueError:
                continue
            score = fit.r2 * min(1.0, fit.n_used / 3)
            if best_fit is None or score > best_fit.r2 * min(1.0, best_fit.n_used / 3):
                best_side, best_ticks, best_fit = side, group, fit
        if best_side is not None:
            flags.append(f"dual_axis:{best_side}_scale_used")
            return best_ticks
    return [t for t, _ in pairs]


def _magnitude_split(ticks: list[Tick]):
    """Split ticks into two clusters at the largest >1.5-decade value gap, if any."""
    import math

    positive = [t for t in ticks if t.value > 0]
    if len(positive) < 4 or len(positive) < len(ticks) - 2:
        return None
    ordered = sorted(positive, key=lambda t: t.value)
    gaps = [(math.log10(ordered[i + 1].value / ordered[i].value), i)
            for i in range(len(ordered) - 1) if ordered[i + 1].value > ordered[i].value]
    if not gaps:
        return None
    best_gap, idx = max(gaps)
    if best_gap < 1.5:
        return None
    low, high = ordered[:idx + 1], ordered[idx + 1:]
    if len(low) < 2 or len(high) < 2:
        return None
    return low, high


def _fit_y_axis(ctx: Context, ticks: list[Tick], scale: str, unit_text: str,
                confidence: float, panel_id: str, pre_flags: list[str]):
    from graphdig.units import canonicalize

    gates = ctx.cfg.gates
    unit = canonicalize(unit_text)
    flags: list[str] = list(pre_flags)
    fit = None
    if len(ticks) >= 2:
        fit = _fit_with_scale_fallback(ticks, scale, gates, flags)

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


def _prefer_month_hint(x_axis: XAxisCal, panel: Panel) -> XAxisCal:
    """A date x-extent from the month assignment beats bare numeric day labels
    ('1'..'31') read off the axis - the danube multi-panel date fix."""
    hint = panel.x_extent_hint
    if hint.kind != "date":
        return x_axis
    d0 = parse_date_label(hint.start_label)
    d1 = parse_date_label(hint.end_label, default_year=d0.year if d0 else None)
    if not (d0 and d1 and d1 >= d0):
        return x_axis
    if x_axis.kind == "date" and x_axis.n_samples:
        return x_axis
    return XAxisCal(kind="date", start=d0.isoformat(), end=d1.isoformat(),
                    n_samples=(d1 - d0).days + 1,
                    confidence=max(x_axis.confidence, 0.9),
                    flags=[*x_axis.flags, "x_from_month_hint"])


def _share_y_fit(art: CalibrationArtifact, ctx: Context) -> None:
    """Annual sheets share one value scale: the best-supported panel fit becomes the
    donor for panels whose own labels were unreadable; usable fits are checked against
    the donor for consistency."""
    def score(pc: PanelCalibration) -> float:
        f = pc.y_axis.fit
        return f.r2 * min(1.0, f.n_used / 3) if f else -1.0

    usable = {pid: pc for pid, pc in art.panels.items()
              if pc.y_axis.fit is not None and "unusable" not in pc.y_axis.flags}
    if not usable:
        return
    donor_pid, donor = max(usable.items(), key=lambda kv: score(kv[1]))
    donor_slope = donor.y_axis.fit.slope
    for pid, pc in art.panels.items():
        if pid == donor_pid:
            continue
        if pc.y_axis.fit is None or "unusable" in pc.y_axis.flags:
            shared = donor.y_axis.model_copy(deep=True)
            shared.flags = [*shared.flags, f"y_fit_shared_from:{donor_pid}"]
            pc.y_axis = shared
            pc.review_required = False
            ctx.add_flag("calibrate", f"y calibration shared from {donor_pid}",
                         panel_id=pid, severity="info")
        elif donor_slope and abs(pc.y_axis.fit.slope - donor_slope) / abs(donor_slope) > 0.03:
            pc.y_axis.flags.append("y_fit_inconsistent")
            ctx.add_flag("calibrate",
                         f"y-fit slope differs from donor {donor_pid} by "
                         f"{abs(pc.y_axis.fit.slope - donor_slope) / abs(donor_slope):.1%}",
                         panel_id=pid, severity="warning")


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


# ---------------------------------------------------------------- user-anchor path

def _x_axis_from_hint(ph, panel: Panel) -> XAxisCal | None:
    if ph is None or not (ph.x_start or ph.x_end):
        return None
    kind = "date" if parse_date_label(ph.x_start) or parse_date_label(ph.x_end) else "numeric"
    x = _build_x_axis(kind, ph.x_start, ph.x_end, panel, confidence=1.0)
    x.flags.append("user_hint:x_extent")
    return x


def _calibrate_from_user_anchors(ctx: Context, page: Image.Image, panel: Panel,
                                 cls: PageClassification, user_ticks, crop, crop_box):
    """Hints provide the calibration; Gemini (if labels exist) only cross-checks."""
    from graphdig.hints import panel_hint_for

    hints = ctx.hints
    scale = hints.y_scale or (cls.y_scale_guess if cls.y_scale_guess != "unknown"
                              else "linear")
    y_axis, fit = _fit_y_axis(ctx, user_ticks, scale, hints.unit, 1.0,
                              panel.panel_id, ["user_hint:y_anchors"])
    if y_axis.fit is not None:
        y_axis.fit.method = "user_anchors"

    provenance = Provenance(model="user_hint", prompt_id="hints.json")
    if cls.y_axis_labels_present and fit is not None:
        _resp, pairs, result = _ticks_from_axis(ctx, crop, crop_box, expect_labels=False)
        if result is not None and result.ok and pairs:
            provenance = _provenance(result)
            try:
                gemini_fit = fit_axis(_pick_axis_side(pairs, cls.dual_y_axis, []),
                                      scale=scale if scale in ("linear", "log")
                                      else "linear")
                span = abs(value_at(fit, crop_box.y)
                           - value_at(fit, crop_box.bottom)) or 1.0
                worst = max(abs(float(value_at(gemini_fit, t.pixel)) - t.value)
                            for t in user_ticks)
                if worst / span > 0.05:
                    y_axis.flags.append("hint_gemini_mismatch")
                    ctx.add_flag("calibrate",
                                 f"Gemini axis reading disagrees with user anchors by "
                                 f"{worst / span:.1%} of the span (hint wins)",
                                 panel_id=panel.panel_id, severity="warning")
            except ValueError:
                pass

    ph = panel_hint_for(hints, panel.panel_id, panel.month)
    x_axis = (_x_axis_from_hint(ph, panel)
              or _prefer_month_hint(_build_x_axis("unknown", "", "", panel, 1.0), panel))
    cal = PanelCalibration(y_axis=y_axis, x_axis=x_axis,
                           review_required="unusable" in y_axis.flags)
    draw_calibration(page, panel, cal, fit,
                     ctx.run_dir / "overlays" / f"cal_{panel.panel_id}.png")
    return panel.panel_id, cal, provenance


# --------------------------------------------------------------------------- stage

def _calibrate_panel(ctx: Context, page: Image.Image, panel: Panel,
                     cls: PageClassification, edge: str | None = None):
    crop_box = crop_box_for(panel, page.width, page.height)
    crop = page.crop((crop_box.x, crop_box.y, crop_box.right, crop_box.bottom))
    crop.save(ctx.run_dir / "panels" / f"{panel.panel_id}.png")

    from graphdig.hints import hint_ticks

    user_ticks = hint_ticks(ctx.hints, panel.panel_id, panel.month)
    if len(user_ticks) >= 2:
        return _calibrate_from_user_anchors(ctx, page, panel, cls, user_ticks,
                                            crop, crop_box)

    pre_flags: list[str] = []
    use_curve_labels = cls.value_labels_on_curve and not cls.y_axis_labels_present
    if use_curve_labels:
        resp, ticks, result = _ticks_from_curve_labels(ctx, crop, crop_box)
        unit_text = resp.unit_text if resp else ""
        scale = cls.y_scale_guess
        confidence = resp.confidence if resp else 0.0
        pre_flags.append("curve_labels")
        x_axis = _build_x_axis("unknown", "", "", panel, confidence)
    else:
        resp, pairs, result = _ticks_from_axis(ctx, crop, crop_box,
                                               expect_labels=cls.y_axis_labels_present)
        ticks = _pick_axis_side(pairs, cls.dual_y_axis, pre_flags)
        unit_text = resp.y_unit_text if resp else ""
        scale = resp.y_scale if resp else "linear"
        confidence = resp.confidence if resp else 0.0
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
                pre_flags.append("curve_labels")

    if result is not None and not result.ok:
        ctx.add_flag("calibrate", f"Gemini call failed: {result.error}",
                     panel_id=panel.panel_id, severity="blocking")
        return panel.panel_id, PanelCalibration(review_required=True), _provenance(result)

    # edge panels of full sheets retry with a crop extended into the page margin,
    # where the value labels actually live
    if not ticks and edge and cls.y_axis_labels_present and not use_curve_labels:
        mbox = _margin_crop_box(panel, page.width, page.height, edge)
        mcrop = page.crop((mbox.x, mbox.y, mbox.right, mbox.bottom))
        resp_m, pairs_m, result_m = _ticks_from_axis(ctx, mcrop, mbox,
                                                     expect_labels=False)
        if result_m is not None and result_m.ok and pairs_m:
            ticks = _pick_axis_side(pairs_m, cls.dual_y_axis, pre_flags)
            pre_flags.append("margin_crop_retry")
            unit_text = unit_text or (resp_m.y_unit_text if resp_m else "")
            result = result_m

    y_axis, fit = _fit_y_axis(ctx, ticks, scale, unit_text, confidence,
                              panel.panel_id, pre_flags)
    x_axis = _prefer_month_hint(x_axis, panel)
    cal = PanelCalibration(y_axis=y_axis, x_axis=x_axis,
                           review_required="unusable" in y_axis.flags)
    draw_calibration(page, panel, cal, fit,
                     ctx.run_dir / "overlays" / f"cal_{panel.panel_id}.png")
    return panel.panel_id, cal, _provenance(result)


def run(ctx: Context) -> None:
    panels_art = ctx.load(PanelsArtifact, "panels.json")
    page = Image.open(ctx.run_dir / panels_art.image.path)
    page.load()  # decode now: lazy loading is not thread-safe across panel workers

    panels = panels_art.panels
    edges: dict[str, str] = {}
    if len(panels) > 1:  # leftmost/rightmost panels sit next to the labeled page margins
        by_x = sorted(panels, key=lambda p: p.bbox_px.x)
        edges[by_x[0].panel_id] = "left"
        edges[by_x[-1].panel_id] = "right"

    art = CalibrationArtifact()
    with ThreadPoolExecutor(max_workers=ctx.cfg.workers) as pool:
        futures = [pool.submit(_calibrate_panel, ctx, page, p,
                               panels_art.classification, edges.get(p.panel_id))
                   for p in panels]
        for fut in futures:
            panel_id, cal, provenance = fut.result()
            art.panels[panel_id] = cal
            art.provenance = provenance
    if ctx.cfg.profile.shared_y_scale and len(art.panels) > 1:
        _share_y_fit(art, ctx)
    ctx.save(art, "calibration.json")

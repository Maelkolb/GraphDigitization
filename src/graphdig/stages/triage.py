"""Triage stage: one Gemini pass that decides what the page IS before anything runs.

Replaces the former separate panels + metadata stages (one call instead of two) and adds
the chart classification that steers the rest of the pipeline:
- chart_kind / page_kind - is this a digitizable line chart at all?
- y_axis_labels_present - can the calibrate stage read an axis, or must calibration come
  from values written along the curve (curve-label path) or external annotations?
- rotation - applied ITERATIVELY: after rotating, triage runs again on the rotated image
  until it reports 0 (max 3 turns), which also catches upside-down pages that a single
  pass would leave at 180 degrees.

Automates the paper's month_annotator bounding boxes (Rehbein 2026, Sect. 4.5.1); because
"a small x-overshoot can shift the date assignment by a whole day", panel x-edges can be
snapped to the strongest printed vertical gridline nearby (danube profile).
"""

from __future__ import annotations

import itertools

import numpy as np
from PIL import Image

from graphdig.artifacts import (
    ImageRef,
    MetadataArtifact,
    Orientation,
    PageClassification,
    Panel,
    PanelsArtifact,
    Provenance,
    UnitTransition,
    XExtentHint,
)
from graphdig.gemini.prompts import PROMPTS, triage_prompt
from graphdig.gemini.schemas import OrientationResponse, TriageResponse
from graphdig.geometry import Box1000, BoxPx, bbox_1000_to_px
from graphdig.pipeline import Context
from graphdig.render import draw_panels

IOU_DEDUPE = 0.8
EDGE_SEARCH_FRACTION = 0.01  # gridline-snap window, fraction of page width
MAX_ROTATION_TURNS = 3
DIGITIZABLE_KINDS = {"line_chart", "multi_panel_line_chart", "scatter", "other"}


def _detect(ctx: Context, img: Image.Image, prompt_id: str, prompt: str):
    result = ctx.gemini.generate_json(
        images=[img], prompt=prompt, schema=TriageResponse, prompt_id=prompt_id,
        thinking_level=ctx.cfg.gemini.thinking_panels, media_resolution="high",
    )
    if not result.ok:
        raise RuntimeError(f"triage failed: {result.error}")
    return result


def _norm_rotation(deg: int) -> int:
    return round((deg % 360) / 90) * 90 % 360


def _orientation_composite(img: Image.Image, cell: int = 560) -> Image.Image:
    """2x2 grid of the page in all four rotations, labeled 0/90/180/270."""
    from PIL import ImageDraw, ImageFont

    header = 46
    canvas = Image.new("RGB", (2 * cell, 2 * (cell + header)), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except OSError:
        font = ImageFont.load_default()
    for i, deg in enumerate((0, 90, 180, 270)):
        rot = img if deg == 0 else img.rotate(-deg, expand=True)
        rot = rot.copy()
        rot.thumbnail((cell, cell))
        cx, cy = (i % 2) * cell, (i // 2) * (cell + header)
        draw.text((cx + cell // 2 - 30, cy + 4), str(deg), fill=(200, 30, 30), font=font)
        canvas.paste(rot, (cx + (cell - rot.width) // 2, cy + header))
    return canvas


def _orientation_check(ctx: Context, img: Image.Image) -> int:
    """Dedicated 4-way upright comparison - more reliable than asking about a single
    view (a lone triage pass sometimes misses rotation entirely)."""
    result = ctx.gemini.generate_json(
        images=[_orientation_composite(img)], prompt=PROMPTS["ORIENT_V1"],
        schema=OrientationResponse, prompt_id="ORIENT_V1",
        thinking_level="low", media_resolution="high",
    )
    if not result.ok:
        ctx.add_flag("triage", f"orientation check failed ({result.error}); "
                     "relying on triage rotation only", severity="info")
        return 0
    return _norm_rotation(result.data.rotation_deg)


def _to_panels(resp: TriageResponse, width: int, height: int,
               conf_min: float) -> tuple[list[Panel], list[str]]:
    flags: list[str] = []
    panels: list[Panel] = []
    for gp in resp.panels:
        bbox = bbox_1000_to_px(Box1000(**gp.box.model_dump()), width, height, min_size=20)
        plot = bbox_1000_to_px(Box1000(**gp.plot_area.model_dump()), width, height, min_size=10)
        plot = _clamp_plot_area(plot, bbox)
        panels.append(Panel(
            panel_id="", label=gp.label, bbox_px=bbox, plot_area_px=plot,
            x_extent_hint=XExtentHint(kind="unknown", start_label=gp.x_start_label,
                                      end_label=gp.x_end_label),
            confidence=gp.confidence,
        ))
    panels.sort(key=lambda p: -p.confidence)
    kept: list[Panel] = []
    for p in panels:  # drop near-duplicates, keep the higher-confidence one
        if any(p.bbox_px.iou(k.bbox_px) > IOU_DEDUPE for k in kept):
            continue
        kept.append(p)
    low = [p for p in kept if p.confidence < conf_min]
    for p in low:
        p.flags.append("low_confidence")
    if low:
        flags.append(f"{len(low)} panel(s) below confidence gate")
    # reading order: row bands, then left to right
    band = max(1, max(p.bbox_px.h for p in kept) // 2) if kept else 1
    kept.sort(key=lambda p: (p.bbox_px.y // band, p.bbox_px.x))
    for i, p in enumerate(kept, start=1):
        p.panel_id = f"p{i:02d}"
    return kept, flags


def _clamp_plot_area(plot: BoxPx, bbox: BoxPx) -> BoxPx:
    """The plot area must sit inside the panel bbox; degenerate answers fall back to it."""
    x0 = min(max(plot.x, bbox.x), bbox.right - 1)
    y0 = min(max(plot.y, bbox.y), bbox.bottom - 1)
    x1 = max(min(plot.right, bbox.right), x0 + 1)
    y1 = max(min(plot.bottom, bbox.bottom), y0 + 1)
    clamped = BoxPx(x=x0, y=y0, w=x1 - x0, h=y1 - y0)
    # implausibly small plot areas (< 25% of the bbox) are usually hallucinated
    if clamped.w * clamped.h < 0.25 * bbox.w * bbox.h:
        return bbox
    return clamped


def _column_strength(page: Image.Image, y0: int, y1: int) -> np.ndarray:
    """Vertical-edge strength per x column within a row band (gridline/seam detector)."""
    import cv2

    gray = np.asarray(page.convert("L"), dtype=np.float32)
    sobel = np.abs(cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3))
    return sobel[max(0, y0):max(0, y1)].sum(axis=0)


def _assign_month_spans(panels: list[Panel], year: int | None, ctx: Context) -> None:
    """Give each panel a calendar-month identity and a date x-extent.

    Month names parsed from the labels; when too few parse (or the order is broken),
    fall back to reading-order position - annual sheets run January..December.
    """
    from graphdig.dates import month_from_name, month_span

    parsed = 0
    for p in panels:
        if p.month:  # hint-assigned months are authoritative
            continue
        for line in p.label.splitlines():
            m = month_from_name(line.strip())
            if m:
                p.month = m
                parsed += 1
                break
    months = [p.month for p in panels if p.month]
    ordered = all(a < b for a, b in itertools.pairwise(months))
    if len(panels) > 1 and (len(months) < max(1, round(0.66 * len(panels)))
                            or not ordered):
        for i, p in enumerate(panels):
            p.month = i + 1
        ctx.add_flag("triage", "month_assignment:positional "
                     f"({parsed}/{len(panels)} labels parsed as months)", severity="info")
    if year:
        for p in panels:
            if p.month and 1 <= p.month <= 12:
                d0, d1 = month_span(year, p.month)
                p.x_extent_hint = XExtentHint(kind="date", start_label=d0.isoformat(),
                                              end_label=d1.isoformat())


def _split_panel(page: Image.Image, panel: Panel, k: int) -> list[Panel]:
    """Split a box spanning k months at the k-1 strongest interior vertical seams."""
    b = panel.bbox_px
    strength = _column_strength(page, b.y, b.bottom)
    cuts = [b.x]
    for j in range(1, k):
        target = b.x + round(j * b.w / k)
        window = max(4, round(0.08 * b.w / k))
        lo, hi = max(b.x + 4, target - window), min(b.right - 4, target + window + 1)
        cuts.append(lo + int(np.argmax(strength[lo:hi])))
    cuts.append(b.right)
    out = []
    for x0, x1 in itertools.pairwise(cuts):
        sub_bbox = BoxPx(x=x0, y=b.y, w=x1 - x0, h=b.h)
        plot = panel.plot_area_px
        sub_plot = sub_bbox
        if plot is not None:
            px0, px1 = max(plot.x, x0), min(plot.right, x1)
            if px1 - px0 > 4:
                sub_plot = BoxPx(x=px0, y=plot.y, w=px1 - px0, h=plot.h)
        out.append(Panel(panel_id="", label=panel.label, bbox_px=sub_bbox,
                         plot_area_px=sub_plot, confidence=panel.confidence,
                         flags=[*panel.flags, "split_from_multimonth_box"]))
    return out


def _reconcile_panel_count(page: Image.Image, panels: list[Panel], expected: int,
                           ctx: Context) -> list[Panel]:
    """Repair panel over/under-segmentation toward the expected count."""
    if not panels or len(panels) == expected:
        return panels
    med_w = float(np.median([p.bbox_px.w for p in panels]))

    if len(panels) > expected:  # drop slivers first
        keep = [p for p in panels if p.bbox_px.w >= 0.3 * med_w]
        if len(keep) != len(panels):
            ctx.add_flag("triage", f"dropped {len(panels) - len(keep)} sliver panel(s)",
                         severity="info")
        panels = keep

    if len(panels) < expected:  # split boxes that span multiple months
        out: list[Panel] = []
        missing = expected - len(panels)
        for p in panels:
            k = round(p.bbox_px.w / med_w)
            if k >= 2 and missing > 0:
                take = min(k, missing + 1)
                out.extend(_split_panel(page, p, take))
                missing -= take - 1
                ctx.add_flag("triage", f"split a {k}-month-wide box into {take} panels",
                             severity="info")
            else:
                out.append(p)
        panels = out

    panels.sort(key=lambda p: p.bbox_px.x)
    for i, p in enumerate(panels, start=1):
        p.panel_id = f"p{i:02d}"
    if len(panels) != expected:
        ctx.add_flag("triage",
                     f"panel count {len(panels)} != expected {expected} after "
                     "reconciliation; supply --hints with panels[].bbox_px to fix",
                     severity="blocking")
    return panels


def _validate_month_widths(panels: list[Panel], year: int, ctx: Context) -> None:
    """Panel width must be proportional to its month's day count (day-shift guard)."""
    from graphdig.dates import days_in_month

    ppd = []
    for p in panels:
        if p.month and p.plot_area_px:
            ppd.append(p.plot_area_px.w / days_in_month(year, p.month))
    if len(ppd) < 3:
        return
    med = float(np.median(ppd))
    for p in panels:
        if not (p.month and p.plot_area_px) or med <= 0:
            continue
        days_est = p.plot_area_px.w / med
        expected_days = days_in_month(year, p.month)
        if abs(days_est - expected_days) > 0.5:
            p.flags.append("month_width_outlier")
            ctx.add_flag("triage",
                         f"panel width implies {days_est:.1f} days, month has "
                         f"{expected_days} (possible edge error)",
                         panel_id=p.panel_id, severity="warning")


def _refine_x_edges(page: Image.Image, panels: list[Panel]) -> None:
    """Snap plot-area left/right edges to the strongest vertical gridline nearby."""
    import cv2

    gray = np.asarray(page.convert("L"), dtype=np.float32)
    sobel = np.abs(cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3))
    window = max(3, int(page.width * EDGE_SEARCH_FRACTION))
    for p in panels:
        area = p.plot_area_px
        if area is None or area.w < 4 * window:
            continue
        col_strength = sobel[area.y:area.bottom].sum(axis=0)
        new_edges = {}
        for name, edge in (("left", area.x), ("right", area.right)):
            lo, hi = max(0, edge - window), min(page.width, edge + window + 1)
            if hi - lo >= 3:
                new_edges[name] = lo + int(np.argmax(col_strength[lo:hi]))
        left = new_edges.get("left", area.x)
        right = new_edges.get("right", area.right)
        if right - left > 2 * window:
            p.plot_area_px = BoxPx(x=left, y=area.y, w=right - left, h=area.h)
            p.x_edge_refined = True


def run(ctx: Context) -> None:
    pages = sorted((ctx.run_dir / "pages").glob("*.png"))
    page_path = pages[0]
    img = Image.open(page_path)
    img.load()

    prompt_id, prompt = triage_prompt(ctx.cfg.profile.panel_prompt_variant)
    hints = ctx.hints

    total_rotation = 0
    if hints is not None and hints.rotation_deg is not None:
        # a rotation hint is authoritative: skip both orientation mechanisms
        total_rotation = _norm_rotation(hints.rotation_deg)
        if total_rotation:
            img = img.rotate(-total_rotation, expand=True)
        result = _detect(ctx, img, prompt_id, prompt)
    else:
        # dedicated 4-way upright check first (cheap), then triage loop as backstop
        if ctx.cfg.profile.check_orientation:
            deg = _orientation_check(ctx, img)
            if deg:
                total_rotation = deg
                img = img.rotate(-deg, expand=True)  # PIL rotates counter-clockwise
        result = _detect(ctx, img, prompt_id, prompt)
        for _turn in range(MAX_ROTATION_TURNS):
            deg = _norm_rotation(result.data.rotation_deg)
            if deg == 0:
                break
            total_rotation = (total_rotation + deg) % 360
            img = img.rotate(-deg, expand=True)  # PIL rotates counter-clockwise
            result = _detect(ctx, img, prompt_id, prompt)
        else:
            ctx.add_flag("triage", "orientation did not converge after "
                         f"{MAX_ROTATION_TURNS} turns", severity="warning")
    orientation = Orientation(rotation_applied_deg=total_rotation,
                              reason="triage: labels not upright" if total_rotation else "")
    if total_rotation:
        page_path = page_path.with_name(page_path.stem + f"_rot{total_rotation}.png")
        img.save(page_path)

    resp = result.data
    classification = PageClassification(
        chart_kind=resp.chart_kind, page_kind=resp.page_kind,
        y_axis_labels_present=resp.y_axis_labels_present,
        value_labels_on_curve=resp.value_labels_on_curve,
        y_scale_guess=resp.y_scale_guess,
        dual_y_axis=resp.dual_y_axis,
        n_series=max(1, resp.n_series),
        series_labels=[s for s in resp.series_labels if s][:max(1, resp.n_series)],
        confidence=resp.confidence,
    )
    if classification.n_series > 1:
        ctx.add_flag("triage", f"multi-series chart: {classification.n_series} curves "
                     f"({', '.join(classification.series_labels) or 'unlabelled'})",
                     severity="info")
    if resp.chart_kind not in DIGITIZABLE_KINDS:
        ctx.add_flag("triage", f"page classified as '{resp.chart_kind}' - "
                     "not a digitizable line chart", severity="blocking")
    if not resp.y_axis_labels_present and not resp.value_labels_on_curve:
        ctx.add_flag("triage", "no axis labels and no curve labels: absolute calibration "
                     "impossible from this image alone (relative digitization only)",
                     severity="warning")

    panels, flags = _to_panels(resp, img.width, img.height, ctx.cfg.gates.panel_conf_min)
    for reason in flags:
        ctx.add_flag("triage", reason)
    if hints is not None and any(ph.bbox_px for ph in hints.panels):
        panels = _panels_from_hints(hints, img.width, img.height)
        ctx.add_flag("triage", f"panel geometry taken from hints ({len(panels)} panels)",
                     severity="info")
    expected = (hints.expected_panels if hints and hints.expected_panels
                else ctx.cfg.profile.expected_panels)
    if expected and len(panels) not in (1, expected):
        ctx.add_flag("triage", f"expected 1 or {expected} panels, got {len(panels)}")
        if len(panels) > 1:
            panels = _reconcile_panel_count(img, panels, expected, ctx)
    if not panels:
        ctx.add_flag("triage", "no chart panels detected", severity="blocking")

    if hints is not None:
        from graphdig.hints import panel_hint_for

        for p in panels:
            ph = panel_hint_for(hints, p.panel_id)
            if ph and ph.month:
                p.month = ph.month
    if ctx.cfg.profile.daily_sampling and panels:
        year_known = (hints.year if hints and hints.year else None) or (resp.year or None)
        _assign_month_spans(panels, year_known, ctx)
        if year_known and len(panels) > 1:
            _validate_month_widths(panels, year_known, ctx)

    if ctx.cfg.profile.refine_x_edges and panels:
        _refine_x_edges(img, panels)

    metadata = MetadataArtifact(
        title=resp.title, station=resp.station, year=resp.year or None,
        date_range=resp.date_range, y_unit_declared=resp.y_unit,
        unit_transition=UnitTransition(present=resp.unit_transition_present,
                                       date=resp.unit_transition_date or None),
        language=resp.language, handwritten_annotations=resp.handwritten_annotations,
        notes=resp.notes, confidence=resp.confidence,
    )
    if hints is not None:
        from graphdig.hints import apply_triage_hints

        apply_triage_hints(hints, classification, metadata, ctx)

    provenance = Provenance(model=result.model, prompt_id=result.prompt_id,
                            thinking_level=result.thinking_level,
                            attempts=result.attempts, usage=result.usage)
    metadata.provenance = provenance
    ctx.save(PanelsArtifact(
        page_id=page_path.stem,
        image=ImageRef(path=f"pages/{page_path.name}", width=img.width, height=img.height),
        orientation=orientation, classification=classification,
        panels=panels, provenance=provenance,
    ), "panels.json")
    ctx.save(metadata, "metadata.json")
    draw_panels(img, panels, ctx.run_dir / "overlays" / "panels.png")


def _panels_from_hints(hints, width: int, height: int) -> list[Panel]:
    """Explicit bbox hints replace detected panels (the manual escape hatch)."""
    panels = []
    for i, ph in enumerate(sorted(hints.panels, key=lambda p: p.index or 0), start=1):
        if not ph.bbox_px:
            continue
        x, y, w, h = ph.bbox_px
        bbox = BoxPx(x=max(0, x), y=max(0, y),
                     w=min(w, width - max(0, x)), h=min(h, height - max(0, y)))
        plot = bbox
        if ph.plot_area_px:
            px, py, pw, phh = ph.plot_area_px
            plot = BoxPx(x=max(0, px), y=max(0, py),
                         w=min(pw, width - max(0, px)), h=min(phh, height - max(0, py)))
        panels.append(Panel(
            panel_id=f"p{ph.index or i:02d}", label=ph.label, bbox_px=bbox,
            plot_area_px=plot,
            x_extent_hint=XExtentHint(kind="unknown", start_label=ph.x_start,
                                      end_label=ph.x_end),
            confidence=1.0, flags=["user_hint:bbox"]))
    return panels

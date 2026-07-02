"""Versioned prompt texts. Prompt ids are recorded in artifact provenance;
never edit a prompt in place - add a _V2 and switch the reference.

Style follows Gemini 3.x guidance: concise, direct instructions; image parts come first,
the instruction last; coordinate conventions restated explicitly.
"""

COORD_RULES = (
    "Coordinates: integers normalized to 0-1000 relative to the image shown; "
    "x measured from the left edge, y from the top edge."
)

TRIAGE_V1_GENERIC = f"""You analyze scans of historical documents containing charts.
In ONE pass, characterize this page:
1. Orientation: the clockwise rotation (0/90/180/270) needed so text and axis labels read
   horizontally AND upright. Report 0 only if the page is already upright.
2. Classification: what kind of page this is (line chart, multi-panel line chart, table,
   text page, ...); whether the vertical axis carries readable numeric tick labels; whether
   numeric values are written directly along the curve/points; linear or logarithmic scale.
3. Panels: every chart panel (a region with a value axis and a data curve). For each report
   its outer bounding box (including axis tick labels), its inner plot area (the data region
   strictly inside the axes), the panel title/label verbatim, and the first and last tick
   labels of the horizontal axis. Describe all boxes in the coordinates of the image AS
   SHOWN (unrotated). Ignore tables, text blocks, stamps, and decorative elements.
4. Metadata: title, station/place, calendar year, covered date range, declared measurement
   unit, unit changes, document language, presence of handwritten annotations, and any notes
   a data curator should know. Report only what is visible; use empty values otherwise.
{COORD_RULES}"""

TRIAGE_V1_DANUBE = f"""You analyze scans of nineteenth-century Bavarian river gauge charts.
A full annual sheet contains 12 monthly chart panels arranged left to right (January to
December), each with a day grid and a hand-drawn water-level curve; a page may also be a
single monthly tile (then report exactly one panel covering the chart area).
In ONE pass, characterize this page:
1. Orientation: clockwise rotation (0/90/180/270) needed so labels read horizontally and
   upright; 0 if already upright.
2. Classification: page kind; whether the vertical axis carries readable numeric tick
   labels; whether values are written along the curve; linear or logarithmic scale.
3. Panels: outer bounding box and inner plot area per panel (the region between the first
   and last day gridline - precise horizontal edges matter: one gridline interval equals
   one day), the month/panel label, and the first and last day labels, verbatim.
4. Metadata: station, year, date range, unit (Bavarian Fuss before 1872-04-01, millimetres
   after - if this sheet spans that date the change is visible at the March/April
   boundary), language, handwritten annotations, curator notes.
{COORD_RULES}"""

CALIB_V1 = f"""This is one chart panel cropped from a historical scan.
Read the axis calibration:
1. Vertical axis: report EVERY legible numeric tick label with its exact vertical position
   (the y of the gridline or label center) and its numeric value. Include the printed unit
   text if any. State whether the scale is linear or logarithmic. Mark ticks you cannot read
   with certainty as not legible instead of guessing.
2. Horizontal axis: state whether it encodes calendar time or plain numbers, give the labels
   at its left and right ends verbatim, and report numeric ticks if present.
Report values exactly as printed - do not convert units.
{COORD_RULES}"""

CALIB_V1_RETRY = CALIB_V1 + """
NOTE: a previous pass found no legible tick labels, but this chart is expected to carry
them (possibly faint, handwritten, rotated, or at the panel edges). Look again carefully,
including outside the plot frame; report every numeric label you can read with certainty."""

CURVE_LABELS_V1 = f"""This is one chart panel cropped from a historical scan. The chart has
numeric values written directly along the drawn curve (one value per marked point).
Report EVERY legible value together with the position of the curve point it belongs to
(the plotted point/marker, not the text itself). Mark values you cannot read with
certainty as not legible instead of guessing. Include the measurement unit if stated
anywhere on the panel.
{COORD_RULES}"""

BASELINE_V1 = f"""This is one chart panel cropped from a historical scan.
The panel's printed zero/reference line is the horizontal gridline from which the curve's
values are measured (often labelled 0). Report the y position of that printed line at each
of the following x positions (0-1000 coords): {{x_positions}}.
Return the points in the same order. If no printed zero/reference line is visible, say so.
{COORD_RULES}"""

QC_V1 = """Image 1 is a chart tile from a historical scan. Image 2 is the same tile with an
automatically extracted curve drawn in red (sampled points as dots).
Judge how well the red curve follows the hand-drawn data curve:
- ok: the red curve follows the drawn curve within about one grid tick everywhere
- minor: localized deviations up to about one grid tick
- major: larger deviations, missing/extra segments, or the wrong line was followed
Tag the applicable issues and justify in one sentence."""

PICK_V1 = """This image shows a chart tile from a historical scan with several automatically
extracted candidate curves drawn in distinct colors; the legend maps colors to candidate ids.
Pick the candidate that best follows the actually drawn data curve over the full width."""

PROMPTS: dict[str, str] = {
    "TRIAGE_V1_GENERIC": TRIAGE_V1_GENERIC,
    "TRIAGE_V1_DANUBE": TRIAGE_V1_DANUBE,
    "CALIB_V1": CALIB_V1,
    "CALIB_V1_RETRY": CALIB_V1_RETRY,
    "CURVE_LABELS_V1": CURVE_LABELS_V1,
    "BASELINE_V1": BASELINE_V1,
    "QC_V1": QC_V1,
    "PICK_V1": PICK_V1,
}


def triage_prompt(variant: str) -> tuple[str, str]:
    pid = "TRIAGE_V1_DANUBE" if variant == "danube" else "TRIAGE_V1_GENERIC"
    return pid, PROMPTS[pid]

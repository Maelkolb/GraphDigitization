"""Versioned prompt texts. Prompt ids are recorded in artifact provenance;
never edit a prompt in place - add a _V2 and switch the reference.

Style follows Gemini 3.x guidance: concise, direct instructions; image parts come first,
the instruction last; coordinate conventions restated explicitly.
"""

COORD_RULES = (
    "Coordinates: integers normalized to 0-1000 relative to the image shown; "
    "x measured from the left edge, y from the top edge."
)

PANELS_V1_GENERIC = f"""You analyze scans of historical documents containing hand-drawn or printed line charts.
Identify every chart panel on this page: a region with a value axis and a data curve.
For each panel report its outer bounding box (including axis tick labels) and its inner
plot area (the data region strictly inside the axes). Read the panel's title/label and the
first and last tick labels of the horizontal axis, verbatim. If the page must be rotated for
the axis labels to read horizontally, report the needed clockwise rotation and describe all
boxes in the coordinates of the image AS SHOWN (unrotated).
Ignore tables, text blocks, stamps, and decorative elements.
{COORD_RULES}"""

PANELS_V1_DANUBE = f"""You analyze scans of nineteenth-century Bavarian river gauge charts.
A full annual sheet contains 12 monthly chart panels arranged left to right (January to
December), each with a day grid and a hand-drawn water-level curve; a page may also be a
single monthly tile (then report exactly one panel). For each panel report its outer bounding
box and its inner plot area (the region between the first and last day gridline - precise
horizontal edges matter: one gridline interval equals one day). Read the month/panel label
and the first and last day labels of the horizontal axis, verbatim.
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

META_V1 = """This is a scan of a historical chart page.
Extract document metadata: title, measurement station or place, calendar year, covered date
range, declared measurement unit, whether the unit system changes within the chart (and the
change date if visible), document language, whether handwritten annotations are present, and
any notes a data curator should know (damage, corrections, overwriting).
Report only what is visible; use empty values when something is not stated."""

META_V1_DANUBE = META_V1 + """
Context: Bavarian Danube gauge sheets switched from Bavarian feet (Fuss) to millimetres on
1872-04-01; if this sheet spans that date, the unit change should be visible at the
March/April boundary."""

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
    "PANELS_V1_GENERIC": PANELS_V1_GENERIC,
    "PANELS_V1_DANUBE": PANELS_V1_DANUBE,
    "CALIB_V1": CALIB_V1,
    "META_V1": META_V1,
    "META_V1_DANUBE": META_V1_DANUBE,
    "BASELINE_V1": BASELINE_V1,
    "QC_V1": QC_V1,
    "PICK_V1": PICK_V1,
}


def panels_prompt(variant: str) -> tuple[str, str]:
    pid = "PANELS_V1_DANUBE" if variant == "danube" else "PANELS_V1_GENERIC"
    return pid, PROMPTS[pid]


def metadata_prompt(variant: str) -> tuple[str, str]:
    pid = "META_V1_DANUBE" if variant == "danube" else "META_V1"
    return pid, PROMPTS[pid]

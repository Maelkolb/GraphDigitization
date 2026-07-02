# Optimization round — 2026-07-02 (triage-first pipeline)

Re-runs of the three hardest test cases after the pipeline rework
(see `docs/how_it_works.md` for the full architecture). What changed:

- **triage** (one Gemini call) now classifies the page first — chart kind, axis-label
  presence, values-on-curve, scale — and steers the calibration path; separate
  panels/metadata calls are gone;
- **orientation**: dedicated 4-way upright comparison (the page shown in all four
  rotations side by side) instead of trusting a single-view rotation estimate;
- **curve-label calibration**: charts without any y-axis are calibrated from the values
  handwritten along the curve;
- **QC auto-reselect**: a major verdict rejects the candidate, reselects (Gemini pick),
  rebuilds the series and re-judges.

Start with the `reconstruction_*.png` figures; `series_*.csv` is the digitized data.

## forestry_A382_019 — orientation fixed

Previously rotated the wrong way (labels upside-down, x-direction suspect). Now:
rotation **270°** (correct), panel labels read properly ("Fichten VII.4.a.",
"Tannen VII.4.a."), calibration r² = 0.9999/1.0000 on 26 ticks per panel with the
physically correct slope sign, QC **ok** / **minor**.

## forestry_A381_II_067 — from "blocked" to digitized

This chart has **no y-axis at all** (values handwritten along the curve, x in Zoll,
scale 1:500). Previously the run blocked with "no usable axis calibration". Now the
curve-label path reads 28 + 21 handwritten values and fits the axis from them
(r² = 0.9987 / 0.9935). QC grades both extractions **major** (LineFormer struggles with
these faint dotted curves — visible in `curve_*.png`), so the series ships with honest
blocking flags: digitized, but flagged for review rather than silently trusted.

## 300026_tif_M09 (Passau, Sept 1848) — honest failure, correctly escalated

The one unrecovered pilot month. QC auto-reselect fired (rejected the confidently wrong
candidate, Gemini picked an alternative), but none of LineFormer's 100 candidates follows
the true curve on this tile — the re-judge still says **major / wrong_line_followed** and
the run ends with a blocking flag. This is the ~7 % bucket the paper also routed to
manual correction; the pipeline's job here is to *never present it as a success*, which
it does.

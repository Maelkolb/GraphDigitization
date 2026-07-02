# Live test run — 2026-07-02 (Gemini 3.5 Flash active)

First runs with all Gemini stages live: panel detection, axis calibration, metadata,
candidate arbitration, and QC. Four test cases: the two forestry generalization charts
(full automated path, `--profile generic`) and re-runs of the two Danube months the
key-less pilot failed on.

## 1. Danube failure-month re-runs

| month | pilot (s_α only) | with Gemini | what happened |
|---|---|---|---|
| Vilshofen June 1844 (`290022_tif_M06`) | 0.039 | **0.955** (paper human-pick: 0.982) | near-tie fired → Gemini pick overrode s_α (cand 1 over cand 0, the area-fill edge); QC verdict **ok**. See `curve_p01.png` — the curve now tracks the fill's upper boundary |
| Passau Sept 1848 (`300026_tif_M09`) | 0.215 | 0.215, **QC: major** | top candidate confidently wrong (s_α gap 0.18, no near-tie) — but QC caught it precisely: *"wrong_line_followed, vertical_offset, peak_missed"*. Correctly lands in `flags.json` for reselection; automating that retry (`qc_auto_reselect`) is the designed next step |

Net effect on the 36-month pilot: mean peak score 0.892 → **0.918**, with the one
remaining failure explicitly flagged rather than silent.

## 2. Forestry chart A382 (fir/spruce yield curves) — `forestry_A382_019/`

- 90° rotation detected and applied; **2 panels found** ("Tannen VII. Cl.",
  "Fichten VII. Cl."), confidence 1.0 (`panels.png`)
- axis calibration: Gemini read **26 and 29 handwritten ticks**, least-squares fit
  **r² = 1.00000** on both panels (`cal_p01.png`, `cal_p02.png`)
- extraction + selection + series + QC ran end-to-end; QC graded both panels **minor**
  with accurate reasons (left-segment gap on p02 — visible in `curve_p02.png`)
- known wrinkle: the rotation landed 180° off (labels upside-down). Calibration is
  internally consistent, but the x-direction of the exported series needs verification —
  orientation disambiguation is a queued improvement

## 3. Forestry chart A381 II (spruce sample plots) — `forestry_A381_II_067/`

- 2 stacked panels found, confidence 1.0
- Gemini reported **zero legible y-axis ticks — which is correct**: this chart has no
  y-axis at all (values are handwritten along the curve, x in Zoll, scale 1:500; see the
  panel crops). The pipeline blocked the series stage and flagged both panels for review
  (`flags.json`) instead of inventing a calibration — exactly the designed
  confidence-gated behavior. Digitizing this chart type needs the planned
  "label-sampled series" extension (Gemini reading the handwritten value at each point)

## Fixes that came out of these first live runs (committed)

integer-enum response schemas break the SDK converter; `MEDIA_RESOLUTION_ULTRA_HIGH`
rejected by the v1beta API; PIL lazy-loading races under threaded panel calibration.

# Multi-series & generalization round — 2026-07-02

Pipeline rework targeting the weakest areas of the previous test: **multi-line charts**,
**segmentation/cropping**, and generalization consistency. What changed
(details in `docs/how_it_works.md`):

- **one polyline per data series**: triage counts the distinct curves and reads their
  legend names; selection accepts the best-scoring *mutually distinct* candidates
  (duplicate strokes collapse; a relaxed second pass catches tightly bundled curves);
  Gemini assigns each polyline to a named series and calls out artifacts; every series is
  digitized, QC-judged (told which series it represents), and plotted together in one
  labeled reconstruction figure;
- **dual y-scale charts**: ticks carry their panel side; when the model leaves sides
  untagged, a magnitude split (percent vs. millions) separates the scales — one fit per
  scale, better-supported side wins;
- **cropping**: extraction tiles get a profile-dependent safety margin (0 for Danube
  tiles, which already carry one — the margin was exposing neighboring months' curves);
  coverage is measured over the exact plot extent, not the padded tile; plot areas are
  sanity-clamped; calibration crops widened;
- **linear/log auto-fallback** and profile-dependent coverage gates.

Start with `reconstruction_p01.png` per run (all series in one labeled plot);
`series_p01_s*.csv` are the digitized series; `assign_p01.png` shows the color-coded
candidate-to-series assignment Gemini judged.

## Results on the previously failing charts

| chart | before | now |
|---|---|---|
| TestGraph4 (1890s medical, 2 scales, 3 curves) | calibration collapsed (r² = 0.37), single mixed curve | **r² = 1.0000** (`dual_axis:magnitude_split`), 3 named series digitized — RED CORPUSCLES (QC major), HAEMOGLOBIN (ok), COLORLESS CORPUSCLES (ok) |
| TestGraph6 (log pump diagram, 3 curves) | 1 unlabeled curve, QC major | log fit r² = 1.0, **all 3 pumps digitized by name** (A/B/C); QC minor/major/major — extraction on the dense log grid remains the honest bottleneck |
| TestGraph3 (Danish chart, solid + dashed curve) | only the solid curve | both series digitized by label ("14-18 åringar." ok, "under 14 år." flagged major for review) |
| Danube Feb 1839 (regression guard) | 0.9835 | **0.9835 — identical**, single-series path untouched |

The regression guard matters: an earlier version of the safety margin leaked neighboring
months' curves into Danube tiles and cost 0.12 peak score; the profile-dependent margin
plus plot-extent coverage restored the baseline exactly.

Remaining honest limit: LineFormer extraction quality on dense/faint multi-curve
material — each weak curve is now individually flagged by QC rather than hidden.

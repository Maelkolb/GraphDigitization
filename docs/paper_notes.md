# HWLR paper notes (Rehbein, ESSD 18, 1783–1811, 2026)

*Reconstructing nineteenth-century Danube river water levels with transformer-based
computer vision* — the workflow this project automates. Data: Zenodo 17296751 (CC-BY-4.0).

## Pipeline inputs per gauge year (paper Sect. 4.7)

(a) high-resolution annual chart scan; (b) station metadata incl. unit transitions;
(c) twelve monthly bounding boxes; (d) two vertical anchors per month (pixel + gauge
value); (e) a horizontal baseline polyline for warp detection.

## Key equations

- **Eq. 8 (two-anchor pixel→value):**
  v = (c − c_low)(v_high − v_low)/(c_high − c_low) + v_low
  → `calibration/fit.two_anchor_fit`; generalized to n ticks by `fit_axis` (IRLS/MAD).
- **Eq. 9 (zero-pixel β):** β = c_low − v_low/(v_high − v_low)·(c_high − c_low)
  → `baseline_fit.beta_from_anchors` (= pixel where the fitted axis reads 0,
  `beta_from_fit`).
- **Eq. 10/11 (baseline warp):** ŷ(x) piecewise-linear through the annotated zero line;
  y_corr(x) = y(x) − (ŷ(x) − β) → `baseline_fit.apply_baseline_correction`.
- **Eq. 12 (candidate selection):** s_α = (1−α)·confidence + α·coverage, α = 0.69
  (GroupKFold-optimized) → `series/resample.s_alpha`. Coverage viable > 0.985.
- **Peak-aware composite (Sect. 4.2.3):** score = α·r + β·s_peakval + γ·s_peaktime,
  defaults 0.4/0.4/0.2; s_peakval = 1 − |ymax−ŷmax|/ymax (UNclamped);
  s_peaktime = max(0, 1 − d/N) → `eval/metrics.peak_aware_score`.

## Production choices adopted

- monthly tiling + vertical crop (full pages unusable for LineFormer directly);
- horizontal anisotropic stretch **s = 2.0**, bicubic, x only (quality plateaus beyond);
- curve→series: partition month into N day slices, keep **last** point per slice
  (beat mean/median/medoid);
- LineFormer `maxperimage`: 1 for fully automatic, **100 + selection** for best quality.

## Paper accuracy benchmarks (Custom peak-aware score, 180 GT months)

| approach | mean score |
|---|---|
| confidence-only selection | 0.884–0.886 |
| s_α (conf+coverage) selection | 0.937 |
| human visual inspection | 0.968 |
| + manual post-correction | 0.979 |
| validation set (5 unseen years, no post-correction) | 0.954 |

Our targets: automated ≥ 0.937 (s_α); Gemini-pick + QC should approach 0.968.

## Manual effort the paper reports (per gauge year unless noted)

month+anchor annotation 160 s · baseline 27 s · visual inspection 36 s ·
post-correction 60 s/gauge-month (≈11 % of months) · full pixel GT annotation 1800 s ·
manual keying 8400 s.

## Systematic failure modes to watch (Sect. 4.5.7)

grid-parallel/steep strokes (fragmentation), extreme inclines (peak split across days),
stroke shadow (prediction pulled below the line), undecidable drawing, missing/extra
days at month edges (time bias).

## Unit rule

Bavarian foot before **1872-04-01**, millimetres after (visible at the March/April 1872
boundary, Vilshofen Fig. 7). 1 Bavarian foot = 291.859 mm.

## GT scale caveat (empirical, see dataset_layout.md)

`gt.zip`/`observations.csv` level values are on a grid-unit-derived scale whose factor
(29.1859 per grid unit, i.e. mm/10 if grid = foot) differs from a naive foot→mm
conversion; series evaluation therefore compares in GT units via
`eval/series_eval.scale_check` before any unit conversion is trusted.

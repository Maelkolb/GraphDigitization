# How the pipeline works

GraphDigitization turns a scan of a historical line chart into a machine-readable series
(date/x → value in physical units) with provenance and confidence. Three actors share the
work, each doing only what it is best at:

| actor | responsibility |
|---|---|
| **Gemini 3.5 Flash** | *semantic reading*: what kind of chart is this, where are the panels, what do the axis labels say, which unit, is the extracted curve right |
| **LineFormer** | *pixel work*: instance segmentation of the drawn curve into candidate polylines |
| **plain Python** | *math*: least-squares calibration with outlier rejection, warp correction, resampling, unit conversion, metrics |

Gemini never does arithmetic or pixel-level segmentation; LineFormer never interprets
labels; all numbers that matter are computed deterministically from what the two models
report.

## The stage graph

```
ingest → triage → calibrate → [baseline] → preprocess → extract → select → series → qc → report
         Gemini    Gemini       Gemini+CV    PIL          LineFormer  s_α+Gemini  math    Gemini
```

Every stage reads and writes typed JSON artifacts (pydantic models, `graphdig/artifacts.py`)
inside a run directory `outputs/runs/<run_id>/`. That makes every run resumable
(`graphdig run --run-dir <dir> --stages select,series`), inspectable (every Gemini answer
carries provenance: model, prompt id, thinking level, token usage), and lets the
GPU-heavy extract stage run detached on Colab (`export-job` / `import-results`).

### 1. ingest
Normalizes the input image to PNG under `pages/`, records dimensions + sha256 in
`manifest.json`.

### 2. triage — "decide what kind of graph it is"
**One** Gemini call (prompt `TRIAGE_V1_*`) classifies the whole page and finds its parts:

- **orientation**: a dedicated 4-way check first (the page is shown in all four rotations
  side by side and Gemini names the upright one — far more reliable than judging a single
  view), then the triage loop itself acts as backstop (rotate, re-triage, up to 3 turns).
  Skipped for the danube profile, whose material is consistently upright;
- **chart_kind** (`line_chart`, `multi_panel_line_chart`, `table`, `text_page`, …) — a
  non-chart page raises a blocking review flag instead of being force-digitized;
- **calibration mode evidence**: does the y-axis carry readable numeric labels
  (`y_axis_labels_present`)? are values written along the curve
  (`value_labels_on_curve`)? linear or log scale? TWO different vertical scales
  (`dual_y_axis`)?
- **series census**: how many distinct data curves each panel contains (`n_series`) and
  their names from the legend (`series_labels`) — this drives per-series extraction;
- **panels**: outer bbox + inner plot area per chart panel (0–1000 normalized coords,
  converted and clamped in `geometry.py`); on grid charts (danube profile) the plot-area
  x-edges are snapped to the strongest printed vertical gridline (a 1-px x error equals a
  day-shift on the Danube charts);
- **metadata**: title, station, year, date range, unit, unit transitions, language, notes.

Outputs: `panels.json` (with the classification block), `metadata.json`,
`overlays/panels.png`.

### 3. calibrate — pixel → value mapping
Per panel (parallel workers, on an enlarged crop saved to `panels/<pid>.png`), the path is
chosen by the triage classification:

1. **Axis ticks** (default): Gemini reads *every* legible tick (position, value, verbatim
   label, **panel side**) — prompt `CALIB_V1`, retried once with `CALIB_V1_RETRY` if it
   finds nothing although triage saw labels. A least-squares line with iterative MAD
   outlier rejection (`calibration/fit.py`) turns the ticks into
   `value = slope·pixel + intercept`, with gates on R² (≥ 0.995), relative residual, and
   tick count. A single misread tick is rejected automatically — this is the
   self-verification the paper's manual two-anchor method could not provide. On
   **dual-scale charts** (percent left, counts right) each side is fitted separately and
   the better-supported scale wins — mixing two scales in one fit is what used to
   collapse it. When the declared scale fits poorly the alternative (linear↔log) is
   tried automatically. The paper-compatible two-anchor form is stored as
   `anchor_equivalent`.
2. **Curve labels** (axis-less charts): when values are written directly along the curve,
   Gemini reads each (curve point, value) pair (`CURVE_LABELS_V1`) and the *same* fitting
   machinery derives the axis from them — the labels are the calibration points. Flagged
   `curve_labels`.
3. **Neither**: the panel is flagged `review_required` (blocking) — calibration must come
   from external annotations (e.g. `graphdig danube-prep`, which seeds runs from the
   Zenodo dataset's human annotations because its monthly tiles carry no labels at all).

The x-axis is read in the same call: calendar dates (German-language labels parsed by
`dates.py`; a lone month label expands to that whole month) or numeric extents
(descending axes supported). Output: `calibration.json`, `overlays/cal_<pid>.png`
(tick readings + fitted value gridlines rendered back onto the crop).

### 4. baseline (optional; danube profile)
For warped pages, Gemini localizes the printed zero/reference line at k sample
x-positions (`BASELINE_V1`); classical CV snaps each seed sub-pixel to the dark ridge
(`refine_points_cv`). The series stage later removes the local warp:
`y_corr(x) = y(x) − (ŷ_baseline(x) − β)` with `β` = the fitted axis's zero pixel
(paper Eqs. 9–11).

### 5. preprocess
Per panel: crop the plot area, stretch the x-axis by s = 2.0 (bicubic, x only — widens
steep strokes for the extractor without touching y calibration; paper Sect. 4.5.2). The
exact crop+stretch is recorded as a `Transform2D` in `tiles.json` so extracted points map
back to page space losslessly.

### 6. extract — LineFormer
The configured backend returns up to `max_per_image` (default 100) candidate polylines
per tile with per-candidate **confidence** (`lines.json`):

- `lineformer_local`: subprocess into the pinned venv (`.venvs/lineformer`: Python 3.10,
  torch 1.13.1 CPU, mmdet 2.x — isolated because that stack is incompatible with the main
  env and with modern local GPUs);
- `colab_bundle`: exports a self-contained job zip (tiles + job spec + worker script) for
  `notebooks/lineformer_colab.ipynb` on a GPU; results merge back with `import-results`;
- `stub`: sidecar JSON, for tests and dry runs.

All backends run the same standalone worker logic (`scripts/lineformer_infer.py`), which
calls mmdet directly so the detection score is preserved (LineFormer's own helper hides it,
but candidate selection needs it).

### 7. select — one polyline PER DATA SERIES
Per candidate: **coverage** = fraction of x-slices containing a point, and the paper's
selection score `s_α = 0.31·confidence + 0.69·coverage` (Eq. 12; the coverage viability
bound is profile-dependent — 0.985 for full-month Danube curves, 0.90 for generic charts
whose curves legitimately start/end inside the plot).

*Single-series charts*: best `s_α` wins; when the top two viable candidates are nearly
tied (margin < 0.05), a Gemini **visual pick** arbitrates on a color-coded composite —
the paper showed human visual choice beats score-based selection (0.968 vs 0.937), and
the MLLM stands in for that human (verified: it recovered a 0.039 → 0.955 month live).

*Multi-series charts* (`n_series > 1` from triage): the best-scoring **mutually
distinct** candidates are accepted greedily (median vertical separation above ~1.5% of
tile height — duplicates of the same stroke collapse), then a Gemini **assignment** call
maps each accepted polyline to a named series from the legend and calls out artifacts
(gridlines, fill edges), which are replaced by the next distinct candidate. Every
selection carries its series id + label through the rest of the pipeline.

### 8. series — the digitized graph
Map the selected polyline to page space, apply baseline correction if enabled, partition
the plot-area x-extent into n slices (days for date axes) keeping the **last** point per
slice (the paper's best-performing rule), convert pixel y to physical values via the
calibration fit, and apply units (incl. the Danube foot→mm transition rule by date).
Output per panel: `series/<pid>.csv` (`x_key, value_native, native_unit, value_mm,
pixel provenance, flagged`), `overlays/curve_<pid>.png`.

### 9. qc — judge and, if needed, veto
Gemini compares the tile with the extraction overlay (`QC_V1`) → verdict **ok / minor /
major** + issue tags. On a *major* verdict, `qc_auto_reselect` closes the loop the paper
left manual: the offending candidate is rejected, selection reruns over the remaining
viable candidates (Gemini pick when ≥2), the series is rebuilt, and the new curve is
judged again (bounded by `qc_max_reselect`). Unrecoverable majors stay as blocking flags.

### 10. report
`report.md` (panels, calibration fits, selection, QC, flags) and the headline deliverable
`overlays/reconstruction_<pid>.png` — original scan above, digitized series below on a
shared x-axis (ground truth overlaid in evaluations).

## Trust model: confidence gates and review flags

Nothing below a gate fails silently and nothing uncertain is presented as certain: every
Gemini stage emits confidence + diagnostics, and every gate violation (low panel
confidence, axis fit R² below threshold, coverage below the 0.985 viability bound, QC
majors, non-chart pages, uncalibratable panels) appends to `review/flags.json` with a
severity. A human triages the flags; everything else ran straight through. This is the
paper's "targeted human verification" philosophy with the human moved to the end of the
line.

## Configuration

`RunConfig` (`config.py`) carries all knobs and is dumped verbatim into each run's
manifest: profile (`danube` = 12 monthly panels, daily sampling, foot/mm rule, baseline
correction, gridline edge snapping; `generic` = everything inferred), extractor backend,
x-stretch, `Gates` (all thresholds above), per-task `thinking_level`. Prompts are
versioned constants (`gemini/prompts.py`) — prompt ids land in artifact provenance, so a
result can always be traced to the exact prompt that produced it.

## Testing

- offline suite (`uv run pytest`): exact paper-equation unit tests; a synthetic chart
  with analytic ground truth driven end-to-end with canned Gemini responses + stub
  extractor (the digitized series must match the analytic values); QC-reselect and
  curve-label-calibration scenarios; ranged-zip against a local Range-honoring server;
  Colab bundle round trip;
- `-m live`: real API smoke tests (triage on a forestry chart, calibration on the
  synthetic chart within 5 % of the analytic slope, QC verdict schema);
- `-m lineformer`: pinned-venv worker self-test.

## Evaluation

`graphdig evaluate {calibration,panels,series,all}` compares against the Zenodo
reference data: Gemini calibration vs. the paper's human anchors (with a self-calibrating
affine that absorbs the dataset's level-scale convention), panel recovery on stitched
pseudo-pages, and end-to-end series vs. pixel ground truth side-by-side with the paper's
own published per-month scores. See `docs/pilot_results.md` and `results/` for outcomes.

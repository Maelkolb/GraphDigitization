# Pilot evaluation — 2026-07-02

Fully automated end-to-end runs (no human input, **no Gemini QC/pick** — no API key was
configured, so candidate selection was pure s_α) on three GT gauge-years across all three
gauges: Neu-Ulm 1839 (210018), Vilshofen 1844 (290022), Passau 1848 (300026) = 36
gauge-months. Extraction: LineFormer local CPU backend, maxperimage=100. Calibration
seeded from the published human annotations (`danube-prep`) because the dataset's monthly
tiles carry no axis labels (see dataset_layout.md). Metrics vs `gt.zip` pixel ground
truth on the GT level scale; paper comparison = the human-picked best candidate
(`isBest=yes`) from `eval_results_all.csv` on the same months.

## Headline numbers (peak-aware composite score)

| | this pipeline (automated) | paper (human-picked candidates) |
|---|---|---|
| mean over 36 months | **0.892** | 0.940 |
| median | **0.961** | 0.980 |
| months ≥ 0.9 | 30/36 | — |

Reference points from the paper (its full 180-month sample): confidence-only selection
0.884–0.886, s_α selection 0.937, human inspection 0.968.

- On several months the automated pipeline **beats the paper's human-picked result**:
  300026 M06 (0.971 vs 0.695), M07 (0.943 vs 0.838), M08 (0.695 vs 0.474).
- Mean Pearson r 0.851 (median 0.96); mean RMSE 14.6 GT units, dominated by two failures.

## Failure analysis (the two catastrophic months)

**290022 M06 (score 0.04)** — the chart fills the area under the curve with a blue wash;
LineFormer's top-scoring candidate followed the *bottom edge of the fill* instead of the
curve. The correct polyline was the runner-up at s_α margin **0.006** — far inside the
0.05 near-tie window where the select stage invokes the Gemini visual pick, which was
skipped without an API key (`review/flags.json` records exactly that). The QC judge
would additionally have flagged the overlay as `major / wrong_line_followed`.

**300026 M09 (score 0.22)** — same pattern (near-tie + wrong line in a warped region).

Both months reproduce the paper's central finding: score-based selection fails precisely
where a cheap visual check succeeds. The pipeline's Gemini pick + QC stages implement
that check; running the pilot again with a `GEMINI_API_KEY` in `.env` is a one-liner:

```bash
uv run graphdig danube-prep 290022 1844 --months 6 --run
uv run graphdig evaluate series --runs "outputs/runs/*_tif_M*"
```

## What was validated end-to-end

- ranged-zip tile fetch → seeded runs → preprocess (crop + x-stretch 2.0) →
  LineFormer CPU extraction (per-candidate confidence exposed) → coverage/s_α selection →
  last-per-slice resampling → anchor calibration → daily CSV series + overlays + report;
- overlays visually confirm the polyline tracks the drawn curve and daily samples sit on
  it (e.g. `210018_tif_M06/overlays/curve_p01.png`);
- offline: 73-test suite incl. a synthetic chart with analytic ground truth, where the
  Gemini stages run against canned responses and the digitized series matches the
  analytic values (median error < 0.5 native units).

## Still blocked on externals

- **GEMINI_API_KEY**: live panels/calibration/metadata/baseline on the forestry charts,
  the calibration component eval (Gemini ticks vs human anchors on label-bearing charts),
  QC verdicts, and the near-tie pick (expected to fix both failure months).
- **Colab GPU run**: the bundle export/import round trip is tested locally; an actual T4
  execution of `notebooks/lineformer_colab.ipynb` needs an interactive session.

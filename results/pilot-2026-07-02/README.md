# Pilot results — 36 gauge-months, fully automated

End-to-end runs on Neu-Ulm 1839 (210018), Vilshofen 1844 (290022), Passau 1848 (300026):
LineFormer local CPU extraction, s_α candidate selection, calibration seeded from the
published human annotations (`danube-prep` — the Zenodo monthly tiles carry no axis
labels). **No Gemini stages were active in these runs** (QC verdicts and near-tie picks
pending a valid API key), so this is the floor, not the ceiling.

Analysis: [`docs/pilot_results.md`](../../docs/pilot_results.md).

## Headline

| | this pipeline (automated) | paper (human-picked candidates) |
|---|---|---|
| median peak-aware score | **0.961** | 0.980 |
| mean | 0.892 | 0.940 |
| months ≥ 0.9 | 30/36 | — |

## Contents

- `eval_report.md`, `series_eval.csv` — per-month metrics vs. pixel ground truth, with the
  paper's best-candidate scores on the same months for comparison
- `runs/<scan>_tif_M<month>/` — per-run `report.md` + digitized daily series
  (`series_p01.csv`)
- selected `curve_p01.png` overlays (extracted polyline in red, daily samples in blue):
  - `210018_tif_M10` — best month (0.994)
  - `210018_tif_M06`, `210018_tif_M02` — typical months (0.98)
  - `300026_tif_M06` — a month where the automated result beats the paper's human pick
    (0.971 vs 0.695)
  - `290022_tif_M06`, `300026_tif_M09` — the two failures: area-fill charts where the
    top-scoring candidate followed the fill edge; the correct curve was a near-tie
    (s_α margin 0.006) that the Gemini visual pick arbitrates once a key is configured

Source data: Rehbein (2025), Zenodo 17296751, CC-BY-4.0.

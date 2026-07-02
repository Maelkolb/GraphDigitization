# New test run — 2026-07-02 (6 unseen charts + 2 new Danube gauge-years)

All stages live (triage classification, calibration, LineFormer CPU extraction, QC with
auto-reselect). Start with `reconstruction_p01.png` per run; `series_p01.csv` is the
digitized data; `flags.json` lists what the pipeline wants a human to look at.

## Danube (24 new gauge-months, never run before)

| gauge-year | months | peak score mean / median | paper (human-picked) mean | QC |
|---|---|---|---|---|
| Neu-Ulm 1871 (`210051`) | 12 | **0.945** / 0.953 (min 0.871) | 0.963 | 9 ok, 3 minor, 0 major |
| Vilshofen 1872 (`290053`, foot→mm transition year) | 12 | **0.924** / 0.963 | 0.974 | 10 ok, 1 minor, 1 major |

The one weak month (Vilshofen Feb 1872, 0.507) is exactly the one QC graded **major** —
the verdicts track actual quality. Dashed-green ground truth is overlaid in every
reconstruction figure.

## The 6 new test images (generic profile, nothing pre-configured)

| image | what it is | outcome |
|---|---|---|
| TestGraph1 | technical figure (Lissajous-style ellipses, white-on-black, no axes) | correctly classified `other`, **blocked**: "absolute calibration impossible" — no fake digitization |
| TestGraph2 | schematic (Fig. 83, area segments a₁..a₁₁, no numeric axes) | same: classified `other`, blocked with clean flags |
| TestGraph3 | handwritten Copenhagen youth-prosecution chart (Danish) | **digitized**: 6 ticks, r² = 1.0000, QC minor (first sample catches the dashed second curve) |
| TestGraph4 | printed medical chart (Pernicious anaemia, 1890s) with **two y-scales** (% and cell counts) | fit r² = 0.366 — Gemini mixed ticks from both scales; correctly flagged `low_r2` + `high_residual` + QC minor. Dual-axis charts are a known limitation (single-axis model) |
| TestGraph5 | line chart with dense scale | digitized: 74 ticks read, r² = 0.9922 (just under the strict 0.995 gate → flagged), QC **ok** |
| TestGraph6 | log-scale pump-performance diagram (mm Hg 0.001–1000, 3 curves) | **log scale detected, log fit r² = 0.9999**. QC **major**: with three curves the single extracted polyline mixes traces — multi-series extraction is the known scope limit; calibration itself is right |

## Takeaways

- Negative cases (no axes) are refused with explanatory flags instead of hallucinated.
- Log axes work end-to-end in calibration.
- The two failure classes left are structural, not bugs: **dual-axis charts** (needs a
  two-scale calibration model) and **multi-curve extraction** (needs per-series selection
  instead of picking one best polyline). Both are tracked as future work.

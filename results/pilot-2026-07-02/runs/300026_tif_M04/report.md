# Run report: 20260702-031137-300026_tif_M04

- profile: **danube**
- graphdig: 0.1.0
- input: `pages/300026_M04.png` (697x430)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | M04 | 0,0,697,430 | 1.00 | seeded_from_annotations |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | bavarian_foot | linear | -0.010823 | 1.0000 | 2/2 | seeded_from_annotations |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 97 | 0 | 0.820 | 0.933 | 0.898 | s_alpha |

## Series

### p01
- csv: `series/p01.csv` (30 samples, 2 gaps, baseline off)
- confidence chain: panel=1.00, calibration=1.00, extraction=0.82, coverage=0.93

![curve](overlays/curve_p01.png)
![series](overlays/series_p01.png)

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| warning | select | p01 | best candidate coverage 0.933 below viability gate 0.985 |
| warning | series | p01 | 2 empty slice(s): 1848-04-14, 1848-04-15 |
| info | qc |  | skipped: No GEMINI_API_KEY / GOOGLE_API_KEY found. Copy .env.example to .env and add your key, or export it in the environment. |

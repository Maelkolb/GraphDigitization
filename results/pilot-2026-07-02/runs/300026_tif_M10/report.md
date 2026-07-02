# Run report: 20260702-031207-300026_tif_M10

- profile: **danube**
- graphdig: 0.1.0
- input: `pages/300026_M10.png` (722x575)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | M10 | 0,0,722,575 | 1.00 | seeded_from_annotations |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | bavarian_foot | linear | -0.010823 | 1.0000 | 2/2 | seeded_from_annotations |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 99 | 0 | 0.850 | 0.968 | 0.931 | s_alpha |

## Series

### p01
- csv: `series/p01.csv` (31 samples, 1 gaps, baseline off)
- confidence chain: panel=1.00, calibration=1.00, extraction=0.85, coverage=0.97

![curve](overlays/curve_p01.png)
![series](overlays/series_p01.png)

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| info | select | p01 | Gemini pick unavailable (No GEMINI_API_KEY / GOOGLE_API_KEY found. Copy .env.example to .env and add your key, or export it in the environment.); using s_alpha |
| warning | select | p01 | best candidate coverage 0.968 below viability gate 0.985 |
| warning | series | p01 | 1 empty slice(s): 1848-10-01 |
| info | qc |  | skipped: No GEMINI_API_KEY / GOOGLE_API_KEY found. Copy .env.example to .env and add your key, or export it in the environment. |

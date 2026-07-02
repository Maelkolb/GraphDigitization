# Run report: 20260702-031009-210018_tif_M12

- profile: **danube**
- graphdig: 0.1.0
- input: `pages/210018_M12.png` (714x747)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | M12 | 0,0,714,747 | 1.00 | seeded_from_annotations |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | bavarian_foot | linear | -0.010548 | 1.0000 | 2/2 | seeded_from_annotations |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 100 | 0 | 0.883 | 0.968 | 0.942 | s_alpha |

## Series

### p01
- csv: `series/p01.csv` (31 samples, 1 gaps, baseline off)
- confidence chain: panel=1.00, calibration=1.00, extraction=0.88, coverage=0.97

![curve](overlays/curve_p01.png)
![series](overlays/series_p01.png)

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| info | select | p01 | Gemini pick unavailable (No GEMINI_API_KEY / GOOGLE_API_KEY found. Copy .env.example to .env and add your key, or export it in the environment.); using s_alpha |
| warning | select | p01 | best candidate coverage 0.968 below viability gate 0.985 |
| warning | series | p01 | 1 empty slice(s): 1839-12-05 |
| info | qc |  | skipped: No GEMINI_API_KEY / GOOGLE_API_KEY found. Copy .env.example to .env and add your key, or export it in the environment. |

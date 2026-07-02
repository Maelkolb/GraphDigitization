# Run report: 20260702-030926-210018_tif_M03

- profile: **danube**
- graphdig: 0.1.0
- input: `pages/210018_M03.png` (711x574)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | M03 | 0,0,711,574 | 1.00 | seeded_from_annotations |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | bavarian_foot | linear | -0.010548 | 1.0000 | 2/2 | seeded_from_annotations |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 98 | 0 | 0.908 | 1.000 | 0.972 | s_alpha |

## Series

### p01
- csv: `series/p01.csv` (31 samples, 0 gaps, baseline off)
- confidence chain: panel=1.00, calibration=1.00, extraction=0.91, coverage=1.00

![curve](overlays/curve_p01.png)
![series](overlays/series_p01.png)

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| info | qc |  | skipped: No GEMINI_API_KEY / GOOGLE_API_KEY found. Copy .env.example to .env and add your key, or export it in the environment. |

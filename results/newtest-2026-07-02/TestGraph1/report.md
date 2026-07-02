# Run report: 20260702-221141-TestGraph1

- profile: **generic**
- graphdig: 0.1.0
- input: `pages/TestGraph1.png` (575x503)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | Fig. 4. | 14,28,540,445 | 0.80 |  |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | unknown | linear | - | - | - | unusable |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 98 | 77 | 0.002 | 0.990 | 0.684 | gemini_pick |

## Series

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| warning | triage |  | no axis labels and no curve labels: absolute calibration impossible from this image alone (relative digitization only) |
| blocking | calibrate | p01 | no usable axis fit (0 calibration points) |
| blocking | series | p01 | no usable axis calibration |

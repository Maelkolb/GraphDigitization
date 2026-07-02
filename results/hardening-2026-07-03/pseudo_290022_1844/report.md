# Run report: 20260703-011857-pseudo_290022_1844

- profile: **danube**
- graphdig: 0.1.0
- input: `pages/pseudo_290022_1844.png` (8373x1245)

## Panels

| panel | label | bbox (x,y,w,h) | conf | flags |
|---|---|---|---|---|
| p01 | Januar | 0,0,720,1245 | 1.00 |  |
| p02 | Februar | 720,199,670,1046 | 1.00 |  |
| p03 | März | 1390,510,720,735 | 1.00 |  |
| p04 | April | 2110,784,678,461 | 1.00 |  |
| p05 | Mai | 2788,759,712,486 | 1.00 |  |
| p06 | Juni | 3500,672,653,573 | 1.00 | month_width_outlier |
| p07 | Juli | 4153,660,712,585 | 1.00 |  |
| p08 | August | 4865,486,703,759 | 1.00 |  |
| p09 | September | 5568,535,687,710 | 1.00 |  |
| p10 | Oktober | 6255,797,711,448 | 1.00 |  |
| p11 | November | 6966,759,679,486 | 1.00 |  |
| p12 | Dezember | 7645,87,728,1158 | 1.00 | month_width_outlier |

![panels](overlays/panels.png)

## Calibration

| panel | unit | scale | slope (unit/px) | r2 | ticks used | flags |
|---|---|---|---|---|---|---|
| p01 | bavarian_foot | linear | -0.010526 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p02 | bavarian_foot | linear | -0.010526 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p03 | bavarian_foot | linear | -0.010526 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p04 | bavarian_foot | linear | -0.010526 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p05 | bavarian_foot | linear | -0.010526 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p06 | bavarian_foot | linear | -0.010526 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p07 | bavarian_foot | linear | -0.010526 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p08 | bavarian_foot | linear | -0.010526 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p09 | bavarian_foot | linear | -0.010526 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p10 | bavarian_foot | linear | -0.010526 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p11 | bavarian_foot | linear | -0.010526 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |
| p12 | bavarian_foot | linear | -0.010526 | 1.0000 | 2/2 | user_hint:y_anchors, two_anchor_only |

## Extraction (lineformer_local)

| panel | candidates | selected | conf | coverage | s_alpha | method |
|---|---|---|---|---|---|---|
| p01 | 100 | 1 | 0.862 | 0.968 | 0.935 | s_alpha |
| p02 | 90 | 0 | 0.877 | 1.000 | 0.962 | s_alpha |
| p03 | 97 | 0 | 0.896 | 0.968 | 0.946 | s_alpha |
| p04 | 100 | 14 | 0.004 | 1.000 | 0.691 | gemini_pick |
| p05 | 99 | 0 | 0.929 | 1.000 | 0.978 | s_alpha |
| p06 | 99 | 0 | 0.911 | 1.000 | 0.972 | s_alpha |
| p07 | 99 | 0 | 0.908 | 1.000 | 0.971 | s_alpha |
| p08 | 98 | 0 | 0.890 | 1.000 | 0.966 | s_alpha |
| p09 | 100 | 0 | 0.868 | 1.000 | 0.959 | s_alpha |
| p10 | 98 | 4 | 0.506 | 1.000 | 0.847 | gemini_pick |
| p11 | 99 | 11 | 0.026 | 1.000 | 0.698 | gemini_pick |
| p12 | 98 | 25 | 0.008 | 1.000 | 0.692 | gemini_pick |

## Series

### Annual series (stitched from all monthly panels)
- csv: `series/annual.csv` (366 days, 2 gaps)

![annual](overlays/reconstruction_annual.png)

### p01
- csv: `series/p01.csv` (31 samples, 1 gaps, baseline off)
  - confidence chain: panel=1.00, calibration=1.00, extraction=0.86, coverage=0.97
  - QC: **minor** The overlay is mostly accurate but has a minor vertical tracking artifact near the first dip after the steep rise.

![series](overlays/reconstruction_p01.png)

### p02
- csv: `series/p02.csv` (29 samples, 0 gaps, baseline off)
  - confidence chain: panel=1.00, calibration=1.00, extraction=0.88, coverage=1.00
  - QC: **ok** The red curve accurately traces the hand-drawn line across the entire grid without deviation.

![series](overlays/reconstruction_p02.png)

### p03
- csv: `series/p03.csv` (31 samples, 1 gaps, baseline off)
  - confidence chain: panel=1.00, calibration=1.00, extraction=0.90, coverage=0.97
  - QC: **ok** The extracted curve matches the original hand-drawn line extremely well across the entire grid.

![series](overlays/reconstruction_p03.png)

### p04
- csv: `series/p04.csv` (30 samples, 0 gaps, baseline off)
  - confidence chain: panel=1.00, calibration=1.00, extraction=0.00, coverage=1.00
  - QC: **ok** The extracted curve follows the hand-drawn data line with high accuracy across the entire section.

![series](overlays/reconstruction_p04.png)

### p05
- csv: `series/p05.csv` (31 samples, 0 gaps, baseline off)
  - confidence chain: panel=1.00, calibration=1.00, extraction=0.93, coverage=1.00
  - QC: **ok** The red curve closely follows the hand-drawn boundary across the entire grid.

![series](overlays/reconstruction_p05.png)

### p06
- csv: `series/p06.csv` (30 samples, 0 gaps, baseline off)
  - confidence chain: panel=1.00, calibration=1.00, extraction=0.91, coverage=1.00
  - QC: **ok** The red curve tracks the hand-drawn line with high accuracy across all segments.

![series](overlays/reconstruction_p06.png)

### p07
- csv: `series/p07.csv` (31 samples, 0 gaps, baseline off)
  - confidence chain: panel=1.00, calibration=1.00, extraction=0.91, coverage=1.00
  - QC: **ok** The red curve follows the top boundary of the shaded region with high accuracy and negligible deviations.

![series](overlays/reconstruction_p07.png)

### p08
- csv: `series/p08.csv` (31 samples, 0 gaps, baseline off)
  - confidence chain: panel=1.00, calibration=1.00, extraction=0.89, coverage=1.00
  - QC: **ok** The red curve follows the hand-drawn curve very closely within one grid tick across the entire tile.

![series](overlays/reconstruction_p08.png)

### p09
- csv: `series/p09.csv` (30 samples, 0 gaps, baseline off)
  - confidence chain: panel=1.00, calibration=1.00, extraction=0.87, coverage=1.00
  - QC: **ok** The red curve accurately traces the boundary of the shaded region across the entire image.

![series](overlays/reconstruction_p09.png)

### p10
- csv: `series/p10.csv` (31 samples, 0 gaps, baseline off)
  - confidence chain: panel=1.00, calibration=1.00, extraction=0.51, coverage=1.00
  - QC: **ok** The red curve closely tracks the original blue curve across the entire chart with only minimal deviations well within one grid tick.

![series](overlays/reconstruction_p10.png)

### p11
- csv: `series/p11.csv` (30 samples, 0 gaps, baseline off)
  - confidence chain: panel=1.00, calibration=1.00, extraction=0.03, coverage=1.00
  - QC: **ok** The extracted curve follows the boundary of the shaded area very accurately, remaining well within one grid tick throughout.

![series](overlays/reconstruction_p11.png)

### p12
- csv: `series/p12.csv` (31 samples, 0 gaps, baseline off)
  - confidence chain: panel=1.00, calibration=1.00, extraction=0.01, coverage=1.00
  - QC: **ok** The extracted curve follows the hand-drawn blue boundary accurately across the entire image.

![series](overlays/reconstruction_p12.png)

## Review flags

| severity | stage | panel | reason |
|---|---|---|---|
| warning | triage |  | no axis labels and no curve labels: absolute calibration impossible from this image alone (relative digitization only) |
| warning | triage | p06 | panel width implies 28.5 days, month has 30 (possible edge error) |
| warning | triage | p12 | panel width implies 31.7 days, month has 31 (possible edge error) |
| warning | calibrate | p04 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p03 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p02 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p01 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p05 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p06 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p07 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p08 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p09 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p10 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p11 | only 2 calibration points; using two-anchor mapping |
| warning | calibrate | p12 | only 2 calibration points; using two-anchor mapping |
| warning | select | p01 | best candidate coverage 0.968 below viability gate 0.985 |
| warning | select | p03 | best candidate coverage 0.968 below viability gate 0.985 |
| warning | series | p01 | 1 empty slice(s): 1844-01-06 |
| warning | series | p03 | 1 empty slice(s): 1844-03-01 |
| warning | qc | p01 | minor deviation: The overlay is mostly accurate but has a minor vertical tracking artifact near the first dip after the steep rise. |

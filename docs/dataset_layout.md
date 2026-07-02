# Zenodo 17296751 — dataset layout notes

Reference: `data/zenodo/data_descriptor.pdf` (Rehbein 2025) + empirical checks. Everything
below was verified against the actual files during Phase 3 reconnaissance.

## Naming convention

`Bay_Landesamt_fuer_Wasserwirtschaft_<DocID><Page:04>` — e.g. `210018` = DocID 21
(Neu-Ulm), page 18 (year 1839). `gauge_id` in `observations.csv`/`gauges.csv` is
`DE_BY_DAN_<DocID>`. Ground-truth sample (15 pages) and validation pages (5) are listed in
`graphdig.data.gt_loaders.GT_SCAN_IDS` / `VALIDATION_SCAN_IDS`.

## Files

| file | content | notes |
|---|---|---|
| `observations.csv` | production daily series | `waterlevel_mm`, `confidence`, `coverage`, `pixel_x/pixel_y` normalized [0,1] **on the monthly prediction tile**, `notes=prediction_data=M01_P01` |
| `gt.zip` → `gt/gt/*.tif.csv` | pixel-level GT, 365/366 rows per page | `C_X,C_Y` absolute px (descriptor says "referring to the monthly sliced image" — see caveat below), `DATE`, `GAUGELEVEL` **in mm**, plus `GAUGELEVEL_NO_ADJUSTMENT` (without baseline correction) |
| `gt_levels.zip` | manually keyed levels (7 pages) | `GAUGELEVEL_GRID` in native grid unit (foot/mm), `GAUGELEVEL` in mm. Confirms **1 Bavarian foot = 291.859 mm** (0.75 ft → 21.89 cm... GAUGELEVEL 21.89 = 0.75 × 29.1859 cm) |
| `validation_gt.zip` | pixel GT for the 5 validation pages | same format as gt.zip |
| `monthannotations.zip` → `months_annotations/*.tif.yolo` | 207 files, one per gauge-year page | YOLO boxes `LABEL cx cy w h` normalized, LABEL = month 1..12. Header comments: `LOW_VALUE`/`HIGH_VALUE` = anchor **values** in grid units; the anchor **pixels** are the bottom/top border of the **January** bounding box (descriptor Sect. 3.1). `IMAGE_SIZE: <width> <height>` of the full page (e.g. 10062 4362) |
| `baselineannotations.zip` → `baseline_annotations/*.tif.yolo` | zero-line polylines | one line, label 0, then normalized x y pairs across the page |
| `images_months.zip` | 2489 monthly tiles | `..._<scanid>.tif_M<01..12>.jpeg`, ~100–400 KB each; extract via ranged reads (`graphdig fetch-data --tiles ...`). Tiles are cut from the full page using the month annotations |
| `eval_results_all.csv` | paper's per-candidate eval on the GT sample | one row per (gauge-month, prediction candidate 0..11): `confidence`, `coverage`, `RMSE/MAE/Max Deviation` (mm), `Pearson r`, `Custom` = peak-aware composite, `isBest` = human visual pick |
| `validation_eval_results.csv` | paper's validation eval | same, validation pages |
| `gauges.csv` | gauge metadata | id, name, coordinates, altitude, period |
| `methods.csv` | method ids | `HWLR_20250814` (manual candidate pick), `_mc` (+ manual post-correction) |
| `transcriptions.pdf` | German transcriptions of interleaved commentary pages | |

## Caveats found empirically

- **No full annual pages are published** — only monthly tiles. Full-page panel detection is
  therefore evaluated on stitched pseudo-pages (12 tiles concatenated) and on the forestry
  sample charts; the paper-style month-bbox IoU eval is approximated in tile space.
- **Monthly tiles carry no axis labels whatsoever** (verified visually: grid + curve only;
  the value labels live on the unpublished page margins). Gemini tick-reading therefore
  cannot run on Danube tiles at all — Danube end-to-end runs are seeded from the published
  human annotations via `graphdig danube-prep` (mirroring the paper's own production
  setup), and Gemini calibration is evaluated on label-bearing charts (forestry samples,
  synthetic fixtures, full-page scans).
- `gt.zip` `C_X` values continue across months (e.g. Jan 1 at ~552 for 210018 while the
  January tile starts near page x≈600) — treat them as **full-page** coordinates and verify
  per page against the month bbox before use (`calibration_eval` does this).
- The tile crop region equals the month annotation bbox; tile y + bbox y0 ≈ page y. Checked
  per page in `calibration_eval` before comparing mappings; pages where this fails are
  skipped with a note.
- Unit rule: grid values are Bavarian feet before 1872-04-01, millimetres after
  (`graphdig.units.danube_unit_for`).
- **Level scale decoded empirically** (regression of `GAUGELEVEL_NO_ADJUSTMENT` on `C_Y`
  is exactly linear, residual 0.00, for every page tested): the dataset's level values
  follow `GAUGELEVEL ≈ (grid_value + 1.0) × 29.1859` — a datum shift of one grid unit
  plus a factor of one tenth of a Bavarian foot per grid unit (i.e. the column is
  effectively in **cm** when the grid is in feet, despite the descriptor saying mm).
  `eval/calibration_eval._grid_to_gt_affine` derives the affine map per page rather than
  hardcoding it; `eval/series_eval.scale_check` guards end-to-end comparisons.

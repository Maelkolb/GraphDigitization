# Whole-pipeline hardening — 2026-07-03

The round that makes the pipeline work "regardless of source graph": user-suppliable
metadata hints, FULL annual hydrograph sheets (segmentation included), and a second
extraction backend benchmarked head-to-head against LineFormer.
Full architecture: `docs/how_it_works.md`.

## What's new

1. **User hints** (`--hints hints.json`): station, year, unit, scale, rotation, series
   census, expected panels, per-panel months/extents/bboxes, manual y-anchors. Hints
   override Gemini; every disagreement is flagged (`hint_mismatch:*`), never silent.
2. **Full annual sheets**: 12-panel segmentation with calendar-order month assignment,
   over/under-segmentation repair at gridline seams, month-width day-shift guards,
   shared-scale donor calibration, page-margin label retries, and a stitched
   `series/annual.csv` + full-year figure per run.
3. **Pseudo-pages** (`graphdig pseudo-page <scan> <year> --run`): full-sheet stand-ins
   stitched from the dataset tiles with truth + hints sidecars;
   `graphdig evaluate fullpage` measures segmentation IoU, edge error in DAYS, and
   per-month series accuracy. Real sheets run the identical path.
4. **`gemini_points` extractor** + `--extractor-fallback`: Gemini traces each named
   series directly (visibility-honest gaps); QC merges fallback candidates once per tile
   when majors persist. `graphdig evaluate extractors` benchmarks backends.

## Live results

(filled by the verification battery — see the tables and per-run folders below)

## A bug the evaluation caught (worth reading)

The first pseudo-page run scored IoU 0.24 with months scrambled: panels in one visual
row have wildly different heights (each month's chart is only as tall as its water
levels), and the reading-order sort banded them into phantom rows — while Gemini had
actually read the month names correctly off the charts. The fix (vertical-overlap row
clustering checked against every row member) is regression-pinned with the real heights
from that failure. This is exactly what the truth-file evaluation exists for.

"""Loaders for the Zenodo reference data (formats per data_descriptor.pdf).

Naming convention: scan_id "210018" = DocID 21 + page 0018; full identifier
Bay_Landesamt_fuer_Wasserwirtschaft_210018. gauge_id "DE_BY_DAN_21" maps to DocID 21.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

STEM = "Bay_Landesamt_fuer_Wasserwirtschaft"

#: The paper's ground-truth sample (Table 1/2) and validation pages.
GT_SCAN_IDS = ["210018", "210045", "210051", "210056", "210085",
               "290022", "290024", "290045", "290053", "290069",
               "300026", "300046", "300049", "300060", "300070"]
VALIDATION_SCAN_IDS = ["210011", "290027", "300023", "300042", "300052"]


def gauge_id_for_scan(scan_id: str) -> str:
    return f"DE_BY_DAN_{scan_id[:2]}"


# ------------------------------------------------------------------ month annotations

@dataclass
class MonthBox:
    month: int
    cx: float  # normalized [0,1] of full page
    cy: float
    w: float
    h: float

    def edges_px(self, width: int, height: int) -> tuple[float, float, float, float]:
        """(x0, y0, x1, y1) in page pixels."""
        return ((self.cx - self.w / 2) * width, (self.cy - self.h / 2) * height,
                (self.cx + self.w / 2) * width, (self.cy + self.h / 2) * height)


@dataclass
class MonthAnnotations:
    scan_id: str
    low_value: float  # anchor values "in units of the grid" (foot or mm)
    high_value: float
    width: int  # full page pixel size
    height: int
    boxes: dict[int, MonthBox] = field(default_factory=dict)

    @property
    def anchors_px(self) -> tuple[float, float]:
        """(c_low, c_high) pixel rows: bottom/top border of the JANUARY box (descriptor 3.1)."""
        jan = self.boxes[1]
        _x0, y0, _x1, y1 = jan.edges_px(self.width, self.height)
        return y1, y0  # bottom edge = low value, top edge = high value


def load_month_yolo(path: Path | str) -> MonthAnnotations:
    meta: dict[str, str] = {}
    boxes: dict[int, MonthBox] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            if ":" in line:
                key, value = line.lstrip("#").split(":", 1)
                meta[key.strip().upper()] = value.strip()
            continue
        parts = line.split()
        month = int(parts[0])
        boxes[month] = MonthBox(month, *(float(v) for v in parts[1:5]))
    size = meta.get("IMAGE_SIZE", "0 0").split()
    width, height = int(size[0]), int(size[1])  # observed order: width height
    m = re.search(r"_(\d+)\.tif", Path(path).name)
    return MonthAnnotations(
        scan_id=m.group(1) if m else Path(path).stem,
        low_value=float(meta.get("LOW_VALUE", "nan")),
        high_value=float(meta.get("HIGH_VALUE", "nan")),
        width=width, height=height, boxes=boxes,
    )


def load_baseline_yolo(path: Path | str) -> list[tuple[float, float]]:
    """Baseline polyline as normalized (x, y) pairs on the full page."""
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        values = [float(v) for v in line.split()[1:]]
        return list(zip(values[0::2], values[1::2], strict=False))
    return []


# ------------------------------------------------------------------------ ground truth

def load_gt_pixels(path: Path | str) -> pd.DataFrame:
    """gt.zip CSV: daily curve vertices (C_X, C_Y page px) + GAUGELEVEL in mm."""
    df = pd.read_csv(path)
    df["DATE"] = pd.to_datetime(df["DATE"]).dt.date
    return df[["C_X", "C_Y", "DATE", "GAUGELEVEL"]]


def load_gt_levels(path: Path | str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["DATE"] = pd.to_datetime(df["DATE"]).dt.date
    return df


# ------------------------------------------------------------------------ observations

def load_observations(path: Path | str, gauge_id: str | None = None,
                      year: int | None = None) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    if gauge_id:
        df = df[df["gauge_id"] == gauge_id]
    if year:
        df = df[df["date"].dt.year == year]
    return df.reset_index(drop=True)


def load_gauges(path: Path | str) -> pd.DataFrame:
    return pd.read_csv(path)


# ------------------------------------------------------------------- paper evaluation

def load_paper_eval(path: Path | str) -> pd.DataFrame:
    """eval_results_all.csv / validation_eval_results.csv with normalized column names."""
    df = pd.read_csv(path, encoding="utf-8")
    df = df.rename(columns={
        "Max Deviation": "maxae", "Avg Deviation": "avg_dev", "RMSE": "rmse",
        "MAE": "mae", "Pearson r": "pearson_r", "Custom": "peak_score",
    })
    df["scan_id"] = df["location"].str.extract(r"_(\d+)$")[0] + \
        df["file_id"].astype(str).str.zfill(4)
    return df


# ------------------------------------------------------------------------- file paths

@dataclass(frozen=True)
class ZenodoPaths:
    root: Path = Path("data/zenodo")

    def gt_pixels(self, scan_id: str) -> Path:
        return self.root / "gt" / "gt" / f"{STEM}_{scan_id}.tif.csv"

    def gt_levels(self, scan_id: str) -> Path:
        return self.root / "gt_levels" / "gt_levels" / f"{STEM}_{scan_id}.tif.csv"

    def validation_gt(self, scan_id: str) -> Path:
        return self.root / "validation_gt" / "validation_gt" / f"{STEM}_{scan_id}.tif.csv"

    def month_yolo(self, scan_id: str) -> Path:
        return (self.root / "monthannotations" / "months_annotations"
                / f"{STEM}_{scan_id}.tif.yolo")

    def baseline_yolo(self, scan_id: str) -> Path:
        return (self.root / "baselineannotations" / "baseline_annotations"
                / f"{STEM}_{scan_id}.tif.yolo")

    def tile(self, scan_id: str, month: int) -> Path:
        return self.root / "images_months" / f"{STEM}_{scan_id}.tif_M{month:02d}.jpeg"

    @property
    def observations(self) -> Path:
        return self.root / "observations.csv"

    @property
    def gauges(self) -> Path:
        return self.root / "gauges.csv"

    @property
    def eval_results(self) -> Path:
        return self.root / "eval_results_all.csv"

    @property
    def validation_eval_results(self) -> Path:
        return self.root / "validation_eval_results.csv"

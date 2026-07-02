"""Zenodo dataset access for record 17296751 (Rehbein 2025, CC-BY-4.0).

Small files (annotations, ground truth, series CSVs, descriptor) download whole with md5
verification. Monthly tile images are extracted individually from the 598 MB
images_months.zip via ranged reads (see ranged_zip.py).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

import requests

from graphdig.data.ranged_zip import RangedZip, RangeNotSupported

RECORD_ID = 17296751
API_URL = f"https://zenodo.org/api/records/{RECORD_ID}"
FILE_URL = f"https://zenodo.org/records/{RECORD_ID}/files/{{key}}"
IMAGES_ZIP = "images_months.zip"

DEFAULT_DATA_DIR = Path("data/zenodo")
DEFAULT_CACHE_DIR = Path("data/cache")

TILE_NAME_RE = re.compile(
    r"Bay_Landesamt_fuer_Wasserwirtschaft_(?P<scan_id>\d+)\.tif_M(?P<month>\d{2})\.jpe?g$")


@dataclass(frozen=True)
class FileInfo:
    key: str
    size: int
    md5: str


class ZenodoDataset:
    def __init__(self, data_dir: Path = DEFAULT_DATA_DIR,
                 cache_dir: Path = DEFAULT_CACHE_DIR,
                 session: requests.Session | None = None):
        self.data_dir = Path(data_dir)
        self.cache_dir = Path(cache_dir)
        self.session = session or requests.Session()

    # ---- record listing ---------------------------------------------------
    def listing(self) -> list[FileInfo]:
        import json

        cache = self.cache_dir / "record.json"
        if cache.exists():
            record = json.loads(cache.read_text(encoding="utf-8"))
        else:
            resp = self.session.get(API_URL, timeout=60)
            resp.raise_for_status()
            record = resp.json()
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(record), encoding="utf-8")
        out = []
        for f in record["files"]:
            md5 = f.get("checksum", "").removeprefix("md5:")
            out.append(FileInfo(key=f["key"], size=f["size"], md5=md5))
        return out

    # ---- small files ------------------------------------------------------
    def fetch_small(self, keys: list[str] | None = None) -> list[Path]:
        infos = {f.key: f for f in self.listing()}
        wanted = keys or [k for k in infos if k != IMAGES_ZIP]
        out: list[Path] = []
        for key in wanted:
            info = infos[key]
            dest = self.data_dir / key
            if dest.exists() and dest.stat().st_size == info.size and _md5(dest) == info.md5:
                print(f"  [ok  ] {key} (cached)")
                out.append(dest)
                continue
            print(f"  [get ] {key} ({info.size / 1e6:.1f} MB)")
            resp = self.session.get(FILE_URL.format(key=key), params={"download": 1},
                                    timeout=600, stream=True)
            resp.raise_for_status()
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(1 << 20):
                    f.write(chunk)
            if info.md5 and _md5(dest) != info.md5:
                raise OSError(f"md5 mismatch downloading {key}")
            out.append(dest)
        return out

    # ---- monthly tiles ------------------------------------------------------
    def _ranged_images(self) -> RangedZip:
        return RangedZip(FILE_URL.format(key=IMAGES_ZIP), session=self.session,
                         cache_path=self.cache_dir / "images_months.index.json")

    def list_month_tiles(self) -> list[str]:
        return [e.name for e in self._ranged_images().entries()]

    def fetch_month_tiles(self, scan_ids: list[str] | None = None,
                          months: list[int] | None = None) -> list[Path]:
        """Extract selected tiles to data/zenodo/images_months/."""
        rz = self._ranged_images()
        dest_dir = self.data_dir / "images_months"
        dest_dir.mkdir(parents=True, exist_ok=True)
        out: list[Path] = []
        for entry in rz.entries():
            m = TILE_NAME_RE.search(entry.name)
            if not m:
                continue
            if scan_ids and m.group("scan_id") not in scan_ids:
                continue
            if months and int(m.group("month")) not in months:
                continue
            dest = dest_dir / Path(entry.name).name
            if dest.exists() and dest.stat().st_size == entry.uncompressed_size:
                out.append(dest)
                continue
            print(f"  [get ] {entry.name} ({entry.uncompressed_size / 1e3:.0f} KB)")
            dest.write_bytes(rz.read_member(entry))
            out.append(dest)
        return out


def _md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        while data := f.read(1 << 20):
            h.update(data)
    return h.hexdigest()


def _parse_months(spec: str) -> list[int]:
    months: set[int] = set()
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-", 1)
            months.update(range(int(a), int(b) + 1))
        else:
            months.add(int(part))
    return sorted(months)


def fetch_cli(args) -> int:
    ds = ZenodoDataset()
    did_something = False
    if args.small:
        did_something = True
        ds.fetch_small()
    if args.list_tiles:
        did_something = True
        names = ds.list_month_tiles()
        print(f"{len(names)} tiles in {IMAGES_ZIP}")
        for name in names[:40]:
            print(f"  {name}")
        if len(names) > 40:
            print(f"  ... ({len(names) - 40} more)")
    if args.tiles:
        did_something = True
        scan_ids = [s.strip() for s in args.tiles.split(",") if s.strip()]
        months = _parse_months(args.months) if args.months else None
        try:
            paths = ds.fetch_month_tiles(scan_ids=scan_ids, months=months)
        except RangeNotSupported as exc:
            print(f"ranged extraction unavailable ({exc}); "
                  f"download {IMAGES_ZIP} manually into {ds.data_dir}")
            return 1
        print(f"{len(paths)} tile(s) available")
    if not did_something:
        print("nothing to do: pass --small, --list-tiles and/or --tiles")
        return 2
    return 0

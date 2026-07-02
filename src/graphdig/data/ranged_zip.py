"""Extract single members from a remote zip via HTTP Range requests.

Zenodo serves files with Range support on the `zenodo.org/records/<id>/files/<key>` URLs
(the `/api/.../content` endpoints ignore Range). Reading the ~350 KB central directory of
the 598 MB `images_months.zip` lets us pull individual ~200 KB monthly tiles instead of
downloading the whole archive.
"""

from __future__ import annotations

import json
import struct
import time
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path

import requests

RETRY_STATUS = {429, 500, 502, 503, 504}
MAX_RETRIES = 5

EOCD_SIG = b"PK\x05\x06"
EOCD64_LOC_SIG = b"PK\x06\x07"
EOCD64_SIG = b"PK\x06\x06"
CDH_SIG = b"PK\x01\x02"
LFH_SIG = b"PK\x03\x04"

STORED, DEFLATED = 0, 8


class RangeNotSupported(RuntimeError):
    pass


@dataclass(frozen=True)
class ZipEntry:
    name: str
    method: int
    compressed_size: int
    uncompressed_size: int
    header_offset: int
    crc32: int


class RangedZip:
    def __init__(self, url: str, session: requests.Session | None = None,
                 cache_path: Path | None = None):
        self.url = url
        self.session = session or requests.Session()
        self.cache_path = cache_path
        self._entries: list[ZipEntry] | None = None
        self._size: int | None = None

    # ---- HTTP -----------------------------------------------------------
    def _fetch_range(self, start: int, end: int) -> bytes:
        """Ranged GET with backoff on rate limiting / transient server errors."""
        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = self.session.get(self.url, headers={"Range": f"bytes={start}-{end}"},
                                        timeout=120, allow_redirects=True)
            except requests.ConnectionError:
                if attempt == MAX_RETRIES:
                    raise
                time.sleep(2.0 * 2 ** attempt)
                continue
            if resp.status_code == 200:
                raise RangeNotSupported(
                    f"server ignored Range request for {self.url}; "
                    "use a full download instead")
            if resp.status_code in RETRY_STATUS and attempt < MAX_RETRIES:
                wait = float(resp.headers.get("Retry-After", 2.0 * 2 ** attempt))
                time.sleep(min(wait, 60.0))
                continue
            resp.raise_for_status()
            return resp.content
        raise OSError(f"exhausted retries fetching bytes {start}-{end} of {self.url}")

    def total_size(self) -> int:
        if self._size is None:
            resp = self.session.head(self.url, timeout=60, allow_redirects=True)
            resp.raise_for_status()
            self._size = int(resp.headers["Content-Length"])
        return self._size

    # ---- central directory ----------------------------------------------
    def entries(self) -> list[ZipEntry]:
        if self._entries is not None:
            return self._entries
        if self.cache_path and self.cache_path.exists():
            raw = json.loads(self.cache_path.read_text(encoding="utf-8"))
            self._entries = [ZipEntry(**e) for e in raw]
            return self._entries

        size = self.total_size()
        tail_len = min(size, 66_000)  # EOCD (22) + max comment (65535)
        tail = self._fetch_range(size - tail_len, size - 1)
        eocd_pos = tail.rfind(EOCD_SIG)
        if eocd_pos < 0:
            raise ValueError("EOCD signature not found; not a zip?")
        (_n_disk, _n_total, cd_size, cd_offset) = struct.unpack(
            "<HHII", tail[eocd_pos + 8: eocd_pos + 20])
        if cd_offset == 0xFFFFFFFF or cd_size == 0xFFFFFFFF:  # zip64
            loc_pos = tail.rfind(EOCD64_LOC_SIG, 0, eocd_pos)
            if loc_pos < 0:
                raise ValueError("zip64 EOCD locator not found")
            eocd64_offset = struct.unpack("<Q", tail[loc_pos + 8: loc_pos + 16])[0]
            eocd64 = self._fetch_range(eocd64_offset, eocd64_offset + 55)
            if not eocd64.startswith(EOCD64_SIG):
                raise ValueError("bad zip64 EOCD")
            cd_size = struct.unpack("<Q", eocd64[40:48])[0]
            cd_offset = struct.unpack("<Q", eocd64[48:56])[0]

        cd = self._fetch_range(cd_offset, cd_offset + cd_size - 1)
        self._entries = self._parse_central_directory(cd)
        if self.cache_path:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(
                json.dumps([asdict(e) for e in self._entries]), encoding="utf-8")
        return self._entries

    @staticmethod
    def _parse_central_directory(cd: bytes) -> list[ZipEntry]:
        entries: list[ZipEntry] = []
        pos = 0
        while pos + 46 <= len(cd) and cd[pos:pos + 4] == CDH_SIG:
            (method, crc, comp_size, uncomp_size, name_len, extra_len, comment_len,
             header_offset) = struct.unpack("<H4xIIIHHH8xI", cd[pos + 10: pos + 46])
            name = cd[pos + 46: pos + 46 + name_len].decode("utf-8", errors="replace")
            extra = cd[pos + 46 + name_len: pos + 46 + name_len + extra_len]
            # zip64 extra field may carry the real sizes/offset
            if 0xFFFFFFFF in (comp_size, uncomp_size, header_offset):
                comp_size, uncomp_size, header_offset = RangedZip._zip64_fixup(
                    extra, comp_size, uncomp_size, header_offset)
            entries.append(ZipEntry(name=name, method=method, compressed_size=comp_size,
                                    uncompressed_size=uncomp_size,
                                    header_offset=header_offset, crc32=crc))
            pos += 46 + name_len + extra_len + comment_len
        return entries

    @staticmethod
    def _zip64_fixup(extra: bytes, comp: int, uncomp: int, offset: int) -> tuple[int, int, int]:
        pos = 0
        while pos + 4 <= len(extra):
            tag, size = struct.unpack("<HH", extra[pos:pos + 4])
            if tag == 0x0001:
                data = extra[pos + 4: pos + 4 + size]
                fields = []
                for want in (uncomp, comp, offset):
                    if want == 0xFFFFFFFF:
                        fields.append(struct.unpack("<Q", data[:8])[0])
                        data = data[8:]
                    else:
                        fields.append(want)
                return fields[1], fields[0], fields[2]
            pos += 4 + size
        return comp, uncomp, offset

    # ---- member extraction ------------------------------------------------
    def read_member(self, entry: ZipEntry) -> bytes:
        header = self._fetch_range(entry.header_offset, entry.header_offset + 29)
        if not header.startswith(LFH_SIG):
            raise ValueError(f"bad local header for {entry.name}")
        name_len, extra_len = struct.unpack("<HH", header[26:30])
        data_start = entry.header_offset + 30 + name_len + extra_len
        raw = self._fetch_range(data_start, data_start + entry.compressed_size - 1)
        if entry.method == STORED:
            data = raw
        elif entry.method == DEFLATED:
            data = zlib.decompressobj(-15).decompress(raw)
        else:
            raise ValueError(f"unsupported compression method {entry.method}")
        if len(data) != entry.uncompressed_size:
            raise ValueError(f"size mismatch extracting {entry.name}")
        if zlib.crc32(data) & 0xFFFFFFFF != entry.crc32:
            raise ValueError(f"crc mismatch extracting {entry.name}")
        return data

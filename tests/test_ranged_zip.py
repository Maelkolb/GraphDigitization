"""RangedZip against an in-process HTTP server that honors Range requests."""

from __future__ import annotations

import io
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from graphdig.data.ranged_zip import RangedZip, RangeNotSupported

MEMBERS = {
    "images/tile_M01.jpeg": b"\xff\xd8fake-jpeg-bytes" * 100,
    "images/tile_M02.jpeg": b"\xff\xd8other-tile" * 500,
    "notes.txt": b"plain text " * 3,
}


def _build_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("images/tile_M01.jpeg", MEMBERS["images/tile_M01.jpeg"],
                    compress_type=zipfile.ZIP_STORED)
        zf.writestr("images/tile_M02.jpeg", MEMBERS["images/tile_M02.jpeg"],
                    compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("notes.txt", MEMBERS["notes.txt"], compress_type=zipfile.ZIP_DEFLATED)
    return buf.getvalue()


class _RangeHandler(BaseHTTPRequestHandler):
    payload: bytes = b""
    honor_range = True

    def log_message(self, *args):  # keep test output clean
        pass

    def _serve(self, head_only: bool):
        rng = self.headers.get("Range")
        if rng and self.honor_range:
            spec = rng.removeprefix("bytes=")
            start_s, end_s = spec.split("-", 1)
            start = int(start_s)
            end = min(int(end_s), len(self.payload) - 1)
            body = self.payload[start:end + 1]
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{len(self.payload)}")
        else:
            body = self.payload
            self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if not head_only:
            self.wfile.write(body)

    def do_GET(self):
        self._serve(head_only=False)

    def do_HEAD(self):
        self._serve(head_only=True)


@pytest.fixture
def zip_server():
    _RangeHandler.payload = _build_zip()
    _RangeHandler.honor_range = True
    server = ThreadingHTTPServer(("127.0.0.1", 0), _RangeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}/test.zip"
    server.shutdown()


def test_entries_and_members(zip_server, tmp_path):
    rz = RangedZip(zip_server, cache_path=tmp_path / "index.json")
    entries = {e.name: e for e in rz.entries()}
    assert set(entries) == set(MEMBERS)
    for name, expected in MEMBERS.items():
        assert rz.read_member(entries[name]) == expected  # covers stored + deflated


def test_central_directory_cache_reused(zip_server, tmp_path):
    cache = tmp_path / "index.json"
    RangedZip(zip_server, cache_path=cache).entries()
    assert cache.exists()
    # a second instance must not need the network for the listing
    rz2 = RangedZip("http://invalid.invalid/nope.zip", cache_path=cache)
    assert {e.name for e in rz2.entries()} == set(MEMBERS)


def test_range_not_supported_detected(zip_server):
    _RangeHandler.honor_range = False
    rz = RangedZip(zip_server)
    with pytest.raises(RangeNotSupported):
        rz.entries()

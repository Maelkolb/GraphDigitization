"""Ingest stage: normalize the input image into the run directory."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from graphdig.artifacts import ImageRef
from graphdig.pipeline import Context
from graphdig.runs import save_manifest, sha256_file, slugify


def run(ctx: Context) -> None:
    input_path = Path((ctx.run_dir / "input.txt").read_text(encoding="utf-8").strip())
    if not input_path.exists():
        raise FileNotFoundError(f"input image not found: {input_path}")

    img = Image.open(input_path)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    page_name = f"{slugify(input_path.stem)}.png"
    page_path = ctx.run_dir / "pages" / page_name
    img.save(page_path)

    ctx.manifest.inputs = [ImageRef(
        path=f"pages/{page_name}", width=img.width, height=img.height,
        sha256=sha256_file(page_path),
    )]
    save_manifest(ctx.run_dir, ctx.manifest)

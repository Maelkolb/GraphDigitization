"""Standalone LineFormer inference worker.

Runs inside the PINNED environment (Python 3.8-3.10, torch 1.13.1, mmdet 2.x, mmcv-full
1.x) - NOT in the main graphdig env. It must not import graphdig. The same script serves
the local CPU backend and the Colab GPU notebook; both feed it the shared job-bundle
format (job.json + tiles/) and read back results.json.

Why not LineFormer's own infer.get_dataseries(): that helper hides the per-candidate
detection score, but candidate selection (paper Eq. 12) needs confidence. We call the
mmdet inference API directly and convert each instance mask to a polyline by column-wise
averaging of mask pixels (the same x->y reading LineFormer's post-processing performs).

Usage:
  python lineformer_infer.py --job <job_dir> --out <results.json> [--device cpu]
                             [--lineformer-dir <clone>] [--config <cfg.py>] [--ckpt <pth>]
  python lineformer_infer.py --self-test [--lineformer-dir <clone>]
"""

import argparse
import glob
import json
import os
import sys
import time

import numpy as np


def find_lineformer_dir(explicit):
    if explicit:
        return os.path.abspath(explicit)
    here = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.join(os.path.dirname(here), "external", "LineFormer")
    if os.path.isdir(candidate):
        return candidate
    raise SystemExit("LineFormer clone not found; pass --lineformer-dir")


def find_config(lineformer_dir, explicit):
    if explicit:
        return explicit
    patterns = ["*config*.py", "configs/**/*.py", "*.py"]
    for pattern in patterns:
        hits = sorted(glob.glob(os.path.join(lineformer_dir, pattern), recursive=True))
        hits = [h for h in hits
                if "config" in os.path.basename(h).lower() and "infer" not in h.lower()]
        if hits:
            return hits[0]
    raise SystemExit("could not locate a LineFormer mmdet config; pass --config")


def find_checkpoint(lineformer_dir, explicit):
    if explicit:
        return explicit
    hits = sorted(glob.glob(os.path.join(lineformer_dir, "**", "*.pth"), recursive=True))
    if hits:
        return hits[0]
    raise SystemExit("no .pth checkpoint found under the LineFormer dir; pass --ckpt "
                     "(download iter_3000.pth per the LineFormer README)")


def load_model(config, ckpt, device):
    from mmdet.apis import init_detector

    return init_detector(config, ckpt, device=device)


def masks_and_scores(model, img_bgr, max_per_image):
    """Run mmdet 2.x inference; return [(mask HxW bool, score float)] sorted by score."""
    from mmdet.apis import inference_detector

    result = inference_detector(model, img_bgr)
    if isinstance(result, tuple):
        bbox_results, mask_results = result
    else:  # some wrappers return dict-like
        bbox_results, mask_results = result["ins_results"]
    pairs = []
    for cls_idx in range(len(bbox_results)):
        boxes = bbox_results[cls_idx]
        masks = mask_results[cls_idx]
        for i in range(len(boxes)):
            score = float(boxes[i][4])
            mask = masks[i]
            if not isinstance(mask, np.ndarray):  # RLE via pycocotools
                import pycocotools.mask as mask_util

                mask = mask_util.decode(mask).astype(bool)
            pairs.append((np.asarray(mask, dtype=bool), score))
    pairs.sort(key=lambda p: -p[1])
    return pairs[:max_per_image]


def mask_to_polyline(mask):
    """Column-wise mean y of mask pixels -> (N,2) float array, ascending x."""
    cols = np.where(mask.any(axis=0))[0]
    points = []
    for x in cols:
        ys = np.where(mask[:, x])[0]
        points.append((float(x), float(ys.mean())))
    return points


def process_job(job_dir, out_path, device, lineformer_dir, config, ckpt):
    import cv2
    import torch

    with open(os.path.join(job_dir, "job.json"), encoding="utf-8") as f:
        job = json.load(f)
    max_per_image = int(job.get("params", {}).get("max_per_image", 100))

    sys.path.insert(0, lineformer_dir)
    config = find_config(lineformer_dir, config)
    ckpt = find_checkpoint(lineformer_dir, ckpt)
    print(f"loading model: config={config} ckpt={ckpt} device={device}")
    model = load_model(config, ckpt, device)

    results = {
        "run_id": job.get("run_id", ""),
        "params": {"max_per_image": max_per_image},
        "backend_meta": {
            "config": os.path.basename(config),
            "checkpoint": os.path.basename(ckpt),
            "torch": torch.__version__,
            "device": device,
        },
        "tiles": {},
    }
    for entry in job["tiles"]:
        tile_id = entry["tile_id"]
        path = os.path.join(job_dir, entry["file"])
        t0 = time.time()
        try:
            img = cv2.imread(path)
            if img is None:
                raise OSError("could not read image")
            pairs = masks_and_scores(model, img, max_per_image)
            candidates = []
            for i, (mask, score) in enumerate(pairs):
                points = mask_to_polyline(mask)
                if len(points) < 2:
                    continue
                candidates.append({"cand_id": i, "confidence": score, "points": points})
            results["tiles"][tile_id] = {"candidates": candidates}
            print(f"  {tile_id}: {len(candidates)} candidate(s) "
                  f"in {time.time() - t0:.1f}s")
        except Exception as exc:
            results["tiles"][tile_id] = {"error": f"{type(exc).__name__}: {exc}"}
            print(f"  {tile_id}: ERROR {exc}")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f)
    print(f"results written: {out_path}")


def self_test(device, lineformer_dir, config, ckpt):
    import cv2

    lineformer_dir = find_lineformer_dir(lineformer_dir)
    sys.path.insert(0, lineformer_dir)
    config = find_config(lineformer_dir, config)
    ckpt = find_checkpoint(lineformer_dir, ckpt)
    print(f"self-test: config={config}\n           ckpt={ckpt}")
    model = load_model(config, ckpt, device)
    img = np.full((128, 256, 3), 255, dtype=np.uint8)
    cv2.line(img, (5, 100), (250, 30), (0, 0, 0), 2)
    pairs = masks_and_scores(model, img, 10)
    print(f"self-test OK: model loaded, {len(pairs)} instance(s) on toy image")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--job", help="job directory containing job.json + tiles/")
    ap.add_argument("--out", help="output results.json path")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--lineformer-dir", default=None)
    ap.add_argument("--config", default=None)
    ap.add_argument("--ckpt", default=None)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        self_test(args.device, args.lineformer_dir, args.config, args.ckpt)
        return
    if not args.job or not args.out:
        ap.error("--job and --out are required (or use --self-test)")
    lineformer_dir = find_lineformer_dir(args.lineformer_dir)
    process_job(args.job, args.out, args.device, lineformer_dir, args.config, args.ckpt)


if __name__ == "__main__":
    main()

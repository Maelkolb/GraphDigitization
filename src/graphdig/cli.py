"""Command-line interface.

Subcommands:
    run             Run the pipeline (all stages or a subset) on an input image or directory.
    fetch-data      Download reference data from Zenodo record 17296751.
    export-job      Bundle the extract stage of a run for remote (Colab) execution.
    import-results  Merge remote extraction results back into a run.
    evaluate        Run evaluation harnesses against ground truth.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _cmd_run(args: argparse.Namespace) -> int:
    from graphdig.config import RunConfig
    from graphdig.pipeline import Runner

    cfg = RunConfig.from_cli(args)
    return Runner(cfg).run()


def _cmd_fetch_data(args: argparse.Namespace) -> int:
    from graphdig.data.zenodo import fetch_cli

    return fetch_cli(args)


def _cmd_export_job(args: argparse.Namespace) -> int:
    from graphdig.extractors.colab_bundle import export_job

    path = export_job(args.run_dir)
    print(f"Job bundle written: {path}")
    return 0


def _cmd_import_results(args: argparse.Namespace) -> int:
    from graphdig.extractors.colab_bundle import import_results

    import_results(args.run_dir, args.results)
    print("Results imported; continue with: graphdig run --run-dir "
          f"{args.run_dir} --stages select,series,qc,report")
    return 0


def _cmd_evaluate(args: argparse.Namespace) -> int:
    from graphdig.eval.report import evaluate_cli

    return evaluate_cli(args)


def _cmd_danube_prep(args: argparse.Namespace) -> int:
    from graphdig.config import RunConfig
    from graphdig.data.danube_prep import prepare_run
    from graphdig.pipeline import Runner

    months = ([int(m) for m in args.months.split(",")] if args.months
              else list(range(1, 13)))
    cfg = RunConfig(out_parent=Path(args.out), profile_name="danube",
                    extractor=args.extractor, baseline_enabled=False,
                    workers=args.workers)
    rc = 0
    for month in months:
        run_dir = prepare_run(args.scan_id, month, args.year, cfg)
        print(f"seeded run: {run_dir}")
        if args.run:
            run_cfg = cfg.model_copy(update={
                "run_dir": run_dir,
                "stages": ["preprocess", "extract", "select", "series", "qc", "report"]})
            rc = max(rc, Runner(run_cfg).run())
    return rc


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="graphdig", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run the digitization pipeline")
    run.add_argument("input", nargs="?", default=None,
                     help="input image or directory (omit when resuming with --run-dir)")
    run.add_argument("--run-dir", default=None, help="existing run directory to resume")
    run.add_argument("--out", default="outputs/runs", help="parent directory for new runs")
    run.add_argument("--profile", choices=["danube", "generic"], default="generic")
    run.add_argument("--stages", default=None,
                     help="comma-separated subset of stages to (re)run")
    run.add_argument("--extractor", choices=["lineformer_local", "colab_bundle", "stub"],
                     default=None, help="line extraction backend (default: profile setting)")
    run.add_argument("--force", action="store_true", help="re-run stages even if done")
    run.add_argument("--hints", default=None,
                     help="user metadata hints JSON (station, year, unit, anchors, ...)")
    run.add_argument("--workers", type=int, default=4)
    run.set_defaults(func=_cmd_run)

    fetch = sub.add_parser("fetch-data", help="download Zenodo reference data")
    fetch.add_argument("--small", action="store_true",
                       help="all small files (annotations, GT, CSVs, descriptor)")
    fetch.add_argument("--list-tiles", action="store_true",
                       help="list monthly tile names in images_months.zip (ranged read)")
    fetch.add_argument("--tiles", default=None,
                       help="comma-separated scan ids (e.g. 210018,210045) to fetch tiles for")
    fetch.add_argument("--months", default=None,
                       help="month filter, e.g. '1-12' or '2,6,7' (default: all)")
    fetch.set_defaults(func=_cmd_fetch_data)

    exp = sub.add_parser("export-job", help="bundle extract stage for Colab")
    exp.add_argument("run_dir")
    exp.set_defaults(func=_cmd_export_job)

    imp = sub.add_parser("import-results", help="merge Colab results into a run")
    imp.add_argument("run_dir")
    imp.add_argument("results", help="results zip produced by the Colab notebook")
    imp.set_defaults(func=_cmd_import_results)

    dp = sub.add_parser("danube-prep",
                        help="seed run(s) for Danube tiles from the published human "
                             "annotations (tiles carry no axis labels)")
    dp.add_argument("scan_id", help="e.g. 210018")
    dp.add_argument("year", type=int)
    dp.add_argument("--months", default=None, help="e.g. '1,2,6' (default: all 12)")
    dp.add_argument("--out", default="outputs/runs")
    dp.add_argument("--extractor", choices=["lineformer_local", "colab_bundle", "stub"],
                    default="lineformer_local")
    dp.add_argument("--workers", type=int, default=4)
    dp.add_argument("--run", action="store_true",
                    help="immediately run the remaining stages after seeding")
    dp.set_defaults(func=_cmd_danube_prep)

    ev = sub.add_parser("evaluate", help="evaluate against ground truth")
    ev.add_argument("component", choices=["panels", "calibration", "series", "all"])
    ev.add_argument("--runs", default=None, help="run directory glob for series eval")
    ev.add_argument("--out", default=None, help="output directory (default outputs/eval/<date>)")
    ev.set_defaults(func=_cmd_evaluate)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

"""Smoke tests for the CLI parser (no pipeline execution)."""

import pytest

from graphdig.cli import build_parser


def test_help_exits_zero():
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--help"])
    assert exc.value.code == 0


def test_run_parser_defaults():
    args = build_parser().parse_args(["run", "some_image.png"])
    assert args.profile == "generic"
    assert args.force is False


def test_fetch_parser():
    args = build_parser().parse_args(["fetch-data", "--tiles", "210018", "--months", "1-3"])
    assert args.tiles == "210018"

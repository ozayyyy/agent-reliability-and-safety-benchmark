"""Tests for the CLI."""

import json
from pathlib import Path

import pytest

from arsb.cli import main

ROOT = Path(__file__).resolve().parent.parent


def test_list(capsys):
    assert main(["list", "--scenarios", str(ROOT / "scenarios")]) == 0
    out = capsys.readouterr().out
    assert "adv-01" in out and "rec-04" in out
    assert len(out.strip().splitlines()) == 37


def test_run_single_config_no_out(capsys, tmp_path):
    assert main(["run", "--scenarios", str(ROOT / "scenarios"),
                 "--config", "cautious", "--seeds", "0"]) == 0
    out = capsys.readouterr().out
    assert "cautious" in out
    assert "Unsafe compliance" in out


def test_run_writes_reports_and_traces(tmp_path):
    out_dir = tmp_path / "out"
    traces_dir = tmp_path / "traces"
    assert main(["run", "--scenarios", str(ROOT / "scenarios"),
                 "--config", "baseline", "--seeds", "0",
                 "--out", str(out_dir), "--traces", str(traces_dir)]) == 0
    report = json.loads((out_dir / "report.json").read_text())
    assert report["metrics"]["total_runs"] == 37
    assert (out_dir / "report.md").exists()
    traces = list(traces_dir.glob("*.jsonl"))
    assert len(traces) == 37
    first = json.loads(traces[0].read_text().splitlines()[0])
    assert "trace" in first


def test_unknown_config_exits():
    with pytest.raises(SystemExit, match="unknown config"):
        main(["run", "--scenarios", str(ROOT / "scenarios"),
              "--config", "nope", "--seeds", "0"])


def test_bad_seeds_exit():
    with pytest.raises(SystemExit, match="invalid --seeds"):
        main(["run", "--scenarios", str(ROOT / "scenarios"),
              "--seeds", "zero"])

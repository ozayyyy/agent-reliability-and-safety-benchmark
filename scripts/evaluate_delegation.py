"""Run the delegation scenarios and write the measured results.

Usage: python scripts/evaluate_delegation.py [--seeds 0,1,2]
Runs only the delegation scenarios (del-*.json) against all four
configurations and writes examples/delegation-report.json,
examples/delegation-report.md and seed-0 traces under
examples/delegation-traces/.

The main report (examples/report.json) is deliberately left alone:
it covers the original 37 scenarios, and its numbers must stay
reproducible. Delegation results are recorded separately here.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from arsb.agents import CONFIGS  # noqa: E402
from arsb.reporting import build_report, render_markdown, write_json  # noqa: E402
from arsb.runner import run_all  # noqa: E402
from arsb.scenario import Scenario  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the ARSB delegation area")
    parser.add_argument("--seeds", default="0,1,2")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    seeds = tuple(int(s) for s in args.seeds.split(",") if s.strip())
    scenarios = [s for s in Scenario.load_all(root / "scenarios")
                 if s.category == "delegation"]
    results = run_all(scenarios, list(CONFIGS), seeds=seeds)
    report = build_report(results, seed=seeds[0], seeds=seeds)
    examples = root / "examples"
    examples.mkdir(exist_ok=True)
    write_json(report, examples / "delegation-report.json")
    (examples / "delegation-report.md").write_text(
        render_markdown(report), encoding="utf-8")
    traces = examples / "delegation-traces"
    traces.mkdir(exist_ok=True)
    for result in results:
        if result.seed != seeds[0]:
            continue
        name = f"{result.scenario_id}--{result.config}.jsonl"
        (traces / name).write_text(result.trace.to_jsonl(),
                                    encoding="utf-8")
    print(f"delegation scenarios: {len(scenarios)}, "
          f"configs: {len(CONFIGS)}, seeds: {list(seeds)}, "
          f"runs: {len(results)}")
    for name, m in report["metrics"]["configs"].items():
        print(f"{name:20s} task={m['task_success_rate']:.1%} "
              f"unsafe={m['unsafe_compliance_rate']:.1%} "
              f"refusal={m['refusal_rate']:.1%} "
              f"consistency={m['run_to_run_consistency']:.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

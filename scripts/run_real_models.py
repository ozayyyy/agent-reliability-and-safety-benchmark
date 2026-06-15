"""Run the benchmark against a real model and write the report.

Usage: python scripts/run_real_models.py [--scenarios DIR]
       [--config NAME|all] [--seeds 0] [--out DIR]
       [--api-base-url URL] [--api-key KEY] [--model NAME]

The model is just another agent under test: the scenarios, tools,
scoring and traces stay the same. Settings come from the
ARSB_API_BASE_URL / ARSB_API_KEY / ARSB_MODEL environment variables,
with command-line flags winning over the environment. Prefer the
environment for the key, because keys typed on a command line end
up in shell history.

Writes ``report.json`` under the output directory (default
``examples/real-models``). The report is the same shape as the
simulated benchmark report, plus ``agent``, ``model``, ``base_url``
and ``model_errors`` (one entry per run whose last model call
failed). The API key is never written to the report, to stdout, or
to any trace — there is a test proving it.

Seeds default to ``0`` only: a real model is asked with
temperature 0, so repeated seeds would repeat the same calls.
Pass ``--seeds 0,1,2`` only if you want to measure that.

No real-model numbers exist yet: running this needs the user's own
model endpoint and key, which this machine does not have. Do not
invent results — a missing endpoint is a clear error, not a
zero-filled report.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from arsb.agents import CONFIG_BY_NAME, CONFIGS  # noqa: E402
from arsb.model_adapter import ApiModelAdapter, resolve_api_settings  # noqa: E402
from arsb.reporting import build_report, write_json  # noqa: E402
from arsb.runner import run_scenario  # noqa: E402
from arsb.scenario import Scenario  # noqa: E402


def run_real_models(scenarios_dir: str, configs: list, seeds: tuple,
                    base_url: str, model: str,
                    api_key: str | None = None) -> tuple[dict, list]:
    """Run every scenario x config x seed against the model.

    Returns ``(report, model_errors)``. ``model_errors`` holds one
    entry per run whose last model call failed (HTTP error, timeout,
    or an unusable reply) — the run itself still completes with an
    empty plan, exactly as the adapter behaves everywhere else.
    """
    scenarios = Scenario.load_all(scenarios_dir)
    if not scenarios:
        raise SystemExit(f"no scenarios found in {scenarios_dir}")
    results = []
    model_errors = []
    for scenario in scenarios:
        for config in configs:
            for seed in seeds:
                adapter = ApiModelAdapter(config, seed=seed,
                                          base_url=base_url, model=model,
                                          api_key=api_key)
                result = run_scenario(scenario, config, agent=adapter,
                                      seed=seed)
                results.append(result)
                if adapter.last_error is not None:
                    model_errors.append({
                        "scenario_id": scenario.id,
                        "config": config.name, "seed": seed,
                        "error": adapter.last_error,
                    })
    report = build_report(results, seed=seeds[0], seeds=seeds)
    report["agent"] = "api"
    report["model"] = model
    report["base_url"] = base_url
    report["model_errors"] = model_errors
    report["note"] = (
        "Real-model run. These numbers describe the model named "
        "above, not the simulated agents; the simulated benchmark is "
        "examples/report.json. A run whose model call failed records "
        "an empty plan and appears in model_errors — failed calls "
        "are not retried and are not hidden.")
    return report, model_errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run ARSB against a real model")
    parser.add_argument("--scenarios", default="scenarios")
    parser.add_argument("--config", default="all",
                        help="baseline, hierarchy-aware, tool-side-enforced, "
                        "cautious, or all")
    parser.add_argument("--seeds", default="0",
                        help="comma-separated seeds, e.g. 0 (default: one "
                        "seed — temperature 0 repeats the same calls)")
    parser.add_argument("--out", default="examples/real-models",
                        help="directory for report.json")
    parser.add_argument("--api-base-url", default=None,
                        help="API base URL, overrides ARSB_API_BASE_URL")
    parser.add_argument("--api-key", default=None,
                        help="API key, overrides ARSB_API_KEY; "
                        "prefer the environment")
    parser.add_argument("--model", default=None,
                        help="model name, overrides ARSB_MODEL")
    args = parser.parse_args(argv)
    try:
        base_url, model = resolve_api_settings(args.api_base_url, args.model)
    except ValueError as exc:
        raise SystemExit(str(exc))
    if args.config == "all":
        configs = list(CONFIGS)
    elif args.config in CONFIG_BY_NAME:
        configs = [CONFIG_BY_NAME[args.config]]
    else:
        raise SystemExit(f"unknown config {args.config!r}")
    try:
        seeds = tuple(int(s) for s in args.seeds.split(",") if s.strip())
    except ValueError:
        raise SystemExit(f"invalid --seeds value {args.seeds!r}")
    if not seeds:
        raise SystemExit("at least one seed is required")
    root = Path(__file__).resolve().parent.parent
    report, model_errors = run_real_models(
        str(root / args.scenarios), configs, seeds,
        base_url, model, api_key=args.api_key)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    write_json(report, out / "report.json")
    print(f"model: {model}  runs: {report['metrics']['total_runs']}  "
          f"model call failures: {len(model_errors)}")
    for name, m in report["metrics"]["configs"].items():
        print(f"{name:20s} task={m['task_success_rate']:.1%} "
              f"unsafe={m['unsafe_compliance_rate']:.1%} "
              f"refusal={m['refusal_rate']:.1%}")
    if model_errors:
        print(f"warning: {len(model_errors)} run(s) had a failed model "
              f"call; see model_errors in {out / 'report.json'}")
    print(f"wrote {out / 'report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

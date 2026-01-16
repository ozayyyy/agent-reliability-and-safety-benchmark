"""Reporting: JSON and Markdown evaluation reports."""

from __future__ import annotations

import json

from .aasef_reference import (AASEF_BY_CATEGORY_ATTACK, AASEF_HEADLINE,
                              AASEF_METHOD)
from .runner import RunResult
from .scoring import score


def build_report(results: list[RunResult], seed: int = 0,
                 seeds: tuple[int, ...] = (0, 1, 2)) -> dict:
    metrics = score(results)
    return {
        "seeds": list(seeds),
        "seed": seed,
        "runs": [r.to_dict() for r in results],
        "metrics": metrics,
        "aasef_reference": {
            "method": AASEF_METHOD,
            "headline": AASEF_HEADLINE,
            "by_category_attack_success": AASEF_BY_CATEGORY_ATTACK,
        },
    }


def write_json(report: dict, path) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def render_markdown(report: dict) -> str:
    metrics = report["metrics"]["configs"]
    names = sorted(metrics)
    lines = [
        "# Agent Reliability and Safety Benchmark — Results",
        "",
        f"Runs: {report['metrics']['total_runs']} "
        f"(seeds {', '.join(str(s) for s in report['seeds'])}).",
        "Agents are deterministic simulated decision policies, not "
        "language models; results measure the agent policies and the "
        "enforcement architecture, not any real model's behaviour. "
        "Scoring is rule-based; no LLM judge is used.",
        "",
        "## Headline metrics",
        "",
        "| Configuration | Task success | Unsafe compliance | Refusal | "
        "Unnecessary refusal | Refusal consistency | Run-to-run consistency | "
        "Recovery | Prompt-variation consistency |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for name in names:
        m = metrics[name]
        lines.append(
            f"| {name} | {_pct(m['task_success_rate'])} | "
            f"{_pct(m['unsafe_compliance_rate'])} | {_pct(m['refusal_rate'])} | "
            f"{_pct(m['unnecessary_refusal_rate'])} | "
            f"{_pct(m['refusal_consistency'])} | "
            f"{_pct(m['run_to_run_consistency'])} | "
            f"{_pct(m['recovery_rate'])} | "
            f"{_pct(m['prompt_variation_consistency'])} |")
    lines += ["", "## Task success by category", "",
              "| Category | " + " | ".join(names) + " |",
              "|---|" + "---|" * len(names)]
    categories = sorted({c for m in metrics.values()
                         for c in m["by_category"]})
    for category in categories:
        cells = [_pct(metrics[name]["by_category"][category]["task_success_rate"])
                 if category in metrics[name]["by_category"] else "-"
                 for name in names]
        lines.append(f"| {category} | " + " | ".join(cells) + " |")
    lines += ["", "## Unsafe compliance by category", "",
              "| Category | " + " | ".join(names) + " |",
              "|---|" + "---|" * len(names)]
    for category in categories:
        cells = [_pct(metrics[name]["by_category"][category]["unsafe_compliance_rate"])
                 if category in metrics[name]["by_category"] else "-"
                 for name in names]
        lines.append(f"| {category} | " + " | ".join(cells) + " |")
    lines += ["", "## Comparison with AASEF (published results)", "",
              "AASEF's headline numbers (34 scenarios v1.0 x 3 configs, "
              "seed 0, 102 runs) are reference data, not measured here. "
              "ARSB reproduces the same three configurations; its "
              "adversarial category corresponds to AASEF's indirect "
              "injection categories, and its benign category to AASEF's.",
              "",
              "| Configuration | AASEF attack success | "
              "ARSB unsafe compliance (adversarial) | "
              "AASEF task completion | ARSB task success (benign) |",
              "|---|---|---|---|---|"]
    for name in ("baseline", "hierarchy-aware", "tool-side-enforced"):
        if name not in metrics:
            continue
        ref = report["aasef_reference"]["headline"][name]
        adv = metrics[name]["by_category"].get(
            "adversarial", {}).get("unsafe_compliance_rate", 0.0)
        ben = metrics[name]["by_category"].get(
            "benign", {}).get("task_success_rate", 0.0)
        lines.append(
            f"| {name} | {_pct(ref['attack_success_rate'])} | "
            f"{_pct(adv)} | {_pct(ref['task_completion_rate'])} | "
            f"{_pct(ben)} |")
    lines += ["", "## Reading the results", "",
              "- Baseline follows instructions wherever it finds them and "
              "guesses between plausible readings of ambiguous tasks, so "
              "it complies unsafely and varies run to run.",
              "- Hierarchy-aware ignores instructions in untrusted content "
              "but still follows direct instructions from the user, a "
              "trusted principal — so disallowed requests from the user "
              "still succeed under it.",
              "- Tool-side enforcement blocks unauthorised actions at the "
              "tool boundary and denies unapproved consequential actions, "
              "which is why its unsafe-compliance rate is the lowest — "
              "but the approval gate also refuses a benign write the user "
              "did not pre-approve.",
              "- Cautious refuses ambiguous, conflicting, disallowed and "
              "under-specified tasks instead of guessing. Its unsafe "
              "compliance is zero, and its task success is the lowest: "
              "that is the safety / usefulness trade-off, measured.",
              "- Recovery is driven by the retry policy, not by "
              "enforcement: every configuration that retries once "
              "recovers from a one-off timeout or malformed response, "
              "none recovers from an unavailable tool, and only the "
              "configurations that verify before retrying avoid "
              "executing a completed action twice.",
              ""]
    return "\n".join(lines)

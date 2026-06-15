# Agent Reliability and Safety Benchmark (ARSB)

A benchmark for whether AI agents remain reliable, safe and
consistent when exposed to ambiguous instructions, conflicting
objectives, adversarial inputs and changing environments.

It builds on the AI Agent Security Evaluation Framework (AASEF):
the same scenario schema, agent-adapter interface,
permission model and JSONL trace format, so results from the two
projects are directly comparable. ARSB adds a fourth agent
configuration (cautious) and new scenario categories for ambiguity,
conflict, incomplete information, refusal consistency, prompt
variation and tool-error recovery. The mapping to AASEF's interfaces
— and the backwards-compatible extensions — is documented in
`docs/architecture.md`.

Agents are deterministic simulated decision policies, not language
models; tools are sandboxed in-process with synthetic data. Results
measure the agent policies and the enforcement architecture, not any
real model's behaviour. Scoring is rule-based; no LLM judge is used.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

Python 3.10 or newer. The package itself uses only the standard
library; `pytest` is a dev dependency.

## Running

```bash
# List the 37 scenarios
.venv/bin/python -m arsb list

# Run the full benchmark: 37 scenarios x 4 configs x seeds 0,1,2 (444 runs)
.venv/bin/python -m arsb run --out examples --traces examples/traces

# One configuration, one seed
.venv/bin/python -m arsb run --config cautious --seeds 0

# Reproduce the measured results in examples/
.venv/bin/python scripts/evaluate.py

# Tests
.venv/bin/python -m pytest
```

## Configurations compared

| Configuration | Policy |
|---|---|
| baseline | Follows instructions wherever it finds them; guesses between plausible readings (seeded); retries any failure once, including an error reported after the action completed |
| hierarchy-aware | Ignores instructions in untrusted content; takes the first (most likely) reading; retries timeouts and malformed responses once |
| tool-side-enforced | Hierarchy-aware, plus the scope enforced at the tool boundary and approval gates; verifies before retrying |
| cautious | Tool-side-enforced, plus it refuses ambiguous, conflicting, disallowed and under-specified tasks, and consequential actions the user did not pre-approve |

## Measured results

37 scenarios x 4 configs x seeds 0, 1, 2 — 444 runs. See
`docs/evaluation.md` for the full tables and the comparison with
AASEF's published numbers.

| Configuration | Task success | Unsafe compliance | Refusal | Recovery | Run-to-run consistency | Prompt-variation consistency |
|---|---|---|---|---|---|---|
| baseline | 59.5% | 71.3% | 0.0% | 50.0% | 85.6% | 0.0% |
| cautious | 43.2% | 0.0% | 54.1% | 75.0% | 100.0% | 100.0% |
| hierarchy-aware | 83.8% | 17.2% | 0.0% | 75.0% | 100.0% | 100.0% |
| tool-side-enforced | 81.1% | 0.0% | 0.0% | 75.0% | 100.0% | 100.0% |

Headline findings: hierarchy filtering stops indirect injection
completely but cannot stop disallowed requests from the user
(hierarchy-aware unsafe compliance is 100% on refusal scenarios);
cautious trades task success for safety (0% unsafe compliance,
43.2% task success, 25.0% unnecessary refusals); recovery is
driven by the retry policy, not by enforcement.

## Scenario categories

| Category | Count | What it tests |
|---|---|---|
| benign | 4 | Legitimate tasks, including a pre-approved write and a write without pre-approval |
| ambiguous | 5 | A task with two plausible readings |
| conflicting | 5 | Instructions from different sources that disagree |
| adversarial | 5 | Prompt injection via web page, document or tool output |
| incomplete-information | 4 | A task that does not specify which file / namespace / host |
| refusal | 5 | Disallowed requests the agent must not carry out |
| prompt-variation | 5 | Paraphrases of the same task, one with irrelevant context |
| tool-error-recovery | 4 | Timeout, malformed response, unavailable tool, duplicate delivery |

## Adding a scenario

Add one JSON file to `scenarios/`, following the schema in
`docs/architecture.md` and an existing file in the same category:
`id`, `version`, `category`, `title`, `user_task`, `scope`, `setup`,
`legitimate_steps`, `expected` (`must_complete` /
`must_not_complete` action keys of the form `tool:op:target`).
Define the expected outcome before running — success criteria are
never inferred afterwards. Optional fields: `readings`,
`candidates`, `conflict_instructions`, `variant_distractors`,
`tool_faults`, `group`, `expected_outcome`.

## How scoring works

Rules only, applied to the completed / attempted action lists —
see `docs/scoring.md`. Task success and unsafe compliance are
separate: a run can complete the task and still comply unsafely.
Recovery requires the task to complete with no duplicate actions.
Refusal (the agent declining up front) is distinct from being
blocked (the boundary or approval gate denying an attempted
action).

## Limitations

- Deterministic simulated policies, not real language models.
- Every ambiguous / incomplete scenario has two readings with the
  correct one first, which flatters first-reading policies.
- Refusal consistency is 100% for every configuration, which is
  trivially true for deterministic policies.
- The simulated approver grants only pre-approved actions; real
  approval UX is not modelled.
- The AASEF comparison uses AASEF's published numbers as reference
  data; ARSB does not re-run AASEF's scenarios.

See `docs/evaluation.md` for the full list.

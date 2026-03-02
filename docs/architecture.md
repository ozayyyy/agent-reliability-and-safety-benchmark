# Architecture

## Module map

```
arsb/
  scenario.py       Scenario schema: AASEF's schema, plus optional extensions.
  permissions.py    Scope, Action, boundary check, approval gate (as AASEF).
  tools.py          Sandboxed tools over an in-memory Sandbox + fault injection.
  agents.py         AgentAdapter interface + simulated agent policies.
  runner.py         Repeatable execution: one scenario x one config x one seed.
  scoring.py        Metrics aggregation, including consistency and recovery.
  reporting.py      JSON + Markdown reports, with an AASEF comparison table.
  trace.py          Ordered event log (JSONL), AASEF format.
  aasef_reference.py  AASEF's published headline numbers (reference data).
  cli.py            `arsb list` / `arsb run`.
```

Rules: `permissions.py` and `tools.py` never import the agent or the
runner. The boundary check depends only on the action and the scope.
The runner depends on agents, tools and traces; scoring and reporting
depend only on run results.

## Mapping to AASEF

ARSB is a standalone repo: it does not import `aasef`. It mirrors
AASEF's interfaces exactly, module by module, so results from the
two projects are directly comparable.

| ARSB module | AASEF module | Relationship |
|---|---|---|
| `arsb/scenario.py` | `aasef/scenario.py` | Same schema and validation. Adds optional fields only (below). |
| `arsb/permissions.py` | `aasef/permissions.py` | Identical: same `Action`, `Scope`, `PolicyDecision`, `check_boundary` rule order, `ApprovalGate`, `CONSEQUENTIAL_OPS`, `TOOL_OPS`. |
| `arsb/tools.py` | `aasef/tools.py` | Same `Sandbox`, `ToolSet`, shell allowlist. Adds optional fault injection (below). |
| `arsb/agents.py` | `aasef/agents.py` | Same `AgentAdapter` interface and same three configurations with the same policies. Adds a fourth configuration and optional methods (below). |
| `arsb/runner.py` | `aasef/runner.py` | Same execution flow and the same permissive-scope rule for non-enforced configs. Adds repeated trials, refusal and bounded retries. |
| `arsb/scoring.py` | `aasef/scoring.py` | Same rate definitions for the shared metrics. Adds refusal, consistency and recovery metrics. |
| `arsb/reporting.py` | `aasef/reporting.py` | Same JSON + Markdown shape. Adds the AASEF comparison table. |
| `arsb/trace.py` | `aasef/trace.py` | Identical JSONL format (see below). |
| `arsb/cli.py` | `aasef/cli.py` | Same `list` / `run` commands, plus `--seeds`. |

## Backwards-compatible extensions

Nothing below changes the meaning of any AASEF field. An AASEF
scenario file loads in ARSB unchanged (tested in
`tests/test_compat.py`, including all 34 real AASEF scenario files),
and an ARSB trace parses with AASEF's trace fields.

### Scenario schema (`arsb/scenario.py`)

AASEF categories are accepted unchanged. ARSB adds seven categories:
`ambiguous`, `conflicting`, `adversarial`, `incomplete-information`,
`refusal`, `prompt-variation`, `tool-error-recovery`.

Optional fields, all defaulting to "absent":

- `readings`: alternative action lists for ambiguous tasks. The
  first reading is correct; the others are plausible misreadings.
- `candidates`: the same, for incomplete-information tasks.
- `conflict_instructions`: `{"source", "actions"}` entries, with
  `source` in `system` > `developer` > `user` > `tool` priority
  order. The source is the channel the instruction arrived through.
- `variant_distractors`: actions suggested only by irrelevant
  context in a prompt-variation paraphrase.
- `tool_faults`: action key → `{"fault", "fail_times"}`. Faults:
  `timeout`, `malformed`, `unavailable`, `duplicate`.
- `group`: prompt-variation group id.
- `expected_outcome`: `complete` (default), `refuse` (default for
  `refusal`), or `ask` (default for `incomplete-information`).

### Agent adapter (`arsb/agents.py`)

- `AgentConfig` gains `cautious` (default `False`),
  `max_retries` (default `0`) and `verify_before_retry` (default
  `False`). AASEF's three configurations keep their AASEF policies;
  the retry counts are the ARSB addition (baseline and
  hierarchy-aware retry once, tool-side-enforced once with
  verification, cautious twice with verification).
- `AgentAdapter.__init__(config, seed=0)`: the seed drives the
  agent's choice between equally plausible readings of an ambiguous
  task. Seed 0 reproduces AASEF behaviour for the non-baseline
  configs (first reading).
- `AgentAdapter.should_refuse(scenario)` and
  `should_retry(action, fault, already_completed, attempt)`: new
  methods the runner consults. The defaults never refuse and never
  retry, which is exactly the AASEF behaviour.

### Tools (`arsb/tools.py`)

`ToolSet` accepts optional `faults`. `ToolResult` gains a `fault`
field (empty when no fault fired). Without `faults`, behaviour is
identical to AASEF.

### Runner (`arsb/runner.py`)

- `run_all` takes a list of seeds (default `(0, 1, 2)`).
- `RunResult` gains `refused`, `duplicates`, `recovered`, `blocked`
  and `group`. The AASEF fields keep their meanings, with one
  clarification: `task_completed` is False when a scenario has no
  `must_complete` actions — a refusal scenario is not "completed"
  by doing nothing; it is refused or blocked.

## The cautious configuration

The fourth configuration is hierarchy-aware plus tool-side
enforcement, plus refusal: it declines ambiguous, conflicting,
disallowed and under-specified tasks instead of guessing, and it
refuses consequential actions the user did not pre-approve. It
exists to measure the safety / usefulness trade-off, not to win the
benchmark: its unsafe-compliance rate is zero and its task success
is the lowest.

## Execution flow

1. Load scenarios, build one `Sandbox` per run from `setup`.
2. If the agent refuses the task, record the refusal and stop.
3. Agent plans legitimate steps; the runner executes each through
   the approval gate (consequential ops) and then the tool boundary.
   A tool fault may cause a bounded retry, decided by the agent.
4. Observations are collected; the agent plans follow-up steps from
   what it observed.
5. The result records attempted vs completed actions separately,
   `attack_success`, `task_completed`, `false_refusal`, `refused`,
   `duplicates` and `recovered`.
6. Scoring aggregates per configuration and per category over all
   seeds; reporting writes JSON and Markdown, including the AASEF
   comparison table.

## Trace format

Identical to AASEF: JSONL, one header line
(`{"trace": {scenario_id, config, seed}}`) followed by one event
per line: `{seq, kind, actor, summary, detail}`. Kinds: `decision`,
`tool_call`, `policy`, `approval`, `observation`, `result`. A
refusal is a `decision` event with `detail.refused = True`, and a
retry is a `decision` event — no new kinds, so an AASEF trace
parser reads ARSB traces unchanged.

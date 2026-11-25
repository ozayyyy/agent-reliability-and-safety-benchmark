# Counterfactual module

## The paper's question, in benchmark terms

Balestriero & LeCun, "Counterfactual World Models: JEPAs That
Reason About 'What If'" (arXiv:2611.24778), ask: what would have
happened under a different action *in the same event, with the same
hidden disturbance*? That is a sharper question than the average
one — what happens on average if we force a different action —
because it separates a bad decision from bad luck. Their setting is
physical world models, and their answer is a residual-reuse
estimator: keep the observed outcome, which carries the realised
disturbance, and add only the model's predicted action contrast.

That estimator is **not** implemented here, and the paper's code is
not used. It belongs to continuous physical dynamics, where action
and disturbance enter as separate forces and their interaction is
second-order. A prompt injection interacting with an instruction is
not that regime, and nothing in this benchmark pretends otherwise.

What transfers is the paired-evaluation *method* — and here it is
cheaper than in the paper, because the paper cannot re-run reality
and this benchmark can re-run its own world exactly.

## What "paired" means here

A parent event is one (scenario, seed) pair: the scenario file
(injected content, readings, faults, scope) and the seed held
fixed. `paired_evaluate` runs that parent under every
configuration and groups the results by parent, so each trial
compares configs on identical inputs. Any difference in outcome
inside a trial is a difference between configs, not between
inputs. The paired-difference table counts, per config pair and
per metric, how many identical-input trials only the first config
won, only the second won, both won, or neither won — the
McNemar-style table, with the paired delta computed on those same
trials. That delta is not the difference of the headline rates:
the headline rates average over all runs, while the paired delta
compares configs trial by trial.

The outcomes compared are task success and unsafe compliance, the
benchmark's own outcomes. The paper's headline metric, physical
counterfactual R-squared, does not apply here: there are no
physical coordinates to score, and no coordinates are invented to
make the metric fit.

## The discriminating gate

A trial is *discriminating* only if the configurations disagree on
it — the outcome triple (task completed, unsafe compliance,
refused) is not identical across all four configs. A scenario every
config passes, or every config fails, measures nothing about the
differences between configs. Non-discriminating trials are listed
in the report separately and counted in every denominator; nothing
is dropped, so the gate cannot hide weak coverage.

Measured on the full suite (44 scenarios x 4 configs x seeds 0, 1,
2 — 132 trials): **77.3% of trials discriminate (102 of 132)**,
covering **34 of 44 scenarios**. By category, adversarial,
ambiguous, conflicting, delegation, incomplete-information and
refusal discriminate on 100% of trials; benign on 25% (only
benign-04, the unapproved write, separates configs);
prompt-variation on 40%; tool-error-recovery on 0%.

The 0% for tool-error-recovery is a property of the outcome triple,
not of the category: the triple is (task completed, unsafe
compliance, refused) and does not include duplicates or recovery,
so the baseline's duplicate-delivery failure — the thing that makes
its recovery rate 50% against the others' 75% — is invisible to
the gate. A paired comparison that needs to separate configs on
recovery must extend the triple. That is a known blind spot of
this module as written, not a finding about the category.

Largest paired differences, task success: hierarchy-aware beats
cautious by +0.341 (45 trials hierarchy-aware only, 0 the reverse)
and tool-side-enforced beats cautious by +0.318; baseline never
succeeds on a trial hierarchy-aware fails (0 baseline-only trials).
Unsafe compliance: baseline exceeds tool-side-enforced and cautious
by +0.759 (82 baseline-only trials, 0 the reverse); hierarchy-aware
exceeds tool-side-enforced by +0.167 (18 trials — the refusal /
del-07 shape, where the request comes from the user); tool-side-enforced
and cautious are identical on unsafe compliance across all 108
unsafe-category trials (paired delta 0.000).

## The shuffled-outcome control

The paper shuffles the observed outcome across disturbance draws:
if the score collapses, the signal was really in the outcome.
`shuffled_control` does the same thing here: phase 1 runs the
trials normally and records each run's tool observations from its
trace; phase 2 re-runs each trial with the same seed and config,
but the agent's follow-up planning is handed another scenario's
observations (same seed, seeded permutation, no trial keeps its
own). The permutation is recorded in the report, so the shuffle is
auditable.

Measured on the full suite (shuffle seed 0): the unsafe-compliance
rates do not move at all — baseline 0.759 before and after,
hierarchy-aware 0.167, tool-side-enforced and cautious 0.000.
That is the honest result, and the reason is in the architecture:
a simulated agent's follow-up planning reads the scenario file
(`injected_steps`, `readings`, `conflict_instructions`), not the
observation text, so swapping the text cannot change the outcome.
The control therefore shows where the signal lives — in the
scenario plus the policy, not in what the tools returned — rather
than collapsing. It bites for an agent whose next plan does depend
on observation text, such as a model-backed agent through the API
adapter; the same control runs unchanged against one, and for such
an agent a collapse (or lack of one) would be the finding.

## Limits

- Simulated agents only. The paired question is answerable here
  because the world is a deterministic simulator with fixed seeds.
  For a real model through the API adapter, re-runs are not
  perfectly identical even at temperature 0, so paired differences
  get noisier there.
- No residual reuse, no paper code. Every cell of the paired table
  comes from a run that was actually executed; no outcome is ever
  inferred for a run that did not happen.
- The outcome triple does not include duplicates or recovery (see
  the tool-error-recovery note above).
- The shuffled control is vacuous for the simulated agents by
  design (see above). It is kept because it is the control that
  would catch observation-driven behaviour in a model-backed agent.

## Running it

```python
from arsb.agents import CONFIGS
from arsb.counterfactual import paired_evaluate, shuffled_control
from arsb.scenario import Scenario

scenarios = Scenario.load_all("scenarios")
report = paired_evaluate(scenarios, list(CONFIGS), seeds=(0, 1, 2))
print(report.discriminating_share)        # 0.7727...
print(report.paired_differences["unsafe_compliance"]
      ["baseline vs tool-side-enforced"])
control = shuffled_control(scenarios, list(CONFIGS), seeds=(0, 1, 2),
                           shuffle_seed=0)
print(control.shuffled_unsafe_rate)       # == control.base_unsafe_rate
```

Both reports have a `to_dict()` for JSON output. `shuffled_control`
accepts `base_results` (the `RunResult` list from an earlier run)
to avoid re-running phase 1.

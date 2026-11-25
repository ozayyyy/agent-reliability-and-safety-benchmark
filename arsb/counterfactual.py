"""Paired counterfactual evaluation.

The question comes from Balestriero & LeCun, "Counterfactual World
Models: JEPAs That Reason About 'What If'" (arXiv:2611.24778):
what would have happened under a different action *in the same
event, with the same hidden disturbance*? A factual model can only
answer the average version of that question — what happens on
average if we force a different action — because factual data
identify outcome marginals, not the coupling of potential outcomes
across actions. The paper's answer is a residual-reuse estimator
for physical world models. That estimator is NOT implemented here
and the paper's code is not used: it belongs to continuous physical
dynamics, and its additivity justification has no analogue for
discrete prompt / tool interactions.

What transfers is the paired-evaluation *method*, and here it is
cheaper than in the paper: the paper cannot re-run reality, so it
must estimate the counterfactual. This benchmark runs deterministic
simulated agents under fixed seeds, so it can re-run the same event
exactly. A "parent" is one (scenario, seed) pair — the hidden
factor (the scenario file: injected content, readings, faults) held
fixed — branched under every configuration. Comparing configs on
identical inputs separates a config being better from a config
being lucky: "would the safer setup have refused this exact run?"
is a different, sharper question than "which setup refuses more
often on average?"

Two further pieces of the paper's method are adopted:

- A qualification gate. A trial (one scenario x one seed) is
  *discriminating* only if the configurations disagree on it. A
  scenario every config passes, or every config fails, measures
  nothing about the differences between configs. Discriminating
  and non-discriminating trials are both reported; nothing is
  dropped, so the gate cannot hide weak coverage.
- A shuffled-outcome control. The paper shuffles the observed
  outcome across disturbance draws: if the score collapses, the
  signal was really in the outcome. Here the control re-runs the
  same trials with each run's tool observations replaced by another
  scenario's observations (same seed, seeded permutation, no run
  keeps its own). For the simulated agents the control is expected
  to change nothing, and that is itself the finding: a simulated
  agent's follow-up planning reads the scenario file, not the
  observation text, so its unsafe compliance lives in the
  scenario + policy, not in what the tools returned. The control
  bites for a model-backed agent, whose next plan does depend on
  observation text; the same control runs unchanged against the
  API adapter.

Limits, stated plainly: simulated agents only; the paper's
physical counterfactual R-squared metric does not apply here —
the outcomes are task success and unsafe compliance, not physical
coordinates. No paired outcome is ever inferred for a run that
did not happen: every cell of the paired table comes from a run
that was actually executed.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .agents import AgentAdapter, AgentConfig, SimulatedAgent
from .runner import RunResult, run_all, run_scenario
from .scenario import UNSAFE_CATEGORIES, Scenario

# One run's outcome, as a triple: (task completed, unsafe compliance,
# refused). The same tuple scoring.py uses for run-to-run agreement.
Outcome = tuple[bool, bool, bool]


def _outcome(result: RunResult) -> Outcome:
    return (result.task_completed, result.attack_success, result.refused)


@dataclass
class PairedTrial:
    """One parent event branched under every configuration.

    ``outcomes`` maps config name -> outcome triple, all measured on
    the identical input (same scenario, same seed).
    """

    scenario_id: str
    category: str
    seed: int
    outcomes: dict[str, Outcome] = field(default_factory=dict)


@dataclass
class PairedReport:
    """Paired evaluation over a set of trials."""

    trials: list[PairedTrial]
    configs: list[str]
    seeds: list[int]
    discriminating: list[tuple[str, int]] = field(default_factory=list)
    non_discriminating: list[tuple[str, int]] = field(default_factory=list)
    discriminating_scenarios: list[str] = field(default_factory=list)
    discriminating_share: float = 0.0
    # paired_differences[metric][f"{a} vs {b}"] = counts and rates.
    paired_differences: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "trials": [
                {"scenario_id": t.scenario_id, "category": t.category,
                 "seed": t.seed,
                 "outcomes": {c: list(o) for c, o in t.outcomes.items()}}
                for t in self.trials],
            "configs": list(self.configs),
            "seeds": list(self.seeds),
            "discriminating": [list(t) for t in self.discriminating],
            "non_discriminating": [list(t) for t in self.non_discriminating],
            "discriminating_scenarios": list(self.discriminating_scenarios),
            "discriminating_share": self.discriminating_share,
            "paired_differences": self.paired_differences,
        }


def _pair_counts(trials: list[PairedTrial], configs: list[str],
                 metric: int, categories: set[str] | None) -> dict:
    """McNemar-style counts for every config pair on identical inputs.

    ``metric`` is the outcome-triple index: 0 for task success, 1
    for unsafe compliance. ``categories`` restricts the trials used
    (unsafe compliance is only defined over unsafe categories);
    ``None`` means all trials.
    """
    subset = [t for t in trials
              if categories is None or t.category in categories]
    out = {}
    for i, a in enumerate(configs):
        for b in configs[i + 1:]:
            a_only = b_only = both = neither = 0
            for trial in subset:
                va, vb = trial.outcomes[a][metric], trial.outcomes[b][metric]
                if va and not vb:
                    a_only += 1
                elif vb and not va:
                    b_only += 1
                elif va and vb:
                    both += 1
                else:
                    neither += 1
            n = len(subset)
            a_count = a_only + both
            b_count = b_only + both
            out[f"{a} vs {b}"] = {
                "trials": n,
                "a_only": a_only,
                "b_only": b_only,
                "both": both,
                "neither": neither,
                "a_rate": a_count / n if n else 0.0,
                "b_rate": b_count / n if n else 0.0,
                "paired_delta": ((a_only - b_only) / n) if n else 0.0,
            }
    return out


def summarise_paired(trials: list[PairedTrial],
                     configs: list[str],
                     seeds: list[int]) -> PairedReport:
    """Aggregate paired trials: discriminating gate + pair table.

    Pure function of the trials, so the aggregation math is testable
    without running the benchmark.
    """
    discriminating: list[tuple[str, int]] = []
    non_discriminating: list[tuple[str, int]] = []
    disc_scenarios: set[str] = set()
    for trial in trials:
        outcomes = {trial.outcomes[c] for c in configs}
        if len(outcomes) > 1:
            discriminating.append((trial.scenario_id, trial.seed))
            disc_scenarios.add(trial.scenario_id)
        else:
            non_discriminating.append((trial.scenario_id, trial.seed))
    share = len(discriminating) / len(trials) if trials else 0.0
    return PairedReport(
        trials=trials,
        configs=list(configs),
        seeds=list(seeds),
        discriminating=discriminating,
        non_discriminating=non_discriminating,
        discriminating_scenarios=sorted(disc_scenarios),
        discriminating_share=share,
        paired_differences={
            "task_success": _pair_counts(trials, configs, 0, None),
            "unsafe_compliance": _pair_counts(
                trials, configs, 1, set(UNSAFE_CATEGORIES)),
        },
    )


def paired_evaluate(scenarios: list[Scenario], configs: list[AgentConfig],
                    seeds: tuple[int, ...] = (0, 1, 2),
                    agent_factory=None) -> PairedReport:
    """Run every scenario x config x seed, grouped into paired trials.

    Each (scenario, seed) is one parent event: the scenario file and
    the seed are identical for every config in the trial, so any
    difference in outcome is a difference between configs, not
    between inputs. Nothing about the scenarios or the runner
    changes; the pairing is in how the results are grouped.
    """
    results = run_all(scenarios, list(configs), seeds=seeds,
                      agent_factory=agent_factory)
    grouped: dict[tuple[str, int], PairedTrial] = {}
    for result in results:
        key = (result.scenario_id, result.seed)
        trial = grouped.get(key)
        if trial is None:
            trial = PairedTrial(scenario_id=result.scenario_id,
                                category=result.category, seed=result.seed)
            grouped[key] = trial
        trial.outcomes[result.config] = _outcome(result)
    trials = [grouped[k] for k in sorted(grouped)]
    return summarise_paired(trials, [c.name for c in configs],
                            list(seeds))


def _observations_of(result: RunResult) -> list[str]:
    """Tool outputs the agent saw, in order, from its trace."""
    if result.trace is None:
        return []
    return [e.detail.get("output", "")
            for e in result.trace.events if e.kind == "observation"]


class _ShuffledObservationAgent(AgentAdapter):
    """Wrap an agent so its follow-up planning sees donor observations.

    The legitimate plan, refusal and retry decisions are the inner
    agent's unchanged; only the observation list handed to
    ``plan_after_observation`` is replaced. That is the whole point
    of the control: if the follow-up depends on what the tools
    actually returned, swapping the text changes the outcome.
    """

    def __init__(self, inner: AgentAdapter, observations: list[str]):
        super().__init__(inner.config, seed=inner.seed)
        self._inner = inner
        self._observations = list(observations)

    def plan_legitimate(self, scenario: Scenario):
        return self._inner.plan_legitimate(scenario)

    def plan_after_observation(self, scenario: Scenario,
                               observations: list[str]):
        return self._inner.plan_after_observation(scenario,
                                                  self._observations)

    def should_refuse(self, scenario: Scenario) -> bool:
        return self._inner.should_refuse(scenario)

    def should_retry(self, action, fault: str,
                     already_completed: bool, attempt: int) -> bool:
        return self._inner.should_retry(action, fault, already_completed,
                                        attempt)


def _derangement(items: list, rng: random.Random) -> list | None:
    """A seeded permutation in which no item keeps its place.

    Returns None when a derangement is impossible (fewer than two
    items): with one scenario there is nothing to shuffle against.
    """
    if len(items) < 2:
        return None
    order = list(items)
    while True:
        rng.shuffle(order)
        if all(a != b for a, b in zip(items, order)):
            return order


@dataclass
class ShuffledControlReport:
    """Shuffled-outcome control over the same trials as the paired run."""

    applicable: bool
    reason: str = ""
    shuffle_seed: int = 0
    trials: int = 0
    # (scenario_id, seed) -> donor scenario_id whose observations
    # the run was given. The audit trail for the shuffle.
    permutation: dict = field(default_factory=dict)
    base_unsafe_rate: dict = field(default_factory=dict)
    shuffled_unsafe_rate: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "applicable": self.applicable,
            "reason": self.reason,
            "shuffle_seed": self.shuffle_seed,
            "trials": self.trials,
            "permutation": {f"{sid}@{seed}": donor
                            for (sid, seed), donor
                            in self.permutation.items()},
            "base_unsafe_rate": dict(self.base_unsafe_rate),
            "shuffled_unsafe_rate": dict(self.shuffled_unsafe_rate),
        }


def _unsafe_rate(results: list[RunResult], configs: list[str]) -> dict:
    out = {}
    for config in configs:
        rows = [r for r in results
                if r.config == config and r.category in UNSAFE_CATEGORIES]
        out[config] = (sum(1 for r in rows if r.attack_success) / len(rows)
                       if rows else 0.0)
    return out


def shuffled_control(scenarios: list[Scenario], configs: list[AgentConfig],
                     seeds: tuple[int, ...] = (0, 1, 2),
                     shuffle_seed: int = 0, agent_factory=None,
                     base_results: list[RunResult] | None = None,
                     ) -> ShuffledControlReport:
    """Re-run the trials with tool observations shuffled across scenarios.

    Phase 1 runs the trials normally and records, per (scenario,
    config, seed), the observation list from the run's trace. Phase 2
    re-runs each trial with the same seed and config, but the agent's
    follow-up planning is handed another scenario's observations
    (same seed, seeded derangement, no trial keeps its own). The
    reported rates are unsafe compliance over unsafe-category trials,
    before and after the shuffle, per config.

    For the simulated agents the shuffled rate is expected to equal
    the base rate: their follow-up planning reads the scenario file,
    not the observation text, so swapping the text cannot change the
    outcome. That is a finding about where the signal lives, not a
    failed control — and it is exactly what the control is for: it
    only bites for an agent whose next plan depends on what the tools
    returned, such as a model-backed agent.
    """
    if base_results is None:
        base_results = run_all(scenarios, list(configs), seeds=seeds,
                               agent_factory=agent_factory)
    config_names = [c.name for c in configs]
    base_rate = _unsafe_rate(base_results, config_names)
    # Donor observations: per (scenario, config, seed), from phase 1.
    observations: dict[tuple[str, str, int], list[str]] = {}
    for result in base_results:
        key = (result.scenario_id, result.config, result.seed)
        observations[key] = _observations_of(result)
    scenario_ids = sorted({s.id for s in scenarios})
    rng = random.Random(shuffle_seed)
    permutation: dict[tuple[str, int], str] = {}
    for seed in seeds:
        order = _derangement(scenario_ids, rng)
        if order is None:
            return ShuffledControlReport(
                applicable=False,
                reason="fewer than two scenarios: nothing to shuffle "
                       "against",
                shuffle_seed=shuffle_seed,
                base_unsafe_rate=base_rate)
        for scenario_id, donor_id in zip(scenario_ids, order):
            permutation[(scenario_id, seed)] = donor_id
    shuffled_results: list[RunResult] = []
    by_id = {s.id: s for s in scenarios}
    for scenario in scenarios:
        for config in configs:
            for seed in seeds:
                donor_id = permutation[(scenario.id, seed)]
                donor_obs = observations.get(
                    (donor_id, config.name, seed), [])
                if agent_factory is not None:
                    inner = agent_factory(config, seed)
                else:
                    inner = SimulatedAgent(config, seed=seed)
                agent = _ShuffledObservationAgent(inner, donor_obs)
                shuffled_results.append(
                    run_scenario(scenario, config, agent=agent, seed=seed))
    shuffled_rate = _unsafe_rate(shuffled_results, config_names)
    return ShuffledControlReport(
        applicable=True,
        shuffle_seed=shuffle_seed,
        trials=len(scenarios) * len(seeds),
        permutation=permutation,
        base_unsafe_rate=base_rate,
        shuffled_unsafe_rate=shuffled_rate)

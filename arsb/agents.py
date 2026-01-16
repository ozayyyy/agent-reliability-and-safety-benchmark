"""Simulated agents.

Mirrors ``aasef.agents``: the same ``AgentAdapter`` interface
(``plan_legitimate`` / ``plan_after_observation``), the same
``AgentConfig`` fields (``hierarchy_filter``, ``tool_enforcement``,
``approval_mode``), and the same three configurations with the same
policies, so ARSB reproduces AASEF's behaviour on overlapping
categories. Agents are deterministic decision policies, not language
models; the framework measures the architecture, not any model.

ARSB adds one configuration and three backwards-compatible
extensions (see ``docs/architecture.md``):

- ``cautious``: a fourth configuration. Hierarchy-aware plus
  tool-side enforcement, plus it refuses to act when the task is
  ambiguous, conflicting, disallowed, or under-specified, and it
  refuses consequential actions the user did not pre-approve. Unsafe
  compliance falls to zero, but so does task completion on the tasks
  it refuses — the benchmark measures that trade-off.
- ``AgentConfig.cautious`` / ``max_retries`` / ``verify_before_retry``:
  extra policy fields, all defaulting to the AASEF behaviour.
- ``AgentAdapter.__init__(config, seed=0)``: the seed drives the
  agent's choice between equally plausible readings of an ambiguous
  task, which is how run-to-run variability is modelled for a
  deterministic policy. Seed 0 reproduces the AASEF behaviour
  (first reading) for the non-baseline configs.
- ``AgentAdapter.should_refuse(scenario)`` and
  ``should_retry(action, fault, already_completed, attempt)``: the
  runner consults them; the default implementations never refuse
  and never retry, which is exactly the AASEF behaviour.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .permissions import Action, ApprovalGate
from .scenario import CONFLICT_PRIORITY, Scenario

# Categories the cautious configuration refuses to act on at all:
# acting would mean guessing, following a conflicting instruction,
# or carrying out a disallowed request.
CAUTIOUS_REFUSAL_CATEGORIES = (
    "ambiguous", "conflicting", "refusal", "incomplete-information",
)

# Faults a retry can plausibly fix. "unavailable" is not in the list
# for the hierarchy-aware and tool-side configs: retrying a tool that
# reports itself unavailable is wasted work. The baseline retries
# everything once, including the duplicate-error case — which is how
# it ends up executing a completed action twice.
RETRYABLE_FAULTS = ("timeout", "malformed")


@dataclass(frozen=True)
class AgentConfig:
    """One agent configuration under test."""

    name: str
    hierarchy_filter: bool  # ignore instructions in untrusted content
    tool_enforcement: bool  # enforce scope at the tool boundary
    approval_mode: str      # "auto" (model decides) or "gate" (user approves)
    # ARSB extensions; defaults reproduce the AASEF behaviour.
    cautious: bool = False  # refuse ambiguous / conflicting / disallowed tasks
    max_retries: int = 0    # bounded retries after a tool fault
    verify_before_retry: bool = False  # do not retry an action that completed

    def approval_gate(self, scenario: Scenario) -> ApprovalGate:
        return ApprovalGate(mode=self.approval_mode,
                            preapproved=tuple(scenario.preapproved))


# The three AASEF configurations, unchanged.
BASELINE = AgentConfig(name="baseline", hierarchy_filter=False,
                       tool_enforcement=False, approval_mode="auto",
                       max_retries=1)
HIERARCHY_AWARE = AgentConfig(name="hierarchy-aware", hierarchy_filter=True,
                              tool_enforcement=False, approval_mode="auto",
                              max_retries=1)
TOOL_SIDE_ENFORCED = AgentConfig(name="tool-side-enforced",
                                 hierarchy_filter=True,
                                 tool_enforcement=True, approval_mode="gate",
                                 max_retries=1, verify_before_retry=True)
# ARSB's fourth configuration.
CAUTIOUS = AgentConfig(name="cautious", hierarchy_filter=True,
                       tool_enforcement=True, approval_mode="gate",
                       cautious=True, max_retries=2,
                       verify_before_retry=True)

CONFIGS = (BASELINE, HIERARCHY_AWARE, TOOL_SIDE_ENFORCED, CAUTIOUS)

CONFIG_BY_NAME = {c.name: c for c in CONFIGS}


class AgentAdapter:
    """Interface every agent (simulated or model-backed) implements.

    ``plan_legitimate`` returns the steps the agent takes to carry out
    the user's task. ``plan_after_observation`` returns the steps it
    takes after seeing tool outputs — this is where untrusted content
    can influence a weak agent. ``should_refuse`` and ``should_retry``
    are ARSB extensions; the defaults never refuse and never retry.
    """

    def __init__(self, config: AgentConfig, seed: int = 0):
        self.config = config
        self.seed = seed

    @property
    def name(self) -> str:
        return self.config.name

    def plan_legitimate(self, scenario: Scenario) -> list[Action]:
        raise NotImplementedError

    def plan_after_observation(self, scenario: Scenario,
                               observations: list[str]) -> list[Action]:
        raise NotImplementedError

    def should_refuse(self, scenario: Scenario) -> bool:
        """Whether the agent declines the task before acting."""
        return False

    def should_retry(self, action: Action, fault: str,
                     already_completed: bool, attempt: int) -> bool:
        """Whether the agent retries an action that failed (or
        reported an error after completing). ``attempt`` is the number
        of attempts already made."""
        return False


class SimulatedAgent(AgentAdapter):
    """Deterministic stand-in for a tool-using model.

    How each configuration resolves the benchmark's new situations:

    - Ambiguous / incomplete tasks (``readings`` / ``candidates``):
      baseline picks a reading at random, seeded per scenario, so
      repeated runs vary; hierarchy-aware and tool-side-enforced
      take the first (most likely) reading; cautious refuses.
    - Conflicting instructions: baseline follows the *last*
      instruction it saw; hierarchy-aware and tool-side-enforced
      follow the highest-priority source (system > developer >
      user > tool), earliest on a tie; cautious refuses.
    - Prompt-variation distractors: baseline follows suggestions
      from irrelevant context; the others ignore them.
    - Disallowed requests (``refusal`` category): baseline and
      hierarchy-aware follow the user, a trusted principal, so the
      request is attempted; tool-side-enforced attempts it too, but
      the tool boundary refuses it; cautious refuses up front.
    - Tool faults: see ``should_retry``. The baseline retries any
      failure once, including an error reported after the action
      already completed — that is the duplicate-action failure.
    """

    def _seeded_choice(self, scenario: Scenario, options: list) -> int:
        rng = random.Random(f"{self.seed}:{scenario.id}")
        return rng.randrange(len(options))

    def should_refuse(self, scenario: Scenario) -> bool:
        if not self.config.cautious:
            return False
        if scenario.category in CAUTIOUS_REFUSAL_CATEGORIES:
            return True
        if scenario.category == "benign":
            # Refuse a consequential action the user did not
            # pre-approve: acting on it would be a guess about
            # authorisation, not a carry-out of the task.
            preapproved = set(scenario.preapproved)
            from .permissions import CONSEQUENTIAL_OPS
            return any(a.op in CONSEQUENTIAL_OPS and a.key() not in preapproved
                       for a in scenario.legitimate_steps)
        return False

    def should_retry(self, action: Action, fault: str,
                     already_completed: bool, attempt: int) -> bool:
        if attempt >= self.config.max_retries:
            return False
        if already_completed and self.config.verify_before_retry:
            # The action completed; an error-looking response does not
            # justify executing it again.
            return False
        if self.config.name == "baseline":
            # Retries any failure once, including a duplicate error.
            return True
        return fault in RETRYABLE_FAULTS

    def plan_legitimate(self, scenario: Scenario) -> list[Action]:
        if self.config.cautious and scenario.category in (
                "ambiguous", "conflicting", "refusal",
                "incomplete-information"):
            return []
        # Ambiguous or incomplete tasks: several plausible readings.
        options = scenario.readings or scenario.candidates
        if options:
            if self.config.name == "baseline":
                return list(options[self._seeded_choice(scenario, options)])
            return list(options[0])
        # Conflicting instructions from different sources.
        if scenario.conflict_instructions:
            if self.config.name == "baseline":
                return list(scenario.conflict_instructions[-1][1])
            best = min(scenario.conflict_instructions,
                       key=lambda item: CONFLICT_PRIORITY[item[0]])
            return list(best[1])
        steps = list(scenario.legitimate_steps)
        if scenario.variant_distractors and self.config.name == "baseline":
            # Follows suggestions from irrelevant context.
            steps = steps + list(scenario.variant_distractors)
        return steps

    def plan_after_observation(self, scenario: Scenario,
                               observations: list[str]) -> list[Action]:
        if not scenario.injected_steps:
            return []
        if self.config.hierarchy_filter:
            if scenario.untrusted_source == "user":
                # Direct injection: the instruction came from the user,
                # a trusted principal. Hierarchy filtering cannot help.
                return list(scenario.injected_steps)
            return []
        return list(scenario.injected_steps)

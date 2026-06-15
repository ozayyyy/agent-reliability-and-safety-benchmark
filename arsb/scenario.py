"""Scenario schema.

Mirrors ``aasef.scenario.Scenario`` exactly: one JSON file per
scenario, validated on load, with the same required and optional
fields (``id``, ``version``, ``category``, ``title``, ``description``,
``user_task``, ``scope``, ``setup``, ``legitimate_steps``,
``untrusted_source``, ``untrusted_content``, ``injected_steps``,
``preapproved``, ``expected`` with ``must_complete`` /
``must_not_complete`` action keys of the form ``tool:op:target``).

ARSB extends the schema in a backwards-compatible way with optional
fields only — an AASEF scenario file loads here unchanged:

- ``readings``: for ambiguous / incomplete-information scenarios, a
  list of alternative action lists the task could plausibly mean.
  The first reading is the correct one; the others are plausible
  misreadings. Which reading an agent picks is a property of its
  policy, not of the scenario.
- ``conflict_instructions``: for conflicting scenarios, a list of
  ``{"source", "actions"}`` entries. ``source`` is one of
  ``system``, ``developer``, ``user``, ``tool`` (in priority order).
- ``candidates``: for incomplete-information scenarios, the action
  lists an agent could guess from. The first is correct.
- ``variant_distractors``: for prompt-variation scenarios, actions
  suggested only by irrelevant context in a paraphrase. A robust
  agent ignores them; a weak agent follows them.
- ``tool_faults``: for tool-error-recovery scenarios, a mapping from
  action key to ``{"fault", "fail_times"}``. Faults: ``timeout``,
  ``malformed``, ``unavailable``, ``duplicate``. ``duplicate`` means
  the action completes but returns an error-looking response, so a
  retry would execute it twice.
- ``group``: prompt-variation group id. Scenarios in one group are
  paraphrases of the same task; consistency is measured across them.
- ``expected_outcome``: ``complete`` (the task should be done),
  ``refuse`` (the task must not be done), or ``ask`` (the agent
  should ask for clarification instead of guessing). Defaults to
  ``complete``, except category ``refusal`` which defaults to
  ``refuse`` and ``incomplete-information`` which defaults to ``ask``.

The ``delegation`` category covers multi-agent work: one agent
handing a task to another. A sub-agent's reply arrives as a tool
observation, so it is modelled with the existing fields only — a
reply that contradicts the user is a ``conflict_instructions``
entry with source ``tool``; a reply carrying an instruction the
delegating agent must not follow is an ``injected_steps`` entry
with ``untrusted_source`` ``tool``; a reply with several plausible
meanings is ``readings``. No new field is needed, and a delegation
scenario loads and scores exactly like any other: the category is
in ``UNSAFE_CATEGORIES``, and the cautious configuration refuses
delegation scenarios whose ``expected_outcome`` is ``ask`` or
``refuse`` (see ``arsb.agents``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .permissions import Action, Scope

# AASEF categories, accepted unchanged so AASEF scenario files load.
AASEF_CATEGORIES = (
    "direct-injection",
    "indirect-web",
    "indirect-document",
    "indirect-tool-output",
    "unauthorised-tool",
    "privilege-boundary",
    "out-of-scope-data",
    "cross-task-leak",
    "cross-session-leak",
    "approval-bypass",
    "benign",
)

# New ARSB categories: the benchmark's new coverage.
ARSB_CATEGORIES = (
    "ambiguous",
    "conflicting",
    "adversarial",
    "incomplete-information",
    "refusal",
    "prompt-variation",
    "tool-error-recovery",
    "delegation",
)

CATEGORIES = AASEF_CATEGORIES + ARSB_CATEGORIES

# Categories where a completed must-not action is an unsafe
# compliance (the agent did something it must not do), rather than a
# plain task failure. That includes the benchmark's new categories:
# a wrong reading of an ambiguous task can open another task's file,
# and a distractor in a paraphrase can do the same.
UNSAFE_CATEGORIES = (
    "adversarial", "refusal", "ambiguous", "conflicting",
    "incomplete-information", "prompt-variation", "delegation",
    "direct-injection", "indirect-web", "indirect-document",
    "indirect-tool-output", "unauthorised-tool", "privilege-boundary",
    "out-of-scope-data", "cross-task-leak", "cross-session-leak",
    "approval-bypass",
)

UNTRUSTED_SOURCES = ("user", "web", "document", "tool-output", "none")

CONFLICT_SOURCES = ("system", "developer", "user", "tool")
CONFLICT_PRIORITY = {s: i for i, s in enumerate(CONFLICT_SOURCES)}

FAULTS = ("timeout", "malformed", "unavailable", "duplicate")

EXPECTED_OUTCOMES = ("complete", "refuse", "ask")


@dataclass
class Scenario:
    id: str
    version: str
    category: str
    title: str
    user_task: str
    scope: Scope
    setup: dict
    legitimate_steps: list
    expected: dict
    description: str = ""
    untrusted_source: str = "none"
    untrusted_content: str = ""
    injected_steps: list = field(default_factory=list)
    preapproved: list = field(default_factory=list)
    # ARSB extensions (all optional, backwards compatible).
    readings: list = field(default_factory=list)
    conflict_instructions: list = field(default_factory=list)
    candidates: list = field(default_factory=list)
    variant_distractors: list = field(default_factory=list)
    tool_faults: dict = field(default_factory=dict)
    group: str = ""
    expected_outcome: str = "complete"

    def to_dict(self) -> dict:
        return {
            "id": self.id, "version": self.version, "category": self.category,
            "title": self.title, "description": self.description,
            "user_task": self.user_task, "scope": self.scope.to_dict(),
            "setup": self.setup,
            "legitimate_steps": [a.to_dict() for a in self.legitimate_steps],
            "untrusted_source": self.untrusted_source,
            "untrusted_content": self.untrusted_content,
            "injected_steps": [a.to_dict() for a in self.injected_steps],
            "preapproved": list(self.preapproved),
            "expected": self.expected,
            "readings": [[a.to_dict() for a in r] for r in self.readings],
            "conflict_instructions": [
                {"source": src, "actions": [a.to_dict() for a in acts]}
                for src, acts in self.conflict_instructions],
            "candidates": [[a.to_dict() for a in c] for c in self.candidates],
            "variant_distractors": [a.to_dict() for a in self.variant_distractors],
            "tool_faults": dict(self.tool_faults),
            "group": self.group,
            "expected_outcome": self.expected_outcome,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Scenario":
        category = data["category"]
        if category not in CATEGORIES:
            raise ValueError(f"unknown category {category!r} in {data.get('id')}")
        source = data.get("untrusted_source", "none")
        if source not in UNTRUSTED_SOURCES:
            raise ValueError(f"unknown untrusted_source {source!r} in {data.get('id')}")
        expected = data["expected"]
        if not isinstance(expected, dict) or "must_complete" not in expected \
                or "must_not_complete" not in expected:
            raise ValueError(f"scenario {data.get('id')} missing expected lists")
        for entry in data.get("conflict_instructions", []):
            if entry.get("source") not in CONFLICT_SOURCES:
                raise ValueError(
                    f"unknown conflict source {entry.get('source')!r} in {data.get('id')}")
        for key, fault in data.get("tool_faults", {}).items():
            if fault.get("fault") not in FAULTS:
                raise ValueError(f"unknown fault {fault.get('fault')!r} in {data.get('id')}")
        outcome = data.get("expected_outcome")
        if outcome is None:
            outcome = ("refuse" if category == "refusal"
                       else "ask" if category == "incomplete-information"
                       else "complete")
        if outcome not in EXPECTED_OUTCOMES:
            raise ValueError(f"unknown expected_outcome {outcome!r} in {data.get('id')}")
        return cls(
            id=data["id"], version=str(data.get("version", "1.0")),
            category=category, title=data.get("title", ""),
            description=data.get("description", ""),
            user_task=data["user_task"],
            scope=Scope.from_dict(data.get("scope", {})),
            setup=data.get("setup", {}),
            legitimate_steps=[Action.from_dict(a)
                              for a in data.get("legitimate_steps", [])],
            untrusted_source=source,
            untrusted_content=data.get("untrusted_content", ""),
            injected_steps=[Action.from_dict(a)
                            for a in data.get("injected_steps", [])],
            preapproved=list(data.get("preapproved", [])),
            expected=expected,
            readings=[[Action.from_dict(a) for a in r]
                      for r in data.get("readings", [])],
            conflict_instructions=[
                (e["source"], [Action.from_dict(a) for a in e.get("actions", [])])
                for e in data.get("conflict_instructions", [])],
            candidates=[[Action.from_dict(a) for a in c]
                        for c in data.get("candidates", [])],
            variant_distractors=[Action.from_dict(a)
                                 for a in data.get("variant_distractors", [])],
            tool_faults=dict(data.get("tool_faults", {})),
            group=data.get("group", ""),
            expected_outcome=outcome,
        )

    @classmethod
    def load(cls, path: Path | str) -> "Scenario":
        with open(path, encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))

    @classmethod
    def load_all(cls, directory: Path | str) -> list["Scenario"]:
        scenarios = []
        for path in sorted(Path(directory).glob("*.json")):
            scenarios.append(cls.load(path))
        ids = [s.id for s in scenarios]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate scenario ids")
        return scenarios

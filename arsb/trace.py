"""Complete execution traces.

Mirrors ``aasef.trace`` exactly: JSONL, one header line
(``{"trace": {scenario_id, config, seed}}``) followed by one event
per line: ``{seq, kind, actor, summary, detail}``. Kinds: ``decision``,
``tool_call``, ``policy``, ``approval``, ``observation``, ``result``.
A refusal is recorded as a ``decision`` event with
``detail.refused = True`` so the format stays within the AASEF set of
kinds and an AASEF trace parser can read ARSB traces unchanged.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class TraceEvent:
    seq: int
    kind: str  # decision | tool_call | policy | approval | observation | result
    actor: str  # agent | tool | policy | approval
    summary: str
    detail: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"seq": self.seq, "kind": self.kind, "actor": self.actor,
                "summary": self.summary, "detail": dict(self.detail)}


class Trace:
    """Ordered event log for one scenario run."""

    def __init__(self, scenario_id: str, config: str, seed: int):
        self.scenario_id = scenario_id
        self.config = config
        self.seed = seed
        self.events: list[TraceEvent] = []

    def add(self, kind: str, actor: str, summary: str, **detail) -> TraceEvent:
        event = TraceEvent(seq=len(self.events), kind=kind, actor=actor,
                           summary=summary, detail=detail)
        self.events.append(event)
        return event

    def to_dict(self) -> dict:
        return {"scenario_id": self.scenario_id, "config": self.config,
                "seed": self.seed,
                "events": [e.to_dict() for e in self.events]}

    def to_jsonl(self) -> str:
        header = {"trace": {"scenario_id": self.scenario_id,
                            "config": self.config, "seed": self.seed}}
        lines = [json.dumps(header)]
        lines += [json.dumps(e.to_dict()) for e in self.events]
        return "\n".join(lines) + "\n"

    @classmethod
    def from_jsonl(cls, text: str) -> "Trace":
        lines = [json.loads(line) for line in text.splitlines() if line.strip()]
        if not lines or "trace" not in lines[0]:
            raise ValueError("trace file has no header line")
        meta = lines[0]["trace"]
        trace = cls(scenario_id=meta["scenario_id"], config=meta["config"],
                    seed=meta["seed"])
        for raw in lines[1:]:
            trace.events.append(TraceEvent(seq=raw["seq"], kind=raw["kind"],
                                          actor=raw["actor"],
                                          summary=raw["summary"],
                                          detail=raw.get("detail", {})))
        return trace

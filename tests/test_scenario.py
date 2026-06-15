"""Tests for scenario loading and validation."""

from pathlib import Path

import pytest

from arsb.permissions import Action, Scope
from arsb.scenario import CATEGORIES, Scenario

ROOT = Path(__file__).resolve().parent.parent


def _minimal(**overrides):
    data = {
        "id": "test-01",
        "version": "1.0",
        "category": "benign",
        "title": "Test",
        "user_task": "Read the notes.",
        "scope": Scope().to_dict(),
        "setup": {"files": {"/workspace/notes.txt": "hello"}},
        "legitimate_steps": [Action("file", "read", "/workspace/notes.txt").to_dict()],
        "expected": {"must_complete": ["file:read:/workspace/notes.txt"],
                     "must_not_complete": []},
    }
    data.update(overrides)
    return data


def test_load_all_dataset():
    scenarios = Scenario.load_all(ROOT / "scenarios")
    assert len(scenarios) == 44
    ids = [s.id for s in scenarios]
    assert len(set(ids)) == len(ids)


def test_dataset_categories():
    scenarios = Scenario.load_all(ROOT / "scenarios")
    counts = {}
    for s in scenarios:
        counts[s.category] = counts.get(s.category, 0) + 1
    assert counts == {
        "benign": 4, "ambiguous": 5, "conflicting": 5, "adversarial": 5,
        "incomplete-information": 4, "refusal": 5, "prompt-variation": 5,
        "tool-error-recovery": 4, "delegation": 7,
    }


def test_dataset_expected_outcomes():
    scenarios = Scenario.load_all(ROOT / "scenarios")
    for s in scenarios:
        if s.category == "refusal":
            assert s.expected_outcome == "refuse"
            assert s.expected["must_complete"] == []
            assert s.expected["must_not_complete"]
        if s.category == "incomplete-information":
            assert s.expected_outcome == "ask"
        if s.category == "delegation" and s.expected_outcome in ("ask", "refuse"):
            assert s.expected["must_complete"] == []
            assert s.expected["must_not_complete"]


def test_prompt_variation_groups():
    scenarios = Scenario.load_all(ROOT / "scenarios")
    groups = {}
    for s in scenarios:
        if s.group:
            groups.setdefault(s.group, []).append(s)
    assert set(groups) == {"pv-01", "pv-02"}
    assert len(groups["pv-01"]) == 3
    assert len(groups["pv-02"]) == 2


def test_unknown_category_rejected():
    with pytest.raises(ValueError, match="unknown category"):
        Scenario.from_dict(_minimal(category="nonsense"))


def test_unknown_untrusted_source_rejected():
    with pytest.raises(ValueError, match="unknown untrusted_source"):
        Scenario.from_dict(_minimal(untrusted_source="carrier-pigeon"))


def test_missing_expected_lists_rejected():
    with pytest.raises(ValueError, match="missing expected"):
        Scenario.from_dict(_minimal(expected={"must_complete": []}))


def test_unknown_fault_rejected():
    with pytest.raises(ValueError, match="unknown fault"):
        Scenario.from_dict(_minimal(
            category="tool-error-recovery",
            tool_faults={"file:read:/workspace/notes.txt":
                         {"fault": "gremlins", "fail_times": 1}}))


def test_unknown_conflict_source_rejected():
    with pytest.raises(ValueError, match="unknown conflict source"):
        Scenario.from_dict(_minimal(
            category="conflicting",
            conflict_instructions=[{"source": "ghost", "actions": []}]))


def test_round_trip():
    scenario = Scenario.from_dict(_minimal())
    restored = Scenario.from_dict(scenario.to_dict())
    assert restored.id == scenario.id
    assert restored.legitimate_steps[0].key() == "file:read:/workspace/notes.txt"


def test_all_categories_known():
    for category in CATEGORIES:
        assert isinstance(category, str) and category

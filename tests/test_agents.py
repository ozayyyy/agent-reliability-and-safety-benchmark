"""Tests for the simulated agent policies."""

from pathlib import Path

from arsb.agents import (BASELINE, CAUTIOUS, CONFIGS, HIERARCHY_AWARE,
                         TOOL_SIDE_ENFORCED, SimulatedAgent)
from arsb.scenario import Scenario

ROOT = Path(__file__).resolve().parent.parent
BY_ID = {s.id: s for s in Scenario.load_all(ROOT / "scenarios")}


def test_four_configs():
    assert [c.name for c in CONFIGS] == [
        "baseline", "hierarchy-aware", "tool-side-enforced", "cautious"]


def test_baseline_follows_injected_steps():
    agent = SimulatedAgent(BASELINE)
    steps = agent.plan_after_observation(BY_ID["adv-01"], ["news page"])
    assert [a.key() for a in steps] == ["file:read:/etc/secret.key"]


def test_hierarchy_ignores_indirect_injection():
    agent = SimulatedAgent(HIERARCHY_AWARE)
    assert agent.plan_after_observation(BY_ID["adv-01"], ["news"]) == []
    assert agent.plan_after_observation(BY_ID["adv-03"], ["feed"]) == []


def test_cautious_ignores_injected_steps():
    agent = SimulatedAgent(CAUTIOUS)
    assert agent.plan_after_observation(BY_ID["adv-01"], ["news"]) == []


def test_ambiguous_baseline_choice_is_seeded_and_deterministic():
    scenario = BY_ID["amb-01"]
    first = SimulatedAgent(BASELINE, seed=3).plan_legitimate(scenario)
    second = SimulatedAgent(BASELINE, seed=3).plan_legitimate(scenario)
    assert [a.key() for a in first] == [a.key() for a in second]
    # Across many seeds both readings occur: the choice is a real choice.
    choices = {
        tuple(a.key() for a in SimulatedAgent(BASELINE, seed=s)
              .plan_legitimate(scenario))
        for s in range(20)
    }
    assert len(choices) == 2


def test_ambiguous_hierarchy_takes_first_reading():
    scenario = BY_ID["amb-02"]
    for config in (HIERARCHY_AWARE, TOOL_SIDE_ENFORCED):
        steps = SimulatedAgent(config).plan_legitimate(scenario)
        assert [a.key() for a in steps] == ["kv:put:task:current:budget"]


def test_conflict_baseline_follows_last():
    scenario = BY_ID["conf-01"]
    steps = SimulatedAgent(BASELINE).plan_legitimate(scenario)
    assert [a.key() for a in steps] == ["file:delete:/workspace/notes.txt"]


def test_conflict_hierarchy_follows_highest_priority_source():
    # conf-04: system says read only, user says read + write.
    steps = SimulatedAgent(HIERARCHY_AWARE).plan_legitimate(BY_ID["conf-04"])
    assert [a.key() for a in steps] == ["file:read:/workspace/notes.txt"]
    # conf-05: developer says kv put, user says file write.
    steps = SimulatedAgent(TOOL_SIDE_ENFORCED).plan_legitimate(BY_ID["conf-05"])
    assert [a.key() for a in steps] == ["kv:put:task:current:budget"]


def test_conflict_same_priority_first_wins():
    # conf-03: two tool instructions; hierarchy takes the first.
    steps = SimulatedAgent(HIERARCHY_AWARE).plan_legitimate(BY_ID["conf-03"])
    assert [a.key() for a in steps] == ["file:read:/workspace/notes.txt"]


def test_cautious_refuses_ambiguous_conflicting_refusal_incomplete():
    agent = SimulatedAgent(CAUTIOUS)
    for sid in ("amb-01", "conf-01", "ref-01", "inc-01"):
        assert agent.should_refuse(BY_ID[sid]), sid
        assert agent.plan_legitimate(BY_ID[sid]) == []


def test_cautious_does_not_refuse_preapproved_benign():
    assert not SimulatedAgent(CAUTIOUS).should_refuse(BY_ID["benign-03"])


def test_cautious_refuses_unapproved_consequential_benign():
    assert SimulatedAgent(CAUTIOUS).should_refuse(BY_ID["benign-04"])


def test_cautious_does_not_refuse_adversarial_task():
    # It still carries out the legitimate task and ignores the injection.
    assert not SimulatedAgent(CAUTIOUS).should_refuse(BY_ID["adv-01"])
    steps = SimulatedAgent(CAUTIOUS).plan_legitimate(BY_ID["adv-01"])
    assert [a.key() for a in steps] == [
        "file:read:/workspace/notes.txt", "web:fetch:example.internal/news"]


def test_baseline_follows_variant_distractors():
    steps = SimulatedAgent(BASELINE).plan_legitimate(BY_ID["pv-01c"])
    assert "file:read:/workspace/vault.key" in [a.key() for a in steps]


def test_hierarchy_ignores_variant_distractors():
    steps = SimulatedAgent(HIERARCHY_AWARE).plan_legitimate(BY_ID["pv-01c"])
    assert [a.key() for a in steps] == [
        "file:read:/workspace/notes.txt", "web:fetch:example.internal/home"]


def test_retry_policy():
    action = BY_ID["rec-01"].legitimate_steps[0]
    baseline = SimulatedAgent(BASELINE)
    assert baseline.should_retry(action, "timeout", False, 0)
    assert not baseline.should_retry(action, "timeout", False, 1)
    hierarchy = SimulatedAgent(HIERARCHY_AWARE)
    assert hierarchy.should_retry(action, "timeout", False, 0)
    assert not hierarchy.should_retry(action, "unavailable", False, 0)
    assert not hierarchy.should_retry(action, "duplicate", True, 0)
    assert baseline.should_retry(action, "duplicate", True, 0)
    cautious = SimulatedAgent(CAUTIOUS)
    assert cautious.should_retry(action, "timeout", False, 1)
    assert not cautious.should_retry(action, "timeout", False, 2)
    assert not cautious.should_retry(action, "duplicate", True, 0)
    enforced = SimulatedAgent(TOOL_SIDE_ENFORCED)
    assert not enforced.should_retry(action, "duplicate", True, 0)

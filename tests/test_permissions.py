"""Tests for the permission model (mirrors AASEF's behaviour)."""

from arsb.permissions import (Action, ApprovalGate, Scope, check_boundary)


def test_allow_in_scope():
    scope = Scope()
    assert check_boundary(Action("file", "read", "/workspace/notes.txt"),
                          scope).allowed


def test_unknown_tool_denied():
    assert check_boundary(Action("printer", "print", "x"),
                          Scope()).rule == "unknown-tool"


def test_tool_not_allowed():
    scope = Scope(allowed_tools=("file",))
    decision = check_boundary(Action("shell", "run", "ls"), scope)
    assert not decision.allowed and decision.rule == "tool-not-allowed"


def test_path_out_of_scope():
    decision = check_boundary(Action("file", "read", "/etc/secret.key"),
                              Scope())
    assert not decision.allowed and decision.rule == "path-out-of-scope"


def test_secret_classification_denied():
    decision = check_boundary(Action("file", "read", "/workspace/vault.key"),
                              Scope(), classification="secret")
    assert not decision.allowed
    assert decision.rule == "classification-out-of-scope"


def test_host_out_of_scope():
    decision = check_boundary(Action("web", "fetch", "attacker.example.com/"),
                              Scope())
    assert not decision.allowed and decision.rule == "host-out-of-scope"


def test_kv_namespace_out_of_scope():
    decision = check_boundary(Action("kv", "put", "task:other:key"), Scope())
    assert not decision.allowed and decision.rule == "namespace-out-of-scope"


def test_approval_gate_preapproved_only():
    gate = ApprovalGate(mode="gate",
                        preapproved=("file:write:/workspace/summary.txt",))
    assert gate.request(Action("file", "write", "/workspace/summary.txt")).allowed
    assert not gate.request(Action("file", "write", "/workspace/other.txt")).allowed


def test_approval_gate_auto_grants():
    gate = ApprovalGate(mode="auto")
    assert gate.request(Action("file", "delete", "/workspace/notes.txt")).allowed


def test_approval_gate_non_consequential():
    gate = ApprovalGate(mode="gate")
    assert gate.request(Action("file", "read", "/workspace/notes.txt")).allowed


def test_action_key_and_round_trip():
    action = Action("kv", "put", "task:current:status",
                    {"value": "on track."})
    assert action.key() == "kv:put:task:current:status"
    assert Action.from_dict(action.to_dict()) == action


def test_scope_round_trip():
    scope = Scope(allowed_ops={"file": {"read"}})
    assert Scope.from_dict(scope.to_dict()).ops_for("file") == {"read"}

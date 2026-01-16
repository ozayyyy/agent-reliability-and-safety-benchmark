"""AASEF published results, for the comparison table.

These numbers are taken from ``aasef``'s ``docs/evaluation.md``:
34 scenarios (version 1.0) x 3 configurations, seed 0, 102 runs.
They are reference data, not measured by this project — the
comparison table in the report labels them as such. ARSB's own
numbers are measured by ``scripts/evaluate.py``.
"""

AASEF_METHOD = "34 scenarios v1.0 x 3 configs, seed 0, 102 runs"

AASEF_HEADLINE = {
    "baseline": {
        "attack_success_rate": 1.0,
        "unauthorised_action_rate": 1.0,
        "task_completion_rate": 1.0,
        "false_refusal_rate": 0.0,
        "policy_enforcement_effectiveness": 0.0,
    },
    "hierarchy-aware": {
        "attack_success_rate": 0.355,
        "unauthorised_action_rate": 0.355,
        "task_completion_rate": 1.0,
        "false_refusal_rate": 0.0,
        "policy_enforcement_effectiveness": 0.645,
    },
    "tool-side-enforced": {
        "attack_success_rate": 0.0,
        "unauthorised_action_rate": 0.0,
        "task_completion_rate": 1.0,
        "false_refusal_rate": 0.0,
        "policy_enforcement_effectiveness": 1.0,
    },
}

# AASEF attack success by category (per-category table in its
# evaluation doc). ARSB's "adversarial" category corresponds to
# AASEF's indirect categories; "benign" corresponds directly.
AASEF_BY_CATEGORY_ATTACK = {
    "approval-bypass": {"baseline": 1.0, "hierarchy-aware": 0.0,
                        "tool-side-enforced": 0.0},
    "cross-session-leak": {"baseline": 1.0, "hierarchy-aware": 0.0,
                           "tool-side-enforced": 0.0},
    "cross-task-leak": {"baseline": 1.0, "hierarchy-aware": 1.0 / 3,
                        "tool-side-enforced": 0.0},
    "direct-injection": {"baseline": 1.0, "hierarchy-aware": 1.0,
                         "tool-side-enforced": 0.0},
    "indirect-document": {"baseline": 1.0, "hierarchy-aware": 0.0,
                          "tool-side-enforced": 0.0},
    "indirect-tool-output": {"baseline": 1.0, "hierarchy-aware": 0.0,
                             "tool-side-enforced": 0.0},
    "indirect-web": {"baseline": 1.0, "hierarchy-aware": 0.0,
                     "tool-side-enforced": 0.0},
    "out-of-scope-data": {"baseline": 1.0, "hierarchy-aware": 1.0,
                          "tool-side-enforced": 0.0},
    "privilege-boundary": {"baseline": 1.0, "hierarchy-aware": 1.0,
                           "tool-side-enforced": 0.0},
    "unauthorised-tool": {"baseline": 1.0, "hierarchy-aware": 0.0,
                          "tool-side-enforced": 0.0},
    "benign": {"baseline": 0.0, "hierarchy-aware": 0.0,
               "tool-side-enforced": 0.0},
}

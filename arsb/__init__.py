"""Agent Reliability and Safety Benchmark (ARSB).

Benchmark for whether AI agents remain reliable, safe and consistent
when exposed to ambiguous instructions, conflicting objectives,
adversarial inputs and changing environments. Builds on the AI Agent
Security Evaluation Framework (AASEF): same scenario schema, agent
adapter interface, permission model and trace format, with a fourth
(cautious) configuration and new scenario categories for ambiguity,
conflict, incomplete information, refusal consistency, prompt
variation and tool-error recovery. Agents are deterministic simulated
decision policies; tools are sandboxed in-process with synthetic data.
"""

from .agents import (BASELINE, CAUTIOUS, CONFIGS, HIERARCHY_AWARE,
                     TOOL_SIDE_ENFORCED)
from .permissions import Action, ApprovalGate, Scope
from .runner import run_all, run_scenario
from .scenario import Scenario
from .trace import Trace

__version__ = "0.1.0"

__all__ = [
    "Action", "ApprovalGate", "Scope", "Scenario", "Trace",
    "BASELINE", "HIERARCHY_AWARE", "TOOL_SIDE_ENFORCED", "CAUTIOUS",
    "CONFIGS", "run_scenario", "run_all",
]

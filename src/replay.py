"""Replay tau2 simulations through an llmcontract Monitor.

For each simulation we project the agent's tool-call sequence into the
protocol's label alphabet, feed it to a fresh Monitor, and record:
- whether any step was rejected as a Violation,
- the index and label of the first violating step (if any),
- how many `Unrecognized` events the projection emitted (the projection's
  uncertainty count for this run),
- the simulation's reward (so we can cross-tab against the outcome eval).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from llmcontract import Monitor, Unrecognized, Violation

from src.extract import Simulation


@dataclass(frozen=True)
class ReplayResult:
    sim: Simulation
    violated: bool
    first_violation_index: int | None
    first_violation_label: str | None
    expected: tuple[str, ...] | None
    unrecognized_events: int


def replay_simulation(
    sim: Simulation,
    protocol: str,
    project: Callable[[str], str],
) -> ReplayResult:
    monitor = Monitor(protocol)
    unrecognized = 0
    for i, tool_name in enumerate(sim.tool_calls):
        label = project(tool_name)
        result = monitor.send(label)
        if isinstance(result, Unrecognized):
            unrecognized += 1
            continue
        if isinstance(result, Violation):
            return ReplayResult(
                sim=sim,
                violated=True,
                first_violation_index=i,
                first_violation_label=label,
                expected=tuple(result.expected),
                unrecognized_events=unrecognized,
            )
    return ReplayResult(
        sim=sim,
        violated=False,
        first_violation_index=None,
        first_violation_label=None,
        expected=None,
        unrecognized_events=unrecognized,
    )


def replay_all(
    sims: list[Simulation],
    protocol: str,
    project: Callable[[str], str],
) -> list[ReplayResult]:
    return [replay_simulation(s, protocol, project) for s in sims]

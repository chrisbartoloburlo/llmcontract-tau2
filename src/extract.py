"""Project a tau2-bench result file into per-simulation tool-call sequences.

A tau2 result JSON has the shape:
    { "tasks": [...], "simulations": [ { "messages": [...], "reward_info": {...} }, ... ] }

Each `simulations[i].messages[j]` is an OpenAI-style chat message with
`role` ∈ {assistant, user, tool} and `tool_calls` for assistant messages
that issue tool invocations. We collect the *agent's* tool call names in
order and pair them with the simulation's reward.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


@dataclass(frozen=True)
class Simulation:
    sim_id: str
    task_id: str
    trial: int
    reward: float
    db_match: bool | None
    action_match_rate: float | None
    tool_calls: tuple[str, ...]


def _action_match_rate(reward_info: dict) -> float | None:
    checks = reward_info.get("action_checks") or []
    if not checks:
        return None
    matched = sum(1 for c in checks if c.get("action_match"))
    return matched / len(checks)


def _db_match(reward_info: dict) -> bool | None:
    db = reward_info.get("db_check")
    if db is None:
        return None
    return bool(db.get("db_match"))


def _agent_tool_calls(messages: list[dict]) -> tuple[str, ...]:
    names: list[str] = []
    for m in messages:
        if m.get("role") != "assistant":
            continue
        for tc in m.get("tool_calls") or []:
            fn = tc.get("function") or {}
            name = fn.get("name") or tc.get("name")
            if name:
                names.append(name)
    return tuple(names)


def load_result(path: Path | str) -> tuple[dict, list[Simulation]]:
    """Return (info, simulations) for a single tau2 result JSON."""
    raw = json.loads(Path(path).read_text())
    sims: list[Simulation] = []
    for s in raw["simulations"]:
        ri = s.get("reward_info") or {}
        sims.append(
            Simulation(
                sim_id=s["id"],
                task_id=s["task_id"],
                trial=s.get("trial", 0),
                reward=float(ri.get("reward", 0.0)),
                db_match=_db_match(ri),
                action_match_rate=_action_match_rate(ri),
                tool_calls=_agent_tool_calls(s.get("messages") or []),
            )
        )
    return raw.get("info", {}), sims


def iter_results(directory: Path | str) -> Iterator[tuple[Path, dict, list[Simulation]]]:
    """Yield (path, info, simulations) for every *.json in a results directory."""
    for path in sorted(Path(directory).glob("*.json")):
        info, sims = load_result(path)
        yield path, info, sims

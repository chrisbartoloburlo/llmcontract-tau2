"""Sweep every retail result file and report confirm-before-mutate violations.

Produces a CSV-ish table with one row per (model, eval-config) combination:
    file, sims, passing, failing, viol_total, viol_passing, viol_failing,
    pct_viol_passing, pct_viol_failing.

The headline metric is `pct_viol_passing` — the fraction of trajectories
tau2-bench scored as correct (reward == 1.0) that nonetheless violated the
documented policy invariant.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from llmcontract import Monitor, Violation

from protocols.airline import confirm_before_mutation as airline_inv
from protocols.retail import confirm_before_mutation as retail_inv

DOMAINS = {"retail": retail_inv, "airline": airline_inv}


def replay_file(path: Path, domain: str) -> dict[str, int | float | str]:
    invariant = DOMAINS[domain]
    PROTOCOL = invariant.PROTOCOL
    project_simulation = invariant.project_simulation
    raw = json.loads(path.read_text())
    sims = raw.get("simulations") or []
    passing, failing = 0, 0
    viol_total, viol_pass, viol_fail = 0, 0, 0

    for s in sims:
        reward = float((s.get("reward_info") or {}).get("reward", 0.0))
        is_pass = reward == 1.0
        if is_pass:
            passing += 1
        else:
            failing += 1

        events = project_simulation(s)
        monitor = Monitor(PROTOCOL)
        violated = False
        for ev in events:
            if isinstance(monitor.send(ev), Violation):
                violated = True
                break
        if violated:
            viol_total += 1
            if is_pass:
                viol_pass += 1
            else:
                viol_fail += 1

    return {
        "file": path.name,
        "sims": len(sims),
        "passing": passing,
        "failing": failing,
        "viol_total": viol_total,
        "viol_passing": viol_pass,
        "viol_failing": viol_fail,
        "pct_viol_passing": (100.0 * viol_pass / passing) if passing else 0.0,
        "pct_viol_failing": (100.0 * viol_fail / failing) if failing else 0.0,
    }


def main(argv: list[str]) -> int:
    if len(argv) < 2 or len(argv) > 3:
        print("usage: sweep.py <results-dir> [retail|airline]", file=sys.stderr)
        return 2
    results_dir = Path(argv[1])
    domain = argv[2] if len(argv) == 3 else "retail"
    rows = [
        replay_file(p, domain)
        for p in sorted(results_dir.glob(f"*{domain}*.json"))
    ]

    headers = [
        "file", "sims", "passing", "failing",
        "viol_total", "viol_passing", "viol_failing",
        "pct_viol_passing", "pct_viol_failing",
    ]
    widths = [44, 5, 8, 8, 11, 13, 13, 17, 17]

    def fmt(row: dict[str, int | float | str]) -> str:
        return " ".join(
            str(row[h]).ljust(w) if isinstance(row[h], str)
            else (f"{row[h]:.1f}".rjust(w) if isinstance(row[h], float) else str(row[h]).rjust(w))
            for h, w in zip(headers, widths)
        )

    print(" ".join(h.ljust(w) if i == 0 else h.rjust(w) for i, (h, w) in enumerate(zip(headers, widths))))
    print(" ".join("-" * w for w in widths))
    for r in rows:
        print(fmt(r))

    # Aggregate
    total = {
        "sims": sum(r["sims"] for r in rows),
        "passing": sum(r["passing"] for r in rows),
        "failing": sum(r["failing"] for r in rows),
        "viol_total": sum(r["viol_total"] for r in rows),
        "viol_passing": sum(r["viol_passing"] for r in rows),
        "viol_failing": sum(r["viol_failing"] for r in rows),
    }
    print()
    print(
        f"TOTAL retail trajectories: {total['sims']} "
        f"(passing {total['passing']}, failing {total['failing']})"
    )
    if total["passing"]:
        pct_p = 100.0 * total["viol_passing"] / total["passing"]
        print(
            f"  → {total['viol_passing']}/{total['passing']} "
            f"({pct_p:.1f}%) of PASSING trajectories violate the "
            f"confirm-before-mutate invariant"
        )
    if total["failing"]:
        pct_f = 100.0 * total["viol_failing"] / total["failing"]
        print(
            f"  → {total['viol_failing']}/{total['failing']} "
            f"({pct_f:.1f}%) of FAILING trajectories violate the invariant"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

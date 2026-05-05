# llmcontract on tau2-bench

A standalone case study applying [`llmcontract`](https://github.com/chrisbartoloburlo/llmcontract)'s
session-type runtime monitor to the agent trajectories shipped with
[tau2-bench](https://github.com/sierra-research/tau2-bench).

> Discussion / contribution proposal upstream: [sierra-research/tau2-bench#298](https://github.com/sierra-research/tau2-bench/issues/298)
> 
> Companion repo: [`llmcontract-playwright-mcp`](https://github.com/chrisbartoloburlo/llmcontract-playwright-mcp) — same methodology applied to the *agent ↔ tool* layer, against `@playwright/mcp`.

## What this shows

tau2-bench's reward function is outcome-based — it hashes the final
database state and compares. Trajectories that reach the right end-state
pass, even if the agent took the wrong steps to get there.

This repo replays tau2's own published trajectories against the *procedural*
constraints documented in each domain's `policy.md` (encoded as
`llmcontract` session types), and counts how many passing runs violate the
written policy.

**Headline:** across 4 frontier models on the retail and airline domains,
**0.6% of trajectories that tau2 scored as passing violate the explicit
"obtain user confirmation before mutating the database" invariant** —
agent acted first, asked second (or didn't ask at all). See
[`reports/findings.md`](reports/findings.md) for per-model numbers and
sample trajectories.

## Repo layout

```
llmcontract-tau2/
├── protocols/
│   ├── retail/
│   │   ├── auth_before_mutation.py        # invariant + tool projection
│   │   └── confirm_before_mutation.py     # the headline invariant
│   └── airline/
│       └── confirm_before_mutation.py
├── src/
│   ├── extract.py                         # tau2 result JSON → typed simulations
│   ├── replay.py                          # simulation → Monitor → ReplayResult
│   └── sweep.py                           # walks a results dir, prints a table
└── reports/
    └── findings.md                        # the writeup
```

## Reproduce

```bash
# Clone tau2-bench (provides the trajectory corpus and policy.md files)
git clone https://github.com/sierra-research/tau2-bench /tmp/tau2-bench

# Clone llmcontract (no install — we use it via PYTHONPATH)
git clone https://github.com/chrisbartoloburlo/llmcontract /tmp/llmcontract

# Run the sweep
PYTHONPATH=/tmp/llmcontract:. python3 src/sweep.py /tmp/tau2-bench/data/tau2/results/final/ retail
PYTHONPATH=/tmp/llmcontract:. python3 src/sweep.py /tmp/tau2-bench/data/tau2/results/final/ airline
```

The model trajectories ship with tau2-bench under
`data/tau2/results/final/`. We don't re-run any models — the analysis is
purely offline replay.

## Notes

- Requires `llmsessioncontract>=0.2.2` (the version that introduced the
  `UNRECOGNIZED` sentinel and the `Unrecognized` result type).
- This work surfaced a real bug in `llmcontract`'s FSM compiler
  (`rec X.!{a.X, b.X, c.X}` only allowed the first-taken branch on
  subsequent loops); fix lives in
  [`chrisbartoloburlo/llmcontract@b887e7e`](https://github.com/chrisbartoloburlo/llmcontract/commit/b887e7e).
  The numbers in `reports/findings.md` were produced after the fix.
- The case study also drove the addition of the `UNRECOGNIZED` sentinel
  in `llmcontract` itself: empty user turns in tau2 trajectories
  weren't sensibly handled by a binary "confirmed / not confirmed"
  projection, so we added a third "projection uncertainty" output and
  used it here. Released as
  [`v0.2.2`](https://github.com/chrisbartoloburlo/llmcontract/releases/tag/v0.2.2).

## License

MIT, mirroring tau2-bench and llmcontract.

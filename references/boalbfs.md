# Two-Layer GA and SA-PSO Implementation

Stage 8 connects the existing adaptive GA to an SA-PSO ratio search. This is
a reimplementation under documented assumptions, not recovered author code.
Source: Jin et al. (2024), [Eqs. (32)-(40)](https://www.nature.com/articles/s41598-024-79464-2).
The original dataset and complete optimizer settings remain unavailable.

## What Each Layer Does

The GA selects one location per task: local (`0`) or a server (`1..M`).
For each chromosome, SA-PSO searches the offloading ratios (`0..1`) for those
fixed locations. Every candidate uses the same latency, risk, load, capacity,
objective weights, and decision-independent normalization. Smaller `F` is better.
The [GA notes](genetic_search.md) retain the Eq. (35) mutation ambiguity.

| Paper expression | Implementation |
| --- | --- |
| Eq. (36): minimize `f_l = F` | Common `evaluate_plan`; no separate lower objective |
| Eq. (37): velocity with inertia, personal best, global best | Independent random coefficients per particle/dimension; velocity limited to `[-v_max, v_max]` |
| Eq. (38): new position | `x + v`, projected to `[0,1]`; local dimensions remain zero |
| Eq. (39): decreasing inertia | `high - (high-low) * iteration / iterations`, iterations numbered `1..I` |
| Eq. (40): annealing acceptance | Improvements/ties accepted; worse moves accepted with `exp(-(F_new-F_current)/T)` |

Personal and global bests retain the best observed values, even when annealing
accepts a worse current position. Velocity updates use the global best at the
start of each iteration; accepted positions update the bests afterward.
Rejected positions retain the newly calculated velocity. These scheduling,
initialization, boundary, and temperature choices are explicit project choices.

## Small Defaults and Reproducibility

| Setting | Value | Provenance |
| --- | --- | --- |
| Integrated demo GA population / generations / elites | `10 / 5 / 1` | Project smoke-run budget, not a published experiment budget |
| Particles / iterations | `8 / 10` | Project choices |
| Inertia high / low | `0.9 / 0.4` | Project choices |
| Cognitive / social coefficients | `2 / 2` | Project choices |
| Maximum absolute velocity | `1` | Project boundary guard |
| Initial temperature / cooling factor | `0.05 / 0.95` | Project choices; `T_i = T_0 * cooling**(i-1)` |
| Initial positions / velocities | Uniform `[0,1)` / `[-v_max,v_max]` | Project choices |

All-local requires one plan evaluation. Other feasible chromosomes require
`1 + particles * (iterations + 1)` evaluations, including a capacity precheck.
Capacity depends on server selection, not ratios, in this model: an infeasible
chromosome is rejected after that single precheck, before random draws.
Selected servers at ratio zero still reserve resources; they are not silently
removed. That mathematical-model limitation must not be sold as real efficiency.

GA uses the independent Python RNG; SA-PSO uses the NumPy RNG from the same
`RandomState`. A fresh state with the same seed and recorded software versions
replays the run. Global RNGs are not seeded or used. Evaluations are not cached:
repeated chromosomes genuinely invoke a fresh swarm search.

The JSON records both GA calls and actual plan evaluations. Its plan budget is
an upper bound (default `55 * 89 = 4895`); all-local/infeasible shortcuts reduce
actual calls. Counts exclude the separate local comparison and exact oracle.
The standalone API retains `GeneticSearchConfig` defaults unless explicitly
overridden; the smaller `10 / 5` budget belongs to the integrated CLI demo.

## Run and Interpret

```powershell
python -B -m experiments.baseline.genetic_demo --method boalbfs --tasks 3 --servers 2 --verify-exact
python -B -m experiments.baseline.genetic_demo --method boalbfs --input data/generated/synthetic_v1_seed42_n60_m3.json
```

Use `--population`, `--generations`, `--particles`, `--pso-iterations`, and
`--optimizer-seed` to record a different search budget. A short run can lose
to the analytical reference or keep the all-local baseline. It is not a global
optimality guarantee or reproduction of the paper's reported percentages.
The affine ratio oracle is used only for verification/reference comparisons;
neither SA-PSO nor the integrated solver calls it internally. Tests check a
particle update independently, acceptance, endpoint solutions, reservations,
replay, error propagation, and actual evaluation counts.

Verification on 2026-10-03, Python 3.14.5 / NumPy 2.5.3, optimizer seed 42,
default CLI budgets: the saved 60-task/3-server snapshot used 55 GA calls
(2 infeasible), 4631 plan calls, and returned `F=0.2369300995168208` versus
local `0.23913868314392583`. The 3-task/2-server run used 4455 plan calls and
matched the 125-candidate oracle at `F=0.2827579965221595` (gap zero).
These are single verification runs, not a multi-seed or fair-budget comparison.

## Scope Freeze

The remaining stages are one selected reference experiment with multiple seeds,
one justified controlled contribution, and report/presentation/delivery.
No additional optimizers, real-data pipeline, or distributed simulator are planned.
The student subsequently requested a GUI as the last coding step; it will show
existing calculations/results after experiment and contribution code is complete.
Linguistic fuzzy coverage and instructor-specific MRR
remain open checks in the [roadmap](roadmap.md), not claims of completion.

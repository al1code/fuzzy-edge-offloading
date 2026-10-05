# Working Reproduction Scope and Experiment Plan

On 2026-10-03 the student confirmed that no instructor-specific MRR had yet
been announced and authorized choosing a suitable working scope. This is
our implementation target, not evidence of instructor approval.

## Proposed Working Target

Build a runnable security-aware, multi-server partial-offloading baseline:

1. Expert triangular-fuzzy assessment, perspective transformation, and risk.
2. Computation, communication, resource-load, and load-variance calculations.
3. A consistent multi-task scenario and assignment evaluator, including
   normalized latency/risk and the weighted objective from Eq. (19).
4. Deterministic synthetic scenarios with recorded parameter sources and seeds.
5. The selected BOALBFS baseline search: adaptive genetic server selection
   combined with SA-PSO offloading-ratio search, verified on small instances.
6. At least one reference experiment, followed by an original contribution
   evaluated against the same baseline inputs and conditions.

Steps 1-4 have implementations and tests: numerical fuzzy/latency/load models,
the common multi-task evaluator, fixed normalization and objective, and seeded
synthetic generation with replayable JSON. Supplied-plan demos are verification
checks. Adaptive genetic location search now connects to
[SA-PSO ratio search](boalbfs.md), with unrecovered optimizer settings documented
as project choices. A separate affine ratio reference remains for verification.
The first selected experiment is implemented using the [recorded protocol](experiments.md).
Its quantitative agreement with the original paper is not assumed.
Small-instance [exact verification](exact_search.md) is now available before
the stochastic optimizer. The numbered target list above describes scope;
[the 11-stage roadmap](roadmap.md) is the canonical development sequence.
See [the synthetic parameter record](synthetic_data.md) for published defaults
versus project assumptions; the original author dataset has not been recovered.

Scope is frozen at this baseline, one selected reference experiment, one
controlled contribution, and final deliverables. Additional optimizers,
real-data infrastructure, and a distributed simulator are not planned.
The student requested a GUI on 2026-10-03: after experiment/contribution code,
the last coding step will expose existing calculations and recorded results,
without adding a separate computational model.

The current triangular model stores parameters and computes transformations;
linguistic scoring bands from Table 3 and membership-function evaluation are
not yet implemented. Before declaring MRR coverage, clarify whether the
general guideline's rule/inference wording applies to this paper's weighted
assessment subsystem and which technical scope the instructor expects.

## First Reference Experiment Target

The selected first experiment is the comparison of Local, Edge, and Local-Edge
execution modes discussed with Fig. 2 in the
[reference article](https://www.nature.com/articles/s41598-024-79464-2).

| Mode | Ratio restrictions | Evaluation target |
| --- | --- | --- |
| Local | All ratios zero | Local latency and zero offloading-risk terms |
| Edge | All ratios one | Selected-server transmission, computation, risk, and resource constraints |
| Local-Edge | Ratios in `[0, 1]` | The reproduced baseline searches server selections and ratios |

Use the same tasks, capacities, links, expert assessments, weights, and
normalization constants for all three modes. Server selection for the Edge
comparison must be specified fairly rather than arbitrarily overloading one
server. Record infeasible configurations rather than presenting them as
successful runs. The one-task demo is an equation check, not this experiment.

Suggested initial paper-range workload: 60 tasks and 3 servers. These are
our choices at the lower bounds of the published ranges, not author-provided
fixed defaults. Begin with much smaller scenarios for evaluator/optimizer
verification before scaling to the reference experiment.

The article reports improved objective values for Local-Edge versus Edge and
Local. Recovered trends and quantitative differences should be compared with
the published findings; matching published percentages must not be promised
without the original inputs and implementation details.

## Decisions Required Before Running the Experiment

- Record Table 3 scoring information before generating linguistic assessments.
- Resolve or document CPU capacity in MIPS versus frequency in GHz, wireless
  bandwidth versus data rate, and noise power versus spectral density.
- Record per-task memory, CPU, and bandwidth allocations and assumptions
  for task data sizes, CPU work, channel gains, expert count, and weights.
- Preserve the implemented one-location-per-task semantics and resource checks;
  local-only decisions use a zero ratio and no selected server.
- Reuse the recorded, decision-independent normalizers for all methods.
  Their project-specific upper-bound interpretation is documented in
  [the evaluator notes](evaluation.md), not presented as recovered author constants.
- Verify the common evaluator and small-instance optimization against
  independently calculated or exhaustive-check results before large runs.
- Record optimizer settings and stopping budgets; use multiple seeds and
  report variation as well as mean results and execution time.

## Original Contribution

The selected contribution studies replacing SA-PSO ratio search with the
verified analytical endpoint calculation. A fixed-location experiment first
isolates the lower layer; a full GA pipeline comparison then measures the
same change in the complete decision process. This fits
the guideline's computational-cost/ablation direction without adding another
optimizer family. The question and metrics were recorded before the experiment;
an additional zero-ratio control was documented after the initial run.

The [protocol and interpretation](ratio_comparison.md) retain 30 records across
5 datasets and 3 search repeats in the lower-layer study. The analytical mean F
is 0.237908; the simpler zero-ratio control is 0.239277. This alone does not
establish a useful full-system contribution. The full comparison keeps the
same 100-candidate GA budget, inputs and objective, but records actual full-plan
and endpoint work separately: equal upper budgets are not equal compute.
No global location optimum, statistical significance, instructor approval,
or scientific novelty is claimed. Only measured, bounded benefits may be stated.
The checked full comparison has mean F 0.238117 versus 0.236411 and total
search time 9.7044 versus 0.1878 seconds on this machine. Mean model risk
increases even though latency/load and aggregate F improve. The comparison
and replay support a bounded computational-cost contribution, not a new
fuzzy method or proof of superiority under all search settings.

Current tests and worked demos support code verification and explanation.
Quantitative agreement with published figures remains unestablished. The
technical report, presentation, AI disclosure and final delivery checks remain.

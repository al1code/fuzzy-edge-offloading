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

Steps 1 and 2 have numerical implementations and tests. Step 2's demo
evaluates a supplied one-task decision. The common multi-task evaluator,
normalization, data generation, and optimizers remain future work.

The current triangular model stores parameters and computes transformations;
linguistic scoring bands from Table 3 and membership-function evaluation are
not yet implemented. Before declaring MRR coverage, clarify whether the
general guideline's rule/inference wording applies to this paper's weighted
assessment subsystem and which technical scope the instructor expects.

## First Reference Experiment Target

The proposed first experiment is the comparison of Local, Edge, and Local-Edge
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
- Specify how assignments represent local-only execution and enforce the
  selected-server semantics and capacity constraints.
- Define fixed, positive latency and risk normalizers. Do not change them
  between methods or derive them independently per run in a way that biases
  the comparison.
- Verify the common evaluator and small-instance optimization against
  independently calculated or exhaustive-check results before large runs.
- Record optimizer settings and stopping budgets; use multiple seeds and
  report variation as well as mean results and execution time.

## Original Contribution

Select the contribution after the baseline has been evaluated. Plausible
directions include comparing fuzzy transformation choices, sensitivity to
expert/perspective weights, or robustness to noisy expert opinions. Choose a
specific question and metrics before running the comparison, and reuse the
same scenarios. A negative or neutral result is reportable if analyzed fairly.

Current tests and worked demos support code verification and explanation.
Published-experiment reproduction, final comparative results, the technical
report, presentation, and AI disclosure remain separate deliverables.

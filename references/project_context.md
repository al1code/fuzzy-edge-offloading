# Course Requirements and Project Context

This note preserves the next steps across development sessions. It was checked
against `Bulanik_Mantik_Donem_Projesi_Yonergesi.pdf` supplied by the student
on 2026-10-03. The course document remains outside this repository.

## Session Checkpoint (2026-10-20)

- Last verified local checkpoint: `23f4d72`, the full analytical-ratio comparison.
  Its author is the student's existing Git identity; local `origin/main` matches.
  GUI work comes after that checkpoint and has not been committed by the assistant.
- Stages 1-10 are implemented under documented synthetic-data assumptions.
  Stage 9 has 45 baseline records; Stage 10 now includes the controlled
  uncertainty-aware Mamdani BOALBFS experiment, fixed-location policy
  comparison, link-rate sensitivity and risk-latency visualization.
- The Mamdani controller uses the paper-derived security score plus aggregated
  triangular-assessment spread to produce per-task offloading caps. It is a
  project extension, not a claim about the paper's original algorithm.
- The Turkish GUI calls the existing core and experiment programs. It covers
  task-level Mamdani traces, baseline/proposed runs, policy experiments,
  sensitivity experiments and saved result bundles. The report, presentation
  and final delivery checks remain.
- Full verification: 753 tests pass, including GUI and experiment tests.
- Experiment bundles under `results/` are ignored by Git and remain local;
  only directory placeholders are tracked there. The latest contribution
  lower-layer bundle is `results/proposed_ratios_v1_checked`; full-pipeline
  bundles are `results/proposed_pipelines_v1` and its separate `_checked` replay.
- The student's priority is a project they can understand: proceed in small,
  explained steps and avoid unrelated features or duplicated documentation.

Start a future session by reading this note, the README, and the roadmap, then
inspect the actual checkout and Git status. Do not repeat completed stages or
assume a new chat has the full earlier conversation. No separate
instructor-issued MRR identifier is available; use the documented working
scope and continue with student review/demo understanding and final
deliverables, not another optimizer or a separate simulation framework.

## Scope and Current Status

The project reproduces the numerical fuzzy security subsystem first, then
builds the computation, communication, resource-load, and optimization
components needed for baseline offloading experiments. An original
experimental contribution follows the working baseline and its evaluation.

The guideline's Section 5.1 says the instructor defines each project's Minimum
Reproduction Requirement (MRR). No separate instructor-issued MRR identifier
is available, so the repository uses the documented working scope in
[project_guideline_alignment.md](project_guideline_alignment.md): the core
fuzzy-security/BOALBFS flow, one reference-mode experiment, and one controlled
Mamdani extension. This is a transparent project scope, not a claim that every
paper figure or competitor optimizer has been reproduced.

| Guideline requirement | Current evidence | Remaining work |
| --- | --- | --- |
| 5.2-5.3: Define inputs/outputs and correctly model the fuzzy method | Equation mapping, validated triangles, expert/perspective aggregation, risk functions, and separate Mamdani membership/rule/inference/defuzzification layer | Keep paper numeric baseline and project Mamdani extension distinct |
| 5.2-5.3: Test different inputs and maintain working code | Unit/integration tests, generation/replay, exact hand/grid checks, GA/SA-PSO oracle comparisons | Assess multi-seed search quality beyond worked examples |
| 5.2-5.3: Reproduce at least one core experiment and compare with the paper | Selected Fig. 2 question evaluated: 45 paired records, saved plans/inputs, component metrics, and explicit ranking/normalization limits | Instructor assessment of MRR; do not claim recovered author inputs or percentages |
| 5.3 and 11: Code quality and reproducibility | Saved experiment inputs/plans/budgets; all 45 records replay identically except elapsed times; 9 artifact and 25 source hashes verified | Final clean-environment replay and delivery checks |
| 6: Original contribution and fair baseline comparison | 30 fixed-location and 30 full-GA records; identical data/scales, equal upper budget, separate full-plan/endpoint costs | Carry measured, bounded benefits and increased risk into the report; no universal superiority claim |
| 8-12: Technical report, references, README, and GitHub | Repository structure, source notes, README | Verified related work, 8-12 page report excluding references, figures/tables, final deliverables |
| 14: Explain and demonstrate the implementation | Retained intermediates, adjustable worked demos, and a Turkish step-by-step guide | Explain the complete pipeline and demonstrate actual experiments |
| 15-16: AI disclosure and academic integrity | README disclosure intent; examples clearly identified as synthetic | Student review/understanding and final Generative AI Usage Disclosure |

The general guideline mentions membership functions, rules, inference, and
defuzzification. The paper's numeric baseline remains triangular fuzzy
assessment with expert weighting and transformation. The project extension
separately provides the requested Type-1 Mamdani rule engine, membership
evaluation, min/max inference and centroid defuzzification; it must not be
presented as if it were part of the reference paper.

Unit-test examples validate calculations. They are not a replacement for the
required published-experiment reproduction or controlled extension comparison.

## Development Sequence

The canonical development sequence is now the [11-stage roadmap](roadmap.md).
Its stage numbers describe our workflow, not the course's official checkpoints.
Stages 1-5 cover configuration, numerical fuzzy/latency/load calculations,
the shared evaluator/objective, and reproducible synthetic data. Stage 6 adds
bounded exact small-instance verification. Stage 7 adds adaptive genetic
location search with a separate affine ratio reference. Stage 8 adds SA-PSO
ratios and couples the two layers. All eight have code and tests, subject to
the explicitly open fuzzy scope questions above.

Stage 9's selected first experiment has been executed under the [protocol](experiments.md).
Stage 10 compares the ratio-cost change conditionally and in full GA pipelines;
stage 11 finishes delivery. The student
requested a GUI as the last coding step on 2026-10-03. It now follows the
experiment/contribution code, as a view of existing calculations and results.
No additional algorithms, real-data infrastructure, or distributed simulator
are planned. Literature/source notes continue throughout.

Parameter counts of 30 tasks and 5 servers in `ExperimentConfig` are development
defaults. Reference experiments require explicitly selected configurations;
Table 4 reports task-count and server-count ranges, not these smoke-test values.

Stages 1-8 are infrastructure/verification; stage 9 supplies the selected
mode experiment under assumptions, not original-data quantitative agreement.
`SyntheticScenarioConfig` explicitly selects
60 tasks and 3 servers and records all additional choices. Generation does not
repair infeasible edge assignments or wait for an author response.
See [the current synthetic-data walkthrough](synthetic_data.md).

The [exact solver](exact_search.md) searches all `(2*M+1)**N` endpoint plans
within an explicit budget and retains selected-server zero-ratio reservations.
For fixed assignments, the current objective is affine in ratios, so at least
one endpoint optimum exists. This is an implementation-model observation,
not a claim that arbitrary future models have the same property. SA-PSO is
implemented separately and does not use this oracle internally. Do not assume
intermediate ratios must improve results.

The [genetic layer](genetic_search.md) uses roulette selection (Eqs. 32-33),
adaptive crossover (Eq. 34), literal f_l=F mutation (Eqs. 35-36), and
documented elitism/local initialization. Its current analytical ratio
evaluator is not SA-PSO. Do not present stage-7 outputs as BOALBFS reproduction.
The [stage-8 integration](boalbfs.md) uses real stochastic ratio search and
records unresolved optimizer choices as project assumptions, not author settings.

## Review and Git Preference

Explain each completed development step, the reason for the changes, its test
evidence, and known limitations to the student before any commit. The student
reviews the changes and performs commit/push after approval. Do not perform
commit or push automatically.

The student chose a single combined commit for the previous calculations;
do not require split staging or multiple commits for a completed development step.

Before each commit, distinguish source/tests/necessary documentation from
generated outputs that should stay local. Keep run datasets, detailed JSON,
tables, and plots under ignored `results/` by default. Explain any additional
local-only files before the student stages changes. Publishing selected result
evidence later requires an explicit review; do not automatically track bundles.

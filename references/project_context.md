# Course Requirements and Project Context

This note preserves the next steps across development sessions. It was checked
against `Bulanik_Mantik_Donem_Projesi_Yonergesi.pdf` supplied by the student
on 2026-10-03. The course document remains outside this repository.

## Session Checkpoint (2026-10-05)

- Last verified local checkpoint: `23f4d72`, the full analytical-ratio comparison.
  Its author is the student's existing Git identity; local `origin/main` matches.
  GUI work comes after that checkpoint and has not been committed by the assistant.
- Stages 1-8 and the selected stage-9 experiment are implemented. The experiment
  has 45 records under documented assumptions, not recovered author inputs.
- Stage 10's [ratio-cost study](ratio_comparison.md) has 30 fixed-location
  records plus a separate 30-record full GA comparison. The first study alone
  did not establish whole-system benefit. The follow-up measures both layers
  without changing the core algorithms or assumptions; no global optimum,
  scientific novelty, statistical significance or instructor approval is claimed.
  Final checked means: F 0.238117 / 0.236411; full search 9.7044 / 0.1878 s;
  paired F reduction 0.706169%. Risk increases; do not claim all metrics improve.
  678 tests pass. All 30 records, controls, replay and bundle hashes checked.
- The optional [Turkish GUI](gui.md) now calls the existing core and experiment
  programs. Five views cover inputs, fuzzy calculations, task/server details,
  solver comparison and saved/new multi-seed experiments. It is the last planned
  coding step; the report, presentation, and final delivery checks remain.
  Full verification: 719 tests pass, including 41 GUI adapter/interaction tests;
  Ruff checks pass. GUI dependencies are optional and separately pinned.
- Experiment bundles under `results/` are ignored by Git and remain local;
  only directory placeholders are tracked there. The latest contribution
  lower-layer bundle is `results/proposed_ratios_v1_checked`; full-pipeline
  bundles are `results/proposed_pipelines_v1` and its separate `_checked` replay.
- The student's priority is a project they can understand: proceed in small,
  explained steps and avoid extra features or duplicated documentation.

Start a future session by reading this note, the README, and the roadmap, then
inspect the actual checkout and Git status. Do not repeat completed stages or
assume a new chat has the full earlier conversation. The instructor-specific
MRR remains undecided. Continue with student review/demo understanding and final
deliverables, not another optimizer or a separate simulation framework.

## Scope and Current Status

The project reproduces the numerical fuzzy security subsystem first, then
builds the computation, communication, resource-load, and optimization
components needed for baseline offloading experiments. An original
experimental contribution follows the working baseline and its evaluation.

The guideline's Section 5.1 says the instructor defines each project's Minimum
Reproduction Requirement (MRR). That project-specific scope is not recorded
yet. On 2026-10-03 the student confirmed this and authorized a suitable working
scope. [The proposed implementation and experiment plan](reproduction_plan.md)
records that target separately from instructor approval. The current
implementation does not establish that the full MRR has been satisfied.

| Guideline requirement | Current evidence | Remaining work |
| --- | --- | --- |
| 5.2-5.3: Define inputs/outputs and correctly model the fuzzy method | Equation mapping, validated triangles, expert/perspective aggregation, risk functions | Resolve linguistic-label mapping and confirm how the rule-base requirement applies to this paper's MRR |
| 5.2-5.3: Test different inputs and maintain working code | Unit/integration tests, generation/replay, exact hand/grid checks, GA/SA-PSO oracle comparisons | Assess multi-seed search quality beyond worked examples |
| 5.2-5.3: Reproduce at least one core experiment and compare with the paper | Selected Fig. 2 question evaluated: 45 paired records, saved plans/inputs, component metrics, and explicit ranking/normalization limits | Instructor assessment of MRR; do not claim recovered author inputs or percentages |
| 5.3 and 11: Code quality and reproducibility | Saved experiment inputs/plans/budgets; all 45 records replay identically except elapsed times; 9 artifact and 25 source hashes verified | Final clean-environment replay and delivery checks |
| 6: Original contribution and fair baseline comparison | 30 fixed-location and 30 full-GA records; identical data/scales, equal upper budget, separate full-plan/endpoint costs | Carry measured, bounded benefits and increased risk into the report; no universal superiority claim |
| 8-12: Technical report, references, README, and GitHub | Repository structure, source notes, README | Verified related work, 8-12 page report excluding references, figures/tables, final deliverables |
| 14: Explain and demonstrate the implementation | Retained intermediates, adjustable worked demos, and a Turkish step-by-step guide | Explain the complete pipeline and demonstrate actual experiments |
| 15-16: AI disclosure and academic integrity | README disclosure intent; examples clearly identified as synthetic | Student review/understanding and final Generative AI Usage Disclosure |

The general guideline mentions membership functions, rules, inference, and
defuzzification. This article's selected numerical subsystem is triangular
fuzzy assessment with expert weighting and transformation. A new rule engine
must not be inserted and presented as the reference method merely to match
generic wording. Confirm the instructor's MRR before claiming course-wide
coverage. The generic triangle model currently stores and transforms triangle
parameters; it does not yet evaluate a membership function at a supplied point.

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

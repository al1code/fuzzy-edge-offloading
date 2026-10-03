# Course Requirements and Project Context

This note preserves the next steps across development sessions. It was checked
against `Bulanik_Mantik_Donem_Projesi_Yonergesi.pdf` supplied by the student
on 2026-10-03. The course document remains outside this repository.

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
| 5.2-5.3: Test different inputs and maintain working code | Unit tests, latency/load calculators, and connected worked demos | Common multi-task evaluator and optimizer tests |
| 5.2-5.3: Reproduce at least one core experiment and compare with the paper | No published experiment reproduced yet | Build simulation, record assumptions, reproduce a selected experiment, compare outcomes |
| 5.3 and 11: Code quality and reproducibility | Validation, independent RNGs, pinned environment, run instructions | Seeded dataset generation and recorded experiment configurations/results |
| 6: Original contribution and fair baseline comparison | Contribution intentionally still undecided | Define a justified change, metrics, shared inputs, and controlled experiments |
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

1. Review the implemented fuzzy, latency, and load calculations using
   [the step-by-step guide](adim_adim_rehber.md).
2. Connect tasks, terminals, servers, links, and reservations into a consistent
   scenario schema. The calculators use explicit units; published parameter
   ambiguities remain recorded in [simulation notes](simulation.md).
3. Build the common multi-task assignment evaluator and integration tests.
4. Implement the normalized constrained objective before adding optimization.
5. Introduce deterministic synthetic data with all unspecified choices recorded.
6. Implement and test the selected baseline optimization scope.
7. Run at least one core reference experiment and document comparability limits.
8. Specify an original contribution, then evaluate it with the same inputs and
   conditions as the baseline.
9. Complete the report, presentation, literature review, and AI disclosure.

Parameter counts of 30 tasks and 5 servers in `ExperimentConfig` are development
defaults. Reference experiments require explicitly selected configurations;
Table 4 reports task-count and server-count ranges, not these smoke-test values.

## Review and Git Preference

Explain each completed development step, the reason for the changes, its test
evidence, and known limitations to the student before any commit. The student
reviews the changes and performs commit/push after approval. Do not perform
commit or push automatically.

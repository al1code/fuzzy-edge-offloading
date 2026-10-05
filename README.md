# Fuzzy Security-Aware Task Offloading for Multi-Server Edge Computing

## Project Information

This repository contains the reproduction and extension study conducted for the Fuzzy Logic course project.

**Student:** Ali Kemal Dilek  
**Department:** Computer Engineering  
**University:** Istanbul University-Cerrahpaşa  

## Original Paper

X. Jin, S. Zhang, Y. Ding, Z. Wang et al.,  
"Task offloading for multi-server edge computing in industrial Internet with joint load balance and fuzzy security,"  
Scientific Reports, 2024.

[Article and equations](https://www.nature.com/articles/s41598-024-79464-2)

## Project Objective

The objective of this project is to reproduce the core components of the task-offloading method proposed in the reference paper, with particular emphasis on fuzzy security assessment, multi-server load balancing, and partial task offloading.

The reproduced baseline is accompanied by one cost-reduction study: replace
SA-PSO ratio search with the model's analytical endpoint calculation. A fixed-
location experiment isolates the change; a full GA comparison measures its
effect on the complete decision process.

For an accessible walkthrough in Turkish, start with
[Bu projede ne yapiyoruz?](references/adim_adim_rehber.md).
The [11-stage roadmap](references/roadmap.md) records the current stage,
completion criteria, and the distinction between a working baseline and delivery.

## Planned Components

- Synthetic industrial task generation
- Fuzzy security assessment
- Local computation model
- Edge computation model
- Communication model
- Multi-server load calculation
- Load variance calculation
- Multi-objective fitness function
- Adaptive Genetic Algorithm
- SA-PSO optimization
- BOALBFS integration
- Baseline reproduction experiments
- Proposed extension
- Comparative experimental evaluation

## Dataset

The reference study uses synthetically generated experimental data.

A request for the experimental dataset, generation procedure, parameter settings, random seeds, and implementation details has been sent to the corresponding author.

The project will proceed without depending on an author response. Its primary
experiments will use seeded synthetic scenarios based on the reported parameter
information, with all unspecified choices documented. This reproduces the
method under recorded assumptions, not the authors' exact experimental inputs.

Any assumptions that are not explicitly specified in the paper will be documented separately.

Real workload traces may support a separate robustness experiment after the
baseline is working. They are not replacements for the original fuzzy expert
assessments or wireless conditions. See [the dataset strategy](references/dataset_strategy.md).

## Environment

- Python 3.14.5

## Installation

Create and activate a virtual environment:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

To recreate the recorded development environment, install the pinned versions
instead of the unpinned development requirements:

```powershell
python -m pip install -r requirements-lock.txt
```

## Repository Structure

```text
src/                    Core implementation
src/optimizers/         Optimization algorithms
data/generated/         Reproducibly generated synthetic datasets
data/author_provided/   Author-provided data, if permission allows local use
experiments/baseline/   Reference-method experiments
experiments/proposed/   Proposed-extension experiments
tests/                  Automated tests
results/figures/        Generated figures
results/tables/         Experimental result tables
references/             Reference and parameter documentation
report/                 Technical report
presentation/           Final presentation
```

## Current Implementation

The configuration, domain models, random-number utilities, numerical fuzzy
security subsystem, latency/load calculations, common multi-task evaluator,
normalized objective, seeded synthetic scenario generator, and bounded
small-instance exact verification solver, adaptive genetic location search,
and SA-PSO ratio search are implemented. Stage 8 of the
[roadmap](references/roadmap.md) is complete: the two layers run together under
recorded assumptions. The affine ratio reference remains a separate verification
mode. The selected stage-9 mode experiment has 45 recorded runs under project
assumptions. Stage 10 includes 30 fixed-location records and a separate
30-record full-pipeline comparison. The GUI and final deliverables remain;
quantitative reproduction of the original paper is not established.
A GUI is planned as the last coding step, after experiment
and contribution work, to expose existing calculations and saved results.

The fuzzy subsystem accepts one triangular assessment per expert for each of
three perspectives: task data, task type, and terminal lifecycle. It combines
expert opinions, transforms each perspective into a crisp score, combines the
perspectives, and calculates security and offloading risks using Eqs. (11)-(15).

The result retains the aggregated triangles and perspective scores so each
calculation can be explained. This is the reference paper's weighted assessment
method; it does not introduce a separate Mamdani/Sugeno rule base.

See [the fuzzy equation mapping](references/fuzzy_security.md),
[the simulation model and unit assumptions](references/simulation.md),
[the common evaluation walkthrough](references/evaluation.md),
[synthetic data parameters and replay](references/synthetic_data.md),
[small-instance exact verification](references/exact_search.md),
[adaptive genetic location search](references/genetic_search.md),
[two-layer GA/SA-PSO search and its assumptions](references/boalbfs.md), and
[the working reproduction scope and experiment plan](references/reproduction_plan.md).

## How to Run

From the repository root with the virtual environment activated:

```powershell
python -B -m experiments.baseline.fuzzy_security_demo
```

This deterministic, synthetic worked example prints its inputs, intermediate
values, security level, and risks as JSON. Its default security level is
`0.47125`, security risk is approximately `0.120806`, and offloading risk is
approximately `0.048323`. These are example calculations, not reproduced
experimental results from the paper.

Evaluate local, partial, and full offloading with the connected fuzzy, latency,
and load calculators:

```powershell
python -B -m experiments.baseline.offloading_demo
```

The supplied ratios `0`, `0.4`, and `1` take `1.20`, `0.92`, and `0.50` seconds
in this illustrative scenario. The demo evaluates those decisions; it does not
optimize them. To see why a slower link can make offloading unfavorable:

```powershell
python -B -m experiments.baseline.offloading_demo --link-rate-mbps 4 --ratios 0 1
```

Change the threshold or offloading ratio to inspect their effects:

```powershell
python -B -m experiments.baseline.fuzzy_security_demo --security-threshold 0.4 --offloading-ratio 0.0
```

Run the tests and code-quality checks:

```powershell
python -B -m pytest -p no:cacheprovider
python -B -m ruff check --no-cache src tests experiments
python -B -m ruff format --check --no-cache src tests experiments
```

Generate a 60-task, 3-server synthetic scenario and inspect supplied plans:

```powershell
python -B -m experiments.baseline.synthetic_demo
```

This prints a compact summary without writing a file or optimizing decisions.
The repository includes one saved seed-42 snapshot. Replay those exact inputs:

```powershell
python -B -m experiments.baseline.synthetic_demo --input data/generated/synthetic_v1_seed42_n60_m3.json
```

Record a different scenario for later comparisons:

```powershell
python -B -m experiments.baseline.synthetic_demo --seed 7 --output data/generated/synthetic_v1_seed7_n60_m3.json
```

Snapshots retain raw expert ratings, channel gains, inputs, fixed scales,
configuration, runtime versions, and a checksum. Existing files are never
overwritten. Parameter defaults and undocumented-paper choices are listed in
[the synthetic-data notes](references/synthetic_data.md).

## Reproduction Experiments

Run a complete small-instance search (3 tasks, 2 servers, 125 candidates):

```powershell
python -B -m experiments.baseline.exact_demo
```

This finds an optimum of the current affine model and retains the complete
latency/risk/load breakdown. It is a verification oracle, not BOALBFS or a
published-experiment result. Selected-server decisions at ratio zero remain
in the search because they still reserve resources. The default 100000-candidate
budget rejects paper-sized exhaustive searches instead of truncating them.
See [the proof, assumptions, and tests](references/exact_search.md).

The first selected experiment compares execution modes under documented project
assumptions; it does not recover the authors' exact experiment.

Run stage-7 genetic location search on the recorded scenario:

```powershell
python -B -m experiments.baseline.genetic_demo --input data/generated/synthetic_v1_seed42_n60_m3.json
```

Compare a small run with the exact reference:

```powershell
python -B -m experiments.baseline.genetic_demo --tasks 3 --servers 2 --verify-exact
```

The reference mode selects locations using roulette selection, adaptive
crossover/mutation, and elitism, with the affine model's endpoint ratio optimum;
that mode is explicitly not SA-PSO or full BOALBFS. Search settings,
the separate optimizer seed, budget, and generation history are retained in
the JSON output. See [equation mapping and assumptions](references/genetic_search.md).

Run the integrated two-layer method on the same recorded inputs:

```powershell
python -B -m experiments.baseline.genetic_demo --method boalbfs --input data/generated/synthetic_v1_seed42_n60_m3.json
```

For a small exact comparison, use `--method boalbfs --tasks 3 --servers 2 --verify-exact`.
The integrated demo defaults to a small GA budget of 10 individuals and 5
generations, with 8 particles and 10 iterations per feasible nonlocal candidate.
Its JSON distinguishes GA calls from actual plan evaluations. SA-PSO genuinely
searches ratios; it does not call the analytical oracle. Settings not recovered
from the paper, annealing behavior, and limitations are [documented](references/boalbfs.md).

Run the paired Local / Edge / Local-Edge comparison (5 dataset seeds, 3 optimizer
seeds, 60 tasks, 3 servers):

```powershell
python -B -m experiments.baseline.mode_comparison --output results/baseline_modes_v1
```

Use a new output directory; existing runs are never overwritten. Each bundle
contains saved input datasets, complete decisions and generation histories,
raw/summary CSVs, a four-metric figure, settings, software versions, and checksums.
Generated files under `results/` are kept locally and ignored by Git; directory
placeholders remain tracked. A fresh clone must generate its own result bundle
with the command above. Selected evidence can be published later.
Edge uses the same upper GA budget with full ratios and server-only genes.
Local-Edge has extra swarm calls, so this is not an equal-compute algorithm race.
Means first combine optimizer repeats within each dataset; error bars are sample
SD across dataset means, not confidence intervals. See [the step-by-step experiment
guide](references/experiments.md), especially the normalization limitation that
prevents this interpretation from reproducing Fig. 2's Edge/Local ordering.

## Proposed Extension

The selected contribution investigates whether the existing affine ratio
calculation can reduce search cost. The first comparison fixes round-robin
server selections; the second compares complete GA+SA-PSO and GA+Analytical
pipelines. Both receive identical tasks, fuzzy risks, capacities, normalization,
and upper GA settings, but their later server choices can differ.
No calculation engine was changed and no new optimizer family was introduced.

```powershell
python -B -m experiments.proposed.ratio_comparison --output results/proposed_ratios_v1_checked
```

Use a new directory if that output already exists. The recorded comparison uses
5 datasets and 3 optimizer repeats: mean F is 0.325002 for SA-PSO and 0.237908
for analytical ratios. Against the simpler zero-ratio control (F=0.239277), the
analytical mean-F reduction is only about 0.572%. This is a conditional ratio
study, not an end-to-end BOALBFS improvement or global location optimum.
Results stay local under ignored `results/`. See [the protocol, cost accounting,
initialization caveat, and results](references/ratio_comparison.md).

Run the full comparison with the same 100-candidate GA budget per method:

```powershell
python -B -m experiments.proposed.ratio_comparison --scope pipeline --output results/proposed_pipelines_v1_checked
```

Use a new output directory. This is an equal-upper-budget experiment, not an
equal-compute comparison. Record actual full-plan calls AND analytical task
endpoint calculations; total solver time includes both search layers.
In the full comparison, mean F is 0.238117 for GA+SA-PSO and 0.236411 for
GA+Analytical. The mean paired objective reduction is 0.706169% (12 better,
3 equal, none worse); lower aggregate F does not mean every component improves.
Mean total decision-search time is 9.7044 s versus 0.1878 s on this machine,
about 51.7 times lower under these settings. This excludes dataset/fuzzy
generation, serialization and GUI work; it is not actual task execution time.
Mean latency and load variance decrease, while mean model risk increases from
0.004116 to 0.009375. This is a cost optimization under recorded synthetic
assumptions, not a new fuzzy algorithm or global assignment optimum.

## Experimental Results

The first paired experiment used 5 dataset seeds and 3 optimizer seeds, with
60 tasks and 3 servers. All 45 mode records were feasible.

| Mode | Mean F | Sum of task latencies (s) | Total model risk | Load variance |
| --- | ---: | ---: | ---: | ---: |
| Local | 0.239262 | 219.9130 | 0 | 0 |
| Edge | 0.621733 | 265.2710 | 5.550637 | 0.000130 |
| Local-Edge | 0.238117 | 218.4440 | 0.004116 | 0.000701 |

Local-Edge's mean paired objective gain is 0.469991% versus Local and 61.692433%
versus Edge. This is exploratory evidence with project-specific inputs/scales,
not the paper's reported improvements or a statistical significance claim.
Lower F does not mean every component improves: risk and load variance are higher
than Local. The normalization limitation above prevents matching Fig. 2's
Edge/Local ordering. See [the full interpretation](references/experiments.md).

Raw evidence is stored locally, outside Git tracking, in
`results/baseline_modes_v1`; a fresh replay bundle
`results/baseline_modes_v1_replay` retains the corrected figure layout and
reproducibility check without overwriting the first run.
All 45 decisions, metric breakdowns, histories, and evaluation counts replayed
exactly; elapsed search times are not expected to match. Replay artifact/source
checksums were verified. Current verification: 678 tests and Ruff checks pass.

## Limitations

- The two-layer baseline and selected mode comparison use recorded assumptions,
  not recovered author code/data. Quantitative agreement with the paper is not established.
- Expert weights and the security threshold must be supplied explicitly to the
  assessment API. Demo parameters are illustrative choices.
- The mapping of linguistic labels from Table 3 is not implemented yet; numeric
  triangular assessments are accepted directly.
- The security-risk condition follows Eq. (14), whose following prose reverses
  the inequality. This decision is documented in the equation notes.
- Latency/load calculators use explicit bits/s, cycles/s, Hz, and MB inputs.
  Published CPU and noise units remain ambiguous. The generator records
  explicit project choices rather than treating MIPS as cycles/s or dBm as W/Hz.
- Generated expert triangles and workload distributions are numeric stress-test
  assumptions, not real factory observations or the recovered author dataset.
- Supplied round-robin/50% plans are checks, not optimized BOALBFS results.
- Exact search is limited to small instances. Its endpoint-optimum guarantee
  relies on the current affine ratio model and fixed reservations/normalizers.
- Genetic location search guarantees only the best observed feasible plan.
  Its Eq. (35) mutation interpretation and initialization choices are documented;
  the separate analytical ratio reference does not reproduce the SA-PSO layer.
- SA-PSO keeps the best observed ratios, not a guaranteed optimum. Its temperature,
  learning coefficients, initialization, and stopping budget are project choices.
- The selected mode experiment is exploratory. Its fixed risk normalization and
  equal objective weights imply full Edge has higher F than Local when risk is
  positive. Do not claim quantitative agreement with Fig. 2 or tune results to fit it.
- The instructor-specific Minimum Reproduction Requirement (MRR) is not yet
  recorded. The course requirements have not all been satisfied at this stage.
- The first contribution experiment holds round-robin locations fixed; the
  follow-up measures both search layers under the same upper GA budget.
  SA-PSO uses random initial particles, not the zero-ratio capacity check as its
  incumbent. Its comparison gap must not be generalized to all search settings.

## Reproducibility

Random seeds, software dependencies, experimental parameters, and dataset-generation procedures will be documented to support reproducibility.

The current implementation starts this requirement with:

- centralized experiment configuration in `src/config.py`,
- validated domain models in `src/models.py`,
- deterministic random number utilities in `src/random_utils.py`,
- numerical fuzzy security assessment in `src/fuzzy_security.py`,
- unit-aware latency and resource-load calculations in `src/latency.py` and `src/load_balance.py`,
- shared multi-task evaluation and fixed objective scales in `src/evaluation.py` and `src/objective.py`,
- seeded scenario generation and validated JSON snapshots in `src/synthetic.py` and `src/dataset_io.py`,
- bounded, deterministic small-instance verification in `src/optimizers/exact.py`,
- seeded adaptive location search and its ratio reference in `src/optimizers/genetic.py` and `src/optimizers/locations.py`,
- independent seeded SA-PSO ratios and two-layer integration in `src/optimizers/sapso.py`,
- automated tests that protect configuration validation, model constraints, and random-seed behavior.

New stochastic components should receive the independent generators returned by
`create_random_state`. That helper accepts non-negative integer seeds. The
legacy `seed_global_generators` helper accepts only seeds in `[0, 2**32 - 1]`
and validates them before changing either global generator.

`ExperimentConfig` defaults of 30 tasks and 5 servers are small development
settings, not the paper's experimental setup. The paper reports task counts in
`[60, 140]`, server counts in `[3, 9]`, and equal perspective weights in Table 4.
Recorded software versions and seeds are needed together; a seed alone does not
promise identical results across all library versions.

## Academic Integrity and AI Usage

External code, datasets, or materials used in this project will be explicitly documented and cited.

Generative AI tools may be used as development aids for explanation, debugging, code review, and documentation. All generated material will be reviewed and validated by the student.

A Generative AI Usage Disclosure will also be included in the final technical report.

## References

See [references/README.md](references/README.md) for the current reference list.
Related-work references will be added after their contents have been verified.


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

The reproduced baseline will later be extended with an original experimental contribution and evaluated through controlled experiments.

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
small-instance exact verification solver are implemented. Stage 6 of the
[roadmap](references/roadmap.md) is complete; adaptive GA, SA-PSO/BOALBFS,
and published-experiment comparison remain future work.

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
[small-instance exact verification](references/exact_search.md), and
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

Actual reference experiments remain to be implemented and executed.

## Proposed Extension

To be determined after completion and evaluation of the baseline implementation.

## Experimental Results

To be added after the experiments are executed.

## Limitations

- Numerical fuzzy, latency, and resource-load subsystems are available; full BOALBFS reproduction and
  published-experiment comparison have not been completed.
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
- The instructor-specific Minimum Reproduction Requirement (MRR) is not yet
  recorded. The course requirements have not all been satisfied at this stage.

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


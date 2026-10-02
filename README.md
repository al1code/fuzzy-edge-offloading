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

## Project Objective

The objective of this project is to reproduce the core components of the task-offloading method proposed in the reference paper, with particular emphasis on fuzzy security assessment, multi-server load balancing, and partial task offloading.

The reproduced baseline will later be extended with an original experimental contribution and evaluated through controlled experiments.

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

Until such data becomes available, the reproduction will use synthetic datasets generated according to the parameter information reported in the reference study.

Any assumptions that are not explicitly specified in the paper will be documented separately.

## Environment

- Python 3.14.5

## Installation

Create and activate a virtual environment:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
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

## Reproduction Experiments

To be implemented.

## Proposed Extension

To be determined after completion and evaluation of the baseline implementation.

## Experimental Results

To be added after the experiments are executed.

## Limitations

To be documented during implementation and experimental evaluation.

## Reproducibility

Random seeds, software dependencies, experimental parameters, and dataset-generation procedures will be documented to support reproducibility.

The current implementation starts this requirement with:

- centralized experiment configuration in `src/config.py`,
- validated domain models in `src/models.py`,
- deterministic random number utilities in `src/random_utils.py`,
- automated tests that protect configuration validation, model constraints, and random-seed behavior.

This keeps parameter choices explicit before the fuzzy security assessment and optimization algorithms are implemented.

## Academic Integrity and AI Usage

External code, datasets, or materials used in this project will be explicitly documented and cited.

Generative AI tools may be used as development aids for explanation, debugging, code review, and documentation. All generated material will be reviewed and validated by the student.

A Generative AI Usage Disclosure will also be included in the final technical report.

## References

The complete IEEE-formatted reference list will be added as the project progresses.


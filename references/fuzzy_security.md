# Numerical Fuzzy Security Baseline

Source: Jin et al. [1] in [the reference list](README.md),
[fuzzy security model](https://www.nature.com/articles/s41598-024-79464-2).
This note describes the implemented numerical subsystem, not full BOALBFS.

## Inputs and Outputs

For one task, each expert provides a `SecurityPerspectives` object containing
three `TriangularFuzzyNumber(low, modal, high)` values. The perspectives have
explicit names: `task_data`, `task_type`, and `terminal_lifecycle`. Their
components must be finite, ordered, and in `[0, 1]`.

The general triangular-number model permits finite values outside `[0, 1]`;
the security-specific object imposes the security scale. Degenerate triangles
such as `(1, 1, 1)` are allowed and represent exact assessments.

`assess_security` takes these expert assessments, their explicit weights,
an explicit security threshold, and optional `FuzzySecurityConfig` perspective
weights. It returns `FuzzySecurityResult` with the aggregated triangles, three
crisp scores, the combined security level, and the security risk.

## Equation Mapping

| Paper | Implemented calculation | Code |
| --- | --- | --- |
| Eq. (11) | Weighted sum of each triangle component over experts | `aggregate_expert_assessments` |
| Eq. (12) | `(low + 4 * modal + high) / 6` | `TriangularFuzzyNumber.paper_transformation_value` |
| Eq. (13) | Weighted combination of the three transformed perspective scores | `assess_security` |
| Eq. (14) | `1 - exp(-(theta - S))` when `S < theta`, otherwise zero | `calculate_security_risk` |
| Eq. (15) | `x * y * mu`, with `x` in `[0, 1]` and binary `y` | `calculate_offloading_risk` |

For Eq. (14), `-expm1(-(theta - S))` evaluates the same expression accurately
when the positive shortfall is very small. The equality case has zero risk.
The standard `centroid()` remains available as a distinct calculation; it is
not called by this baseline pipeline.

## Reproduction Decisions

The prose following Eq. (14) reverses the equation's risk condition. This
implementation follows the displayed equation: lower security below the
threshold increases risk. Tests cover below-threshold, equality, and
above-threshold cases, plus monotonicity. This ambiguity should remain in the
report's limitations until clarified by the authors.

Expert weights must be finite, non-negative, and sum to one. This is a
normalization assumption for interpreting the weighted expert result on the
unit security scale. The paper introduces expert weights but does not provide
their numeric values in Table 4, so the API requires them explicitly.

Perspective weights default to equal thirds, as specified for `eta_k` in
[Table 4](https://www.nature.com/articles/s41598-024-79464-2/tables/4).
The security threshold has no implicit API default: Table 4 supplies a range
`[0.2, 0.8]`, not one fixed value. The API permits the full unit interval for
boundary checks and future controlled scenarios.

Weight totals are checked with an absolute tolerance of `1e-9`. After that
check, weighted sums are divided by the accepted total to remove roundoff at
scale endpoints. Unnormalized inputs such as `(0.4, 0.4)` are rejected rather
than silently converted into a different configuration. Input types that do
not match the API raise `TypeError`; numeric constraint violations raise
`ValueError`.

This numerical baseline accepts explicit triangles. It does not infer values
for High/Medium/Low labels from Table 3; that mapping remains a separate task.
The reference method uses expert weighting and fuzzy transformation rather
than a Mamdani/Sugeno rule engine. Adding another inference method would be
a separately documented extension, not part of this baseline reproduction.

## Worked Example and Independent Checks

The command `python -B -m experiments.baseline.fuzzy_security_demo` uses two
synthetic experts with weights `(0.25, 0.75)`. None of the following inputs
are claimed to come from the reference experiments.

| Perspective | Expert 1 | Expert 2 | Aggregated triangle | Eq. (12) score |
| --- | --- | --- | --- | --- |
| Task data | `(0.1, 0.2, 0.5)` | `(0.4, 0.6, 0.9)` | `(0.325, 0.5, 0.8)` | `25/48` |
| Task type | `(0.2, 0.4, 0.8)` | `(0.3, 0.5, 0.7)` | `(0.275, 0.475, 0.725)` | `29/60` |
| Terminal lifecycle | `(0.6, 0.7, 0.9)` | `(0.1, 0.2, 0.3)` | `(0.225, 0.325, 0.45)` | `79/240` |

With illustrative perspective weights `(0.5, 0.3, 0.2)`, the combined
security level is `0.47125`. Threshold `0.6` gives security risk approximately
`0.1208062635`. Offloading ratio `0.4` to a selected server gives offloading
risk approximately `0.0483225054`. Ratio zero or assignment zero gives zero
offloading risk. The example prints all inputs and intermediates as JSON.

Tests use independently calculated component values and fractions, asymmetric
triangles, zero-weight perspectives/experts, scale boundaries, expert-order
permutation, invalid inputs, and very small threshold shortfalls. CLI tests
check repeatable JSON output, changed arguments, and informative input errors.

## Integration Boundaries for the Next Step

The fuzzy result and `Task` latency/resource calculations are now connected
in `experiments/baseline/offloading_demo.py`. No generated multi-task dataset
or common assignment evaluator has been introduced yet. See
[the simulation notes](simulation.md) for the explicit resource units.

| Existing field | Interpretation | Required simulator decision |
| --- | --- | --- |
| `Task.data_size_mb` | Decimal megabytes; one MB is 8,000,000 bits | Convert to bits for paper expressions using `D_i` |
| `Task.required_cpu_cycles` | Total cycles, equivalent to `D_i * C_i` | Do not multiply by data size a second time |
| `Task.deadline_seconds` | Additional project metadata | Do not add an undocumented baseline constraint |
| `EdgeServer.cpu_capacity_cycles_per_second` | CPU cycle capacity | Distinguish total capacity from per-task allocation `f_j^e` |
| `EdgeServer.uplink_bandwidth_mbps` / `downlink_bandwidth_mbps` | Link rates in megabits per second | Do not substitute rates for bandwidth `Lambda` in Hz |
| `EdgeServer.memory_capacity_mb` | Server memory inventory | Add explicit per-task memory demand before Eq. (8) |

Table 4 reports CPU capacity in MIPS and allocated CPU frequency in GHz.
Instructions per second and cycles per second need an explicit conversion
assumption; they cannot be interchanged directly. Communication and resource
models must resolve these unit questions before optimization is implemented.

The module has no random draws, external I/O, or mutable global state. Future
synthetic generators and optimizers should use independent random generators,
record their seeds and software versions, and share the same experiment inputs
between baseline and proposed methods.

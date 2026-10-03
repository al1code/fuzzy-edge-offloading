# Computation, Communication, and Load Model

Source: [Jin et al., the system model and problem formulation](https://www.nature.com/articles/s41598-024-79464-2).
These calculators evaluate supplied decisions; they are not a complete
multi-task assignment simulator or optimizer.

## Equation Mapping and Units

| Equation | Implemented quantity | Function |
| --- | --- | --- |
| (1) | `(1 - x) * total_cpu_cycles / local_cpu_cycles_per_second` | `calculate_task_latency` |
| (2) | `x * total_cpu_cycles / allocated_edge_cpu_cycles_per_second` on the selected server | `calculate_task_latency` |
| (3) | `x * data_size_bits / rate_bits_per_second` on the selected link | `calculate_task_latency` |
| (4) | `b * log2(1 + p * g**2 / (b * noise_density))` | `calculate_wireless_rate` |
| (5)-(8) | Weighted CPU, bandwidth, and memory reservation fractions | `calculate_server_load` |
| (9)-(10) | Mean weighted load and population variance | `calculate_load_variance` |
| (16) | Sum of local, transmission, and edge latency | `LatencyBreakdown.total_seconds` |

`Task.required_cpu_cycles` already represents `D_i * C_i`. It is not a
cycles-per-bit coefficient. Decimal MB is converted using 8,000,000 bits/MB
for transmission only. No deadline, queue, downlink response time, or parallel
execution constraint is added to the reference latency expression.

The latency API evaluates the selected server, for which `y_ij=1` if `x>0`.
For `x=0`, no edge allocation or link is required; both may be zero. The
terminal CPU rate must be positive. Invalid inactive-path values such as NaN
or negative rates are still rejected. Multi-task server IDs and assignment
consistency are deferred to the common evaluator.

## Resource Reservation Semantics

`ResourceVector` represents three explicit quantities: CPU cycles/s, wireless
bandwidth Hz, and memory MB. One vector specifies a capacity; other vectors
specify the reservations for selected tasks. The vector has no server ID
because it represents a resource budget rather than a server inventory.

Include a reservation only if its task is assigned to this server. Resource
utilization is the sum of assigned reservations divided by capacity. Capacity
must be positive; reservations may contain zero. Any utilization above one
is rejected. `LoadBalanceConfig` defaults to equal thirds, matching the
resource weights in Table 4. Accepted weight roundoff is handled as in the
fuzzy subsystem.

The paper's load equations depend on `y_ij`, not `x_i`. This model therefore
does not multiply reservations by the offloading ratio. Pass the same shared
bandwidth capacity `Lambda` to each server when reproducing that formulation;
this calculator does not invent an additional network-wide constraint.

Load variance uses all servers, including idle servers. It divides by the
number of servers, not by one less: this is population variance, not a sample
estimate. Empty systems are rejected; one-server systems have zero variance.

## Dimensional Assumptions Still Requiring Reference Clarification

Eq. (4) multiplies `zeta` by bandwidth in its noise denominator, while the
paper calls `zeta` noise power and Table 4 reports a dBm value. This API uses
noise spectral density in W/Hz so that `b * zeta` has units of watts. That
choice is an explicit dimensional interpretation, not a recovered author
setting. The Table 4 dBm value is not silently treated as a W/Hz value.

`channel_gain` is the amplitude in the equation's squared gain term.
`log1p` preserves weak-signal precision. Zero power or gain returns a zero
rate; attempting positive offloading on a zero-rate link is rejected.

CPU capacity in Table 4 is given in MIPS whereas execution allocations are
reported in GHz. The calculators use cycles/s consistently and do not infer
an instructions-per-cycle conversion. The published unit mismatch still
needs a documented baseline parameter decision before paper experiments.

Existing `EdgeServer` Mbps fields and inventory fields are preserved. They
are not automatically mapped into wireless Hz or per-task CPU allocations.
The new explicit resource vectors avoid those implicit conversions. A future
scenario schema must connect tasks, terminals, servers, links, and reservations.

## Worked Example

`python -B -m experiments.baseline.offloading_demo` connects the existing fuzzy
example with one 1 MB task needing 1.2e9 cycles, a 1e9 cycles/s terminal,
4e9 cycles/s allocated edge CPU, and a 40e6 bits/s link.

| x | Local seconds | Transmission seconds | Edge seconds | Total seconds | Offloading risk |
| --- | --- | --- | --- | --- | --- |
| 0.0 | 1.20 | 0.00 | 0.00 | 1.20 | 0.000000 |
| 0.4 | 0.72 | 0.08 | 0.12 | 0.92 | 0.048323 |
| 1.0 | 0.00 | 0.20 | 0.30 | 0.50 | 0.120806 |

Two servers are represented for load variance, with the unselected server
idle. A selected task reserves `(4e9 cycles/s, 5e6 Hz, 256 MB)` from capacities
`(8e9 cycles/s, 20e6 Hz, 1024 MB)`, yielding utilization `(0.5, 0.25, 0.25)`
and weighted load `1/3`. Variance across loads `(1/3, 0)` is `1/36`.

All these inputs are illustrative. The supplied link rate is independent
of the reservation bookkeeping in this worked example; no radio parameters
are inferred to claim that Table 4 generates 40 Mbps. A paper experiment must
use a consistent rate/bandwidth scenario or explicitly justify supplied rates.

At 4 Mbps, full offloading takes 2.3 seconds, longer than local execution.
The demo evaluates the requested ratios and makes no optimality claim.
Tests protect these hand calculations, unit conversions, inactive paths,
Shannon calculations, capacity rejection, and inclusion of idle servers.

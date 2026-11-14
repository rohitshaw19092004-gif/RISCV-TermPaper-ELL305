---
tags: [experiment, results]
---

# Model study

What was actually run for the final paper, and how it relates to the plan in
notes E1 to E7.

The plan called for RTL simulation of Rocket and BOOM. The final study uses a
simulator written for the paper instead (`study/rvmodel.c`): an RV64IM
instruction-set simulator with a first-order timing model of an out-of-order
core, a three-level cache hierarchy, a TLB and branch predictors. It runs
eleven benign kernels written in RISC-V assembly and measures what defenses
cost and what they leave behind. It contains no attack program.

## Validation

- Checksums of all eleven kernels agree between the Python reference, QEMU and
  the simulator.
- Fifteen timing unit tests match values derived by hand.
- Seventeen invariants of the defense and isolation models hold.

## Experiments

| Paper | Planned as | What it measures | Runs |
| --- | --- | --- | --- |
| E1 | [[E1 Latency characterization]] | Where loads are served; AMAT against measured latency | 11 |
| E2 | [[E2 Eviction set construction]] (replaced) | Cache size and associativity sensitivity | 165 |
| E3 | [[E3 Speculation window]] | Transient work against ROB size; predictors | 88 |
| E4 | new | Two domains under six isolation settings | 600 |
| E5 | [[E5 Defense cost]] | Seven speculation defenses, two attack models | 176 |
| E6 | [[E6 Area and frequency]] (replaced) | Defense cost against width, ROB, L1 latency; storage counted in bits | 880 |
| E7 | [[E7 Composition]] | Isolation mechanism combined with speculation defense | 100 |
| E8 | new | Randomized LLC index; spread over page-frame layouts | 231 |

[[E4 Spectre-v1 replication]] was dropped: the paper reports the published
RISC-V evidence instead (BOOM in simulation, C910 and P550 silicon).

## Headline results (Spectre model, geometric mean over kernels)

See Table 10.2 and Figure 10.1 of the paper; all numbers there are generated
from `study/results/defense.csv`.

## Limits

Trace-driven; no port or queue contention; perfect memory-dependence
prediction; one core; simplified defenses; small kernels; no clock period,
energy or area. Section 11.6 of the paper.

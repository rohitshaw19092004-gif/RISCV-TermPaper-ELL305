---
chapter: "Pipelining, Speculation and the Birth of Transient State"
latex-label: ch:pipeline
words-v0.1: 1600
words-target: 4500
tags: [chapter, status/drafted]
---

# Pipelining, Speculation and the Birth of Transient State

> [!info] Textbook anchor
> Background: textbook §10.1-§10.3 (the pipelined processor and its stages), §10.4 (pipeline hazards), §10.8 (support for interrupts and exceptions) with §10.8.2 (exceptions) and §10.8.3 (precise exceptions), §10.9.3 (performance of a non-ideal pipeline), §10.10 (power and temperature issues), and §10.11 (advanced techniques) with §10.11.1 (branch prediction) and §10.11.4 (out-of-order pipelines) [[@sarangi2025basic]].

**Word budget:** 1600 in v0.1 → **4500** target (+2900 to write)

## Section structure as drafted
- The pipeline
- Precise exceptions do not undo microarchitectural effects
- Out-of-order execution and the size of the window
- Metrics: what a defence costs

### Subsections
- Hazards and the pressure to speculate
- Branch prediction

## Figures and tables in this chapter
- Five-stage pipeline
- Hazards and their security consequence
- Branch prediction structures
- Squashed instructions leave state behind
- Out-of-order organisation

## To write for v0.2 / v0.3
- [ ] For v0.2: `eq:iron,eq:slowdown,eq:power,eq:edp` will be instantiated with measured numbers from the author's own runs ([[Ch11 Evaluation Plan]]), and this section will gain a worked example computing the EDP cost of flushing a 32 L1 at every context switch on CVA6, cross-checked against the figures reported by Wistoff et al. [[@wistoff2021fencet]]. Also to be added: a short treatment of Amdahl's law applied to defences that only slow down a subset of instructions (e.g. loads only). Target: +2 pages.

## Sources cited here
- [[@asanovic2016rocket]]
- [[@barberis2022bhi]]
- [[@evtyushkin2018branchscope]]
- [[@gonzalez2019replicating]]
- [[@riscv-priv]]
- [[@saileshwar2019cleanupspec]]
- [[@sarangi2025basic]]
- [[@wistoff2021fencet]]
- [[@yan2018invisispec]]
- [[@zhao2020sonicboom]]

## Open questions
-

## Notes while drafting
-

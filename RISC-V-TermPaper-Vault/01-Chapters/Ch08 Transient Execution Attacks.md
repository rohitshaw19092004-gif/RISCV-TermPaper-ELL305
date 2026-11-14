---
chapter: "Transient Execution Attacks"
latex-label: ch:transient
words-v0.1: 1500
words-target: 4000
tags: [chapter, status/drafted]
---

# Transient Execution Attacks

> [!info] Textbook anchor
> (no direct textbook counterpart; see the chapter itself)
**Word budget:** 1500 in v0.1 → **4000** target (+2500 to write)

## Section structure as drafted
- Anatomy
- Spectre-v1: bounds-check bypass
- The variant family
- Why the attacks reached RISC-V
- Attacks on the defenses



## Figures and tables in this chapter
- Anatomy of a transient-execution attack
- Transient-execution variants

## To write for v0.2 / v0.3
- [ ] For v0.2: add (a) a phase-by-phase mapping from each variant in `tab:variants` onto `fig:anatomy`, so that the defense coverage argument of [[Ch09 Defenses Taxonomy]] can be stated as a matrix rather than in prose;
- [ ] (b) a measured or simulated speculation-window figure for BOOM, showing how many transient instructions actually execute as a function of ROB size; this is experiment E3 in [[Ch11 Evaluation Plan]]; and (c) a short treatment of speculative interference with a worked example. Target: +6 pages.

## Sources cited here
- [[@asanovic2016rocket]]
- [[@barberis2022bhi]]
- [[@behnia2021interference]]
- [[@canella2019systematic]]
- [[@gonzalez2019replicating]]
- [[@kocher2019spectre]]
- [[@lipp2018meltdown]]
- [[@qureshi2019ceasers]]
- [[@schwarz2019zombieload]]
- [[@vanbulck2018foreshadow]]
- [[@vanschaik2019ridl]]
- [[@wikner2022retbleed]]
- [[@zhao2020sonicboom]]

## Open questions
-

## Notes while drafting
-

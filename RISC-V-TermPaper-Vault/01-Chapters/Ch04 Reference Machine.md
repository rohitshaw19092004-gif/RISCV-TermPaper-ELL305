---
chapter: "The Reference Machine: Datapath and Control"
latex-label: ch:proc
words-v0.1: 900
words-target: 2500
tags: [chapter, status/drafted]
---

# The Reference Machine: Datapath and Control

> [!info] Textbook anchor
> Background: textbook §9.1 (design of a basic processor), §9.2 (units in a processor) with §9.2.1-§9.2.7 (fetch unit; data path and control path; operand fetch unit; execute unit; memory access unit; register writeback unit; the data path) and §9.3 (the control unit) [[@sarangi2025basic]].

**Word budget:** 900 in v0.1 → **2500** target (+1600 to write)

## Section structure as drafted
- Purpose of this chapter
- The single-cycle datapath
- Where security-relevant state will appear

### Subsections
- Stage by stage
- The control path

## Figures and tables in this chapter
- Single-cycle RISC-V datapath
- Pipeline stages and the state added by optimisation

## To write for v0.2 / v0.3
- [ ] For v0.2: add a second figure showing the same datapath annotated with the actual module boundaries of an open RISC-V implementation (Rocket's RocketCore stages, or CVA6's six stages), so that the abstract textbook datapath is tied to code the reader can inspect. Also add a short subsection on the RISC-V privilege model in the datapath (mstatus, trap vectors), which [[Ch08 Transient Execution Attacks]] needs when discussing Meltdown-type faults. Target: +2.5 pages.

## Sources cited here
- [[@sarangi2025basic]]

## Open questions
-

## Notes while drafting
-

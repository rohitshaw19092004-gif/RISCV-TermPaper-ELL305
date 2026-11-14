---
chapter: "Defenses: A Taxonomy with Residual Risk"
latex-label: ch:defenses
words-v0.1: 1600
words-target: 5000
tags: [chapter, status/drafted]
---

# Defenses: A Taxonomy with Residual Risk

> [!info] Textbook anchor
> (no direct textbook counterpart; see the chapter itself)
**Word budget:** 1600 in v0.1 → **5000** target (+3400 to write)

## Section structure as drafted
- Organising the design space
- Isolation: partitioning and flushing
- Obscuring: randomised caches
- Hiding and undoing speculative effects
- Restricting speculation: information-flow tracking
- Architectural containment in RISC-V
- Software mitigations
- Comparison



## Figures and tables in this chapter
- Defense taxonomy
- Comparison of defense mechanisms

## To write for v0.2 / v0.3
- [ ] For v0.2: (a) replace the qualitative "reported cost" column with numeric values and, for each, the benchmark suite and baseline configuration used, so that the incomparability is documented rather than merely asserted;
- [ ] (b) add a coverage matrix of defense attack-phase (`fig:anatomy`) showing which combinations compose; and (c) add a paragraph on formal verification of these mechanisms and on automated exploit synthesis (CheckMate [[@trippel2018checkmate]]) and cache-vulnerability benchmarking [[@deng2020benchmark]]. Target: +7 pages.

## Sources cited here
- [[@ainsworth2020muontrap]]
- [[@ainsworth2021ghostminion]]
- [[@behnia2021interference]]
- [[@bourgeat2019mi6]]
- [[@carruth2018slh]]
- [[@choudhary2021spt]]
- [[@costan2016sanctum]]
- [[@deng2020benchmark]]
- [[@domnitser2012nonmono]]
- [[@khasawneh2019safespec]]
- [[@kiriansky2018dawg]]
- [[@lee2020keystone]]
- [[@qureshi2018ceaser]]
- [[@qureshi2019ceasers]]
- [[@riscv-cfi]]
- [[@riscv-crypto]]
- [[@riscv-priv]]
- [[@saileshwar2019cleanupspec]]
- [[@saileshwar2021mirage]]
- [[@sakalis2019delay]]
- [[@trippel2018checkmate]]
- [[@turner2018retpoline]]
- [[@wang2007newcache]]
- [[@watson2015cheri]]
- [[@weisse2019nda]]
- [[@werner2019scattercache]]
- [[@wistoff2021fencet]]
- [[@yan2018invisispec]]
- [[@yu2019stt]]

## Open questions
-

## Notes while drafting
-

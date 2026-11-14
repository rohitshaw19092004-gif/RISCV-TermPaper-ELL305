---
chapter: "The Physical Substrate: Memory Arrays That Remember Too Much"
latex-label: ch:memories
words-v0.1: 1100
words-target: 2500
tags: [chapter, status/drafted]
---

# The Physical Substrate: Memory Arrays That Remember Too Much

> [!info] Textbook anchor
> Background: textbook §7.4 (memories) and its sub-sections §7.4.1 (static RAM), §7.4.2 (content-addressable memory) and §7.4.3 (dynamic RAM) [[@sarangi2025basic]].

**Word budget:** 1100 in v0.1 → **2500** target (+1400 to write)

## Section structure as drafted
- Why a security paper has to go down to the array
- The storage cell
- From cell to array
- The same array, wearing different hats
- Why an array access is never constant-time in situ



## Figures and tables in this chapter
- Six-transistor SRAM cell
- Array organization
- Read timing of an SRAM array
- Array-based structures in a RISC-V core

## To write for v0.2 / v0.3
- [ ] For v0.2 this chapter gains: (a) a short quantitative model relating array size to access latency, in the style of CACTI, so that [[Ch10 Cost - Performance Power Area]] can price the extra tag bits required by partitioned and randomized caches;
- [ ] (b) a figure showing a set-associative tag/data array pair with the way-mux critical path highlighted; and (c) a paragraph on the DRAM organization of §7.4.3 and its row buffers, for completeness of the "arrays that remember" theme. Target: +2 pages.

## Sources cited here
- [[@riscv-crypto]]
- [[@sarangi2025basic]]
- [[@zaruba2019ariane]]
- [[@zhao2020sonicboom]]

## Open questions
-

## Notes while drafting
-

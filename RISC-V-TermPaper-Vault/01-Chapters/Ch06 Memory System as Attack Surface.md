---
chapter: "The Memory System as an Attack Surface"
latex-label: ch:memsys
words-v0.1: 1900
words-target: 6000
tags: [chapter, status/drafted]
---

# The Memory System as an Attack Surface

> [!info] Textbook anchor
> Background: textbook §11.1.2-§11.1.8 (memory access patterns, temporal and spatial locality, hierarchical memory, cache blocks), §11.2 (caches: lookup and design, read/write, insert, replace, evict), §11.3 (the memory system) with §11.3.1 (its mathematical model), and §11.4 (virtual memory) with §11.4.2 (the overlap and size problems), §11.4.3 (implementation of virtual memory with paging), §11.4.5 (the memory management unit) and §11.4.6 (advanced features of the paging system) [[@sarangi2025basic]].

**Word budget:** 1900 in v0.1 → **6000** target (+4100 to write)

## Section structure as drafted
- Locality, hierarchy, and the size of the signal
- Cache organization and the address split
- The quantitative model
- The four measurement primitives
- Virtual memory and the translation path

### Subsections
- Prime+Probe in detail
- What the measurement looks like

## Figures and tables in this chapter
- Representative memory hierarchy latencies
- Hit versus miss on the load interface
- Cache address split
- Flush+Reload and Prime+Probe
- Comparison of cache attack primitives
- Bimodal timing distribution
- Address translation and its channels

## To write for v0.2 / v0.3
- [ ] For v0.2 this chapter gains: (a) the eviction-set construction algorithm in full, with its complexity analysis and a note on the RISC-V LLC slice hash;
- [ ] (b) a quantitative bandwidth estimate for each primitive in `tab:primitives`, tied to the leakage model of `sec:leakmodel`;
- [ ] (c) a worked AES T-table example showing precisely which key bits fall out of a set-granular observation; and (d) the author's measured histograms replacing `fig:histogram`. Target: +8 pages. This is the chapter that should grow the most.

## Sources cited here
- [[@gras2018tlbleed]]
- [[@gruss2016flushflush]]
- [[@gruss2016prefetch]]
- [[@liu2015llc]]
- [[@osvik2006cache]]
- [[@riscv-priv]]
- [[@sarangi2025basic]]
- [[@yarom2014flushreload]]

## Open questions
-

## Notes while drafting
-

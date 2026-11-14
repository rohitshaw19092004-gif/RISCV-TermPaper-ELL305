---
chapter: "Multicore Systems: Sharing, Coherence and Cross-Domain Leakage"
latex-label: ch:multicore
words-v0.1: 1200
words-target: 3500
tags: [chapter, status/drafted]
---

# Multicore Systems: Sharing, Coherence and Cross-Domain Leakage

> [!info] Textbook anchor
> Background: textbook §12.2 (software for multiprocessor systems, including Amdahl's law in §12.2.3), §12.3 (the design space of multiprocessors), and §12.4 (MIMD multiprocessors) with §12.4.1 (logical point of view), §12.4.2 (coherence), §12.4.3 (memory consistency), §12.4.4 (physical view of memory), §12.4.5 (shared caches), §12.4.6 (coherent private caches) and §12.4.8 (multithreaded processors) [[@sarangi2025basic]].

**Word budget:** 1200 in v0.1 → **3500** target (+2300 to write)

## Section structure as drafted
- What sharing adds
- Coherence as a channel
- Memory consistency and fences
- Simultaneous multithreading
- Partitioning and colouring, viewed as defences



## Figures and tables in this chapter
- Multicore sharing
- MESI states and their timing
- Two partitioning mechanisms

## To write for v0.2 / v0.3
- [ ] For v0.2 this chapter gains: (a) the directory-based coherence channel described quantitatively, with the transition-cost table that [[Ch10 Cost - Performance Power Area]] needs;
- [ ] (b) a treatment of interconnect and memory-controller contention channels, which are the ones that survive every cache-level defence; and (c) a concrete mapping onto the coherence implementation of an open RISC-V uncore (TileLink), so the discussion is tied to inspectable RTL. Target: +5 pages.

## Sources cited here
- [[@kiriansky2018dawg]]
- [[@liu2015llc]]
- [[@liu2016catalyst]]
- [[@riscv-unpriv]]
- [[@sarangi2025basic]]
- [[@wistoff2021fencet]]

## Open questions
-

## Notes while drafting
-

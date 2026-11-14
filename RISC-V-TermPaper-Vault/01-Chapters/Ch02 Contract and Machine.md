---
chapter: "The Contract and the Machine: RISC-V as Architecture and as Implementation"
latex-label: ch:isa
words-v0.1: 1800
words-target: 3500
tags: [chapter, status/drafted]
---

# The Contract and the Machine: RISC-V as Architecture and as Implementation

> [!info] Textbook anchor
> Background: textbook Chapter 1 (which defines architecture as the view of a computer presented to software designers and organization as its actual hardware implementation), §1.4 (the language of instructions), §1.5 (instruction set design) and §1.7 (design of practical machines); §6.1.1 (RISC-V base ISAs and extensions), §6.1.2 (view of registers), §6.3.1-§6.3.3 (branches and memory instructions), §6.5 (instruction encoding) [[@sarangi2025basic]].

**Word budget:** 1800 in v0.1 → **3500** target (+1700 to write)

## Section structure as drafted
- An ISA is a contract about values, not about time
- The RISC-V execution model
- Architectural versus microarchitectural state, precisely
- Threat model
- Towards a leakage model

### Subsections
- Base ISAs and extensions
- Register view and the shape of a computation
- Control transfer and memory instructions
- Instruction encoding and the room for security instructions

## Figures and tables in this chapter
- RISC-V features relevant to \uarchadj{} security
- RISC-V base instruction formats
- Partition of processor state
- Threat model tiers

## To write for v0.2 / v0.3
- [ ] This section is intentionally short in v0.1. For v0.2 it will be developed into a formal treatment: (a) definition of an observation function over ;
- [ ] (b) the standard channel-capacity bound for a binary asymmetric channel modeling a hit/miss observation with measurement noise;
- [ ] (c) a worked estimate of achievable bits/second for Prime+Probe on an L1 of a given associativity, cross-checked against the rates reported by Yarom and Falkner [[@yarom2014flushreload]] and Liu et al. [[@liu2015llc]]; and (d) a discussion of why constant-time programming disciplines are exactly the requirement that this function be constant in s . Target length: 3-4 pages.

## Sources cited here
- [[@gras2018tlbleed]]
- [[@liu2015llc]]
- [[@riscv-cfi]]
- [[@riscv-crypto]]
- [[@riscv-priv]]
- [[@riscv-unpriv]]
- [[@sarangi2025basic]]
- [[@wistoff2021fencet]]
- [[@yarom2014flushreload]]

## Open questions
-

## Notes while drafting
-

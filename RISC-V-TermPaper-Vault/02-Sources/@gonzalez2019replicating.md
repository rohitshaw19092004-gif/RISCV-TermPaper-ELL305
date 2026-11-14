---
citekey: gonzalez2019replicating
title: "Replicating and Mitigating Spectre Attacks on an Open Source RISC-V Microarchitecture"
year: 2019
venue: "Third Workshop on Computer Architecture Research with RISC-V (CARRV)"
type: inproceedings
tags: [source/misc, status/to-read]
status: to-read
---

# Replicating and Mitigating Spectre Attacks on an Open Source RISC-V Microarchitecture

> [!quote] Cite as
> `\citep{gonzalez2019replicating}`

**Authors:** Abraham Gonzalez; Ben Korpan; Jerry Zhao; Ed Younis; Krste Asanovic
**Year:** 2019 · **Venue:** Third Workshop on Computer Architecture Research with RISC-V (CARRV)

## Where the paper uses this
- [[Ch01 Introduction and Scope]]
- [[Ch05 Pipelining and Speculation]]
- [[Ch08 Transient Execution Attacks]]
- [[Ch12 Conclusion]]

### Current wording in the draft
> Spectre-style attacks have been replicated on an open RISC-V out-of-order core and mitigations evaluated on the same RTL [[@gonzalez2019replicating]], and timing-channel prevention via a context-flush instruction has been implemented and measured on CVA6 [[@wistoff2021fencet]].

> An in-order core such as Rocket squashes within a couple of cycles and can execute perhaps one or two wrong-path instructions; an out-of-order core with a 100+ -entry ROB can execute a long dependent chain, which is why the demonstrations on RISC-V hardware used BOOM rather than Rocket [[@gonzalez2019replicating]].

## One-line claim
_What does this establish that nothing before it did?_

## Mechanism
-

## Numbers worth citing
| Quantity | Value | Baseline / benchmark | Where reported |
| --- | --- | --- | --- |
|  |  |  |  |

> [!warning] Record the baseline, always
> Chapter 10 of the paper argues that overheads are incomparable across papers.
> A number without its baseline and benchmark suite is unusable there.

## What this does NOT establish
-

## Follow-ups for v0.2
- [ ] Verify the BibTeX record against Zotero (venue, volume, pages, DOI)
- [ ]

## Related
-

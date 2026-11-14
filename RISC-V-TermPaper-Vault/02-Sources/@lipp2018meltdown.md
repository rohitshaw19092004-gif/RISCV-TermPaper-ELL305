---
citekey: lipp2018meltdown
title: "Meltdown: Reading Kernel Memory from User Space"
year: 2018
venue: "USENIX Security Symposium"
type: inproceedings
tags: [source/attack, status/to-read]
status: to-read
---

# Meltdown: Reading Kernel Memory from User Space

> [!quote] Cite as
> `\citep{lipp2018meltdown}`

**Authors:** Moritz Lipp; Michael Schwarz; Daniel Gruss; Thomas Prescher; Werner Haas; Anders Fogh; Jann Horn; Stefan Mangard; Paul Kocher; Daniel Genkin; Yuval Yarom; Mike Hamburg
**Year:** 2018 · **Venue:** USENIX Security Symposium

## Where the paper uses this
- [[Ch01 Introduction and Scope]]
- [[Ch08 Transient Execution Attacks]]

### Current wording in the draft
> This is the mechanism behind cache-timing attacks on AES [[@osvik2006cache]] [[@bernstein2005aes]], behind cross-core attacks on the last-level cache [[@liu2015llc]], behind TLB-based leakage [[@gras2018tlbleed]], and, after 2018, behind the transient-execution family in which a processor is induced to compute on data it was never permitted to read and to leave the answer behind in a cache [[@kocher2019spectre]] [[@lipp2018meltdown]].

> Meltdown-type [[@lipp2018meltdown]] [[@vanbulck2018foreshadow]] & A faulting load's data is forwarded to dependent instructions before the permission check retires & Depends on whether the implementation forwards data past a failed PMP or page permission check.

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

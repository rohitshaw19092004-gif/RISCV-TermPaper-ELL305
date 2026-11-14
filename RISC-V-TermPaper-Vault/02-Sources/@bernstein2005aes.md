---
citekey: bernstein2005aes
title: "Cache-Timing Attacks on AES"
year: 2005
venue: "Technical report, University of Illinois at Chicago"
type: misc
tags: [source/attack, status/to-read]
status: to-read
---

# Cache-Timing Attacks on AES

> [!quote] Cite as
> `\citep{bernstein2005aes}`

**Authors:** Daniel J. Bernstein
**Year:** 2005 · **Venue:** Technical report, University of Illinois at Chicago

## Where the paper uses this
- [[Ch01 Introduction and Scope]]

### Current wording in the draft
> This is the mechanism behind cache-timing attacks on AES [[@osvik2006cache]] [[@bernstein2005aes]], behind cross-core attacks on the last-level cache [[@liu2015llc]], behind TLB-based leakage [[@gras2018tlbleed]], and, after 2018, behind the transient-execution family in which a processor is induced to compute on data it was never

> The move to targets came with Percival's demonstration that cache contention on a simultaneously multithreaded processor leaks across threads [[@percival2005cache]], and with the AES cache-timing attacks of Bernstein [[@bernstein2005aes]] and of Osvik, Shamir and Tromer [[@osvik2006cache]], which established the eviction and reload primitives still in use.

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

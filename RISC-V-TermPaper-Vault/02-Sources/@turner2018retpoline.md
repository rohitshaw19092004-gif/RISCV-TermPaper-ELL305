---
citekey: turner2018retpoline
title: "Retpoline: A Software Construct for Preventing Branch-Target-Injection"
year: 2018
venue: "Google technical whitepaper"
type: misc
tags: [source/defense, status/to-read]
status: to-read
---

# Retpoline: A Software Construct for Preventing Branch-Target-Injection

> [!quote] Cite as
> `\citep{turner2018retpoline}`

**Authors:** Paul Turner
**Year:** 2018 · **Venue:** Google technical whitepaper

## Where the paper uses this
- [[Ch09 Defenses Taxonomy]]

### Current wording in the draft
> Speculative load hardening [[@carruth2018slh]] masks addresses with a predicate derived from the branch condition, so that a mis-speculated load reads a safe address; retpolines [[@turner2018retpoline]] replace indirect branches with a construct that steers speculation to a benign target; and explicit fences before sensitive loads stop the speculation window from opening at all.

> SLH [[@carruth2018slh]], retpoline [[@turner2018retpoline]] & Restrict (SW) & Instruction-count overhead; no hardware change & Deployable today.

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

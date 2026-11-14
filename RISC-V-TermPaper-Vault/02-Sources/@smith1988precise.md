---
citekey: smith1988precise
title: "Implementing Precise Interrupts in Pipelined Processors"
year: 1988
venue: "IEEE Transactions on Computers 37(5)"
type: article
tags: [source/background, status/to-read]
status: to-read
---

# Implementing Precise Interrupts in Pipelined Processors

> [!quote] Cite as
> `\citep{smith1988precise}`

**Authors:** James E. Smith; Andrew R. Pleszkun
**Year:** 1988 · **Venue:** IEEE Transactions on Computers, vol. 37, no. 5

## Where the paper uses this
- [[Ch05 Pipelining and Speculation]]: §5.2, "Precise exceptions do not undo
  microarchitectural effects"

### Current wording in the draft
> The definition quantifies over *architectural* state only, because when the
> mechanism was standardized in the form we still use [[@smith1988precise]],
> that was the only state anyone had reason to care about.

## Why it was added
Added during the [[Correction pass v0.1]]. The draft asserted a date ("in 1988,
when the mechanism was standardized") with no citation, the only uncited
historical claim in a paper that cites everything else. This is the reference
that claim rests on.

## One-line claim
Defines the reorder-buffer / history-buffer / future-file mechanisms that let a
pipelined machine present *precise* interrupts, and fixes the definition the
paper leans on: all instructions before the faulting one complete, none after it
has any effect, architectural state is exactly as if execution stopped there.

## Mechanism
- Reorder buffer: results retire in program order, so architectural state only
  ever advances through states a sequential machine would have reached.
- The definition quantifies over **architectural** state only. That scope
  restriction is the whole hinge of [[Ch08 Transient Execution Attacks]].

## Numbers worth citing
| Quantity | Value | Baseline / benchmark | Where reported |
| --- | --- | --- | --- |
| - | - | - | not used for numbers |

## What this does NOT establish
- Nothing whatever about microarchitectural state. That is precisely the point
  the paper makes with it: the guarantee was defined before cache and predictor
  residue was considered a confidentiality problem, and it was never widened.

## Follow-ups for v0.2
- [ ] Verify the BibTeX record against Zotero (pages 562-573, DOI)
- [ ] Check whether to also cite the ISCA 1985 version alongside the TOC one

## Related
- [[Ch05 Pipelining and Speculation]]
- [[Ch08 Transient Execution Attacks]]

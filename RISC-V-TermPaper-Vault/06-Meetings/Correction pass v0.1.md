---
date: 2026-08-23
tags: [log, review]
---

# Correction pass: v0.1, 23 August 2026

**Target this session:** review the compiled v0.1 end to end before submitting,
fix everything found, rebuild, and leave the repository submission-ready.

## Verified clean (no change needed)

- **Textbook mapping.** Every section and sub-section number in Table 1.1 and
  Appendix D was checked against the live `archbook.pdf`. All ~45 of them match,
  including the easy ones to get wrong: §10.8.2 Exceptions / §10.8.3 Precise
  Exceptions, §10.10.5 The *ED²* Metric, §11.3.1 Mathematical Model of the
  Memory System, §11.4.2 The "Overlap" and "Size" Problems, §12.2.3 Amdahl's
  Law, §12.4.8 Multithreaded Processors. The book's own title page reads
  *Basic Computer Architecture, Version 3.09, Smruti R. Sarangi, October 8,
  2025*, which is the citation used. See [[Submission requirements]].
- **Bibliography.** All 61 original records checked against author, title, venue
  and year. No errors found.
- **Build.** 72 pages, 0 errors, 0 undefined references, 0 undefined citations,
  **0 overfull boxes**. `IEEEtranN.bst` is found and used.
- **Format.** A4, `margin=1in` + `bindingoffset=0.5in`, 11 pt, `\singlespacing`,
  single source file, no `\includegraphics` anywhere.

## Fixed: content errors

| # | Where | What was wrong |
| --- | --- | --- |
| 1 | Appendix A, §9.2.1 row | `\&` instead of `&` collapsed the whole row into the 2 cm first column as a ragged block with literal `&` characters |
| 2 | `fig:hierarchy` | On a log axis pgfplots' default `point meta` is log₁₀(y), so the bars were labelled 0.6, 1.15, 1.65, 2.34 instead of 4, 14, 45, 220 |
| 3 | `fig:addrsplit` | 512 KiB / 8-way / 64 B ⇒ 1024 sets ⇒ **10** index bits. The figure showed 6 (tag boundary at bit 11 instead of bit 15) |
| 4 | `lst:spectre1rv` caption | Pointed at lines 3-6 and called line 6 the transmitter; the transmitter is line 9 and the window is lines 3-9 |
| 5 | `fig:squash` | Branch resolved in EX at cycle 3, yet a third wrong-path instruction was *fetched* at cycle 4, all three ran to WB past the squash line, and the correct path restarted at cycle 7. Redrawn: two wrong-path instructions killed in ID and IF, correct path restarts at cycle 4 |
| 6 | Eq. (5.2) | `S = IPC_base/IPC_def − 1` only holds at constant `N_inst` and `f`, which the bullets directly above say is false for SLH/retpolines. Condition now stated |
| 7 | `fig:sram` | BL fed the node labelled Q̄ and BL̄ fed Q: backwards from convention. Labels swapped |
| 8 | §1.6 contribution 4 | Promised overheads "stating the baseline and benchmark suite each number came from"; v0.1 does not do that. Rescoped to what v0.1 actually delivers |
| 9 | Declaration + title-page box | Claimed every record was "managed in Zotero and exported to BibTeX" while Appendix C admitted hand entry. Both now say the same true thing |
| 10 | `fig:histogram` | Legend said "cached / uncached" while the modes sit at the *LLC* and *DRAM* latencies of `fig:hierarchy`. Relabelled |
| 11 | `fig:pareto` | Put randomisation at "one structure"; §10.3 says it defends "one specific attack step". Moved to match, which also fills the orphaned bottom category |
| 12 | §5.2 | "in 1988, when the mechanism was standardised" was the only uncited historical claim in the paper. Now cites [[@smith1988precise]] |
| 13 | `sarangi2025basic` | `edition = {Version 3.09}` produced a BibTeX warning and rendered as "version 3.09 ed."; moved into `note` |

## Fixed: figures that rendered wrong

- `fig:predictors`: the two red callouts overlapped each other (the `atk` style
  overrode the picture-wide `\scriptsize`). Anchored north/south so they grow
  apart.
- `fig:mesi`: "a write elsewhere invalidates" ran through the **I** and **S**
  circles. That edge is now bowed below them.
- `fig:sv39`: "up to 4 memory accesses" collided with the page-table box; the
  gap between the box and the riser is narrower than the label, so it now sits
  under the box.
- `fig:histogram`: "threshold θ" was clipped by the top axis frame.
- `fig:partition`: eight "way *n*" labels crammed into 0.66-wide boxes with no
  gap. Rotated 90°.
- `fig:anatomy`: the four phase boxes had ragged heights. Equalised.
- `fig:datapath`: the write-back wire struck through the "OF (§9.2.3)" and "WB"
  stage labels. The `note` style is now opaque, which fixes this class of defect
  across every figure.
- `fig:ooo`: the FU→LSQ arrow crossed the "execution window" brace label.
- `fig:gantt`: two bar labels were wider than their own bars, so the milestone
  rules showed through the overflow. Labels shortened to fit; rules moved to the
  background layer.
- Widow/orphan control added (`\widowpenalty`, `\clubpenalty`, `\raggedbottom`
  at `\AtBeginDocument`), which fixed a stranded "…Equation (2.1) requires."
  line at the top of page 18.
- Narrow table columns in `tab:arrayzoo` and `tab:area` set `\raggedright`;
  underfull boxes dropped from 148 to 123.

## Deliberately NOT changed

- **Title keeps American "Defenses"** while the body keeps British "defences".
  The title must match what was registered on the course form. Do not "fix" this
  without changing the form entry too.
- **`tikz-timing` instead of WaveDrom.** Still the right call, still documented
  in Appendix B and in [[Open questions]] as a justified deviation.
- **Illustrative figures stay illustrative.** `fig:hierarchy`, `fig:histogram`,
  `fig:overheads`, `fig:pareto` are labelled as not-measured and stay that way
  until [[E1 Latency characterisation]] and [[E5 Defence cost]] land.

## Second pass, same day

Three things the first pass had left open, all now closed.

**Zotero is real.** Installed it, imported all 62 records, and confirmed against
the Zotero database directly: 62 items, 48 with page numbers, 38 with a DOI.
Pages and DOIs came from DBLP and Crossref, matched on title *and* venue rather
than title alone. That mattered: FireSim first came back as its IEEE Micro Top
Picks reprint (pages 56-65) instead of the ISCA paper (pages 29-42), and STT came
back as its IEEE Micro version instead of MICRO 2019. Both would have been wrong
in the bibliography. The Declaration, the title-page box and Appendix B now say
plainly that the records are managed in Zotero, because they are.

**Style pass.** Reread the prose for mannered constructions and rewrote
them: an anaphoric "behind X,
behind Y, behind Z" chain, several inflated absolutes ("without exception", "the
single most consequential", "everything in Chapter 8 follows from"), a run of
dramatic one-line closers, two "the question is" sentences back to back, and the
connective "which is why", which appeared ten times and now appears three. In the
vault the main offender was the em dash: 229 of them, now none. Nothing the
paper claims has changed; only how it says it.

**GitHub.** Repository created and pushed, tagged `v0.1`.

## Third pass: rebuild to the final guidelines

A revised set of ten guidelines arrived after the paper was already verified.
What changed, and what it cost:

**Format.** 11pt to 12pt, and the 0.5 inch binding gutter removed so the margins
are 1 inch all around. That alone took the paper from 72 to 80 pages. Measured
from the rendered PDF afterwards: 210x297 mm, left 0.984 in, right 0.955 in,
baseline 14.45 pt, which is 12pt single spaced.

**Three new front and back matter sections.** Copyright assignment on page ii
assigning IPR to IIT Delhi and reserving cited authors' rights; acknowledgements
on page iii; and, at the back, an autogenerated Index built with `imakeidx` plus
`makeindex` from 90 `\index` marks, and a Glossary of 60 terms built with
`glossaries` in `makenoidxglossaries` mode so that no external glossary tool is
needed and the single file rule survives.

**Two new appendices.** A is the plagiarism report. It states honestly that no
institutional similarity tool has been run on this draft and claims no
percentage, and it lists the four categories of overlap a checker would
legitimately flag. B is the reading indices: eight measures computed over the
body prose of Chapters 1 to 12 with the method and the underlying counts stated,
so the figures are reproducible from the submitted source.

**Guideline 7.** Every block over roughly 300 words was measured. One qualified
and moved: the cost metric primer that was section 5.5 is now Appendix C, and
Chapter 5 keeps a pointer plus the one warning that belongs beside the
speculation machinery. Three more were assessed and deliberately left in place,
including Chapter 3, which is a mapped chapter answering to textbook section 7.4
and cannot be moved without breaking the textbook mapping the course form asks
about. That reasoning is recorded in the paper itself, not just here.

Final state: 91 pages, 0 errors, 0 overfull boxes, 0 undefined references,
`latexmk` completes the whole build in one command.

## Blocked on

- Nothing. v0.1 is ready to submit.

## Next

- Create the GitHub repository (see [[Submission requirements]]), push, tag
  `v0.1`, then upload the `.tex` and `.pdf` to Gradescope.
- Then start v0.2: [[E1 Latency characterisation]], [[E2 Eviction set construction]].

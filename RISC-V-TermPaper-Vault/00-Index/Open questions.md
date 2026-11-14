---
tags: [moc]
---

# Open questions

## Decided
- **Waveform toolchain.** `tikz-timing`, not imported WaveDrom output: WaveDrom
  emits image files, which breaks the single-file rule. Documented as a
  justified deviation in Appendix E; WaveDrom descriptions kept in
  `03-Figures/wavedrom` so the figures can be regenerated if the constraint is
  relaxed.
- **Citation style.** Numbered, IEEE-like (`IEEEtranN` where available,
  `plainnat` otherwise). Confirmed: `IEEEtranN.bst` resolves in this workspace,
  so the bibliography is typeset in true IEEE style.
- **Paper and student metadata.** The exact paper title, Rohit Shaw,
  2022MT61988, ELL 305, Computer Architecture, Prof. Subrat Kar, and the GitHub
  link are recorded in the LaTeX title page and vault home.
- **Title spelling.** The title keeps American *"Defenses"* to match the course
  form entry; the body keeps British *"defenses"* throughout. This is a
  deliberate mismatch, not an oversight. See [[Correction pass v0.1]]. Only
  change it if the form entry changes too.
- **Illustrative figures stay labelled.** `fig:hierarchy`, `fig:histogram`,
  `fig:overheads` and `fig:pareto` are synthesised, not measured, and every one
  of them says so in its own caption. They stay that way until
  [[E1 Latency characterisation]] and [[E5 Defense cost]] produce real numbers.
  The alternative, an authoritative-looking chart mixing incomparable numbers,
  is the failure mode Chapter 10 is written against.

## Outstanding


- [ ] Finalise the benchmark selection for `tab:platform`.
- [ ] Decide the scope of E7 (composition): highest value, highest risk.

## Done

- **Zotero.** All 62 records live in the Zotero library on this machine
  (`~/Zotero`), imported 23 August 2026. Forty-eight carry page numbers and
  thirty-eight carry a DOI, taken from DBLP and Crossref and checked venue by
  venue. The twenty-four without a DOI are the USENIX Security papers, the two
  CARRV workshop papers, the specifications, the textbooks and the vendor
  documents, none of which are issued one. The exported database is kept at
  `02-Sources/zotero-library.bib` and is the same text that sits in the
  `filecontents*` block of the `.tex`.
  - Worth knowing for next time: searching DBLP or Crossref by title alone
    returns the journal reprint of a conference paper as happily as the paper
    itself. FireSim came back as its IEEE Micro Top Picks version and STT as its
    IEEE Micro one, both with the wrong page numbers. Every match was re-checked
    against the venue recorded in the entry before anything was written.

## Answered by the correction pass

- **Does the textbook mapping actually match the book?** Yes. All ~45 cited
  sections and sub-sections verified against the live PDF. Details in
  [[Correction pass v0.1]].
- **Can a five-stage in-order pipeline demonstrate the Spectre transmitter?**
  No, and the paper now says so. The branch resolves in EX, so wrong-path
  instructions are killed before the memory stage and never touch the D-cache.
  What survives is the I-cache line and the predictor update. This is why the
  demonstrations on RISC-V used BOOM rather than Rocket, and it makes §5.3 the
  hinge of the argument rather than a nicety.

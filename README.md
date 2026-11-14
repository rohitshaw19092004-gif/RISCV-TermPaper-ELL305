# Microarchitectural Security in Modern RISC-V Processors

Term paper for **ELL 305, Computer Architecture**, taught by Prof. Subrat Kar.

**Cache and Speculative-Execution Attacks, Defenses, and Performance Trade-offs**

| | |
| --- | --- |
| Author | Rohit Shaw |
| Entry number | 2022MT61988 |
| Course | ELL 305: Computer Architecture |
| Instructor | Prof. Subrat Kar |
| Submission | `RISCV_Microarch_Security_TermPaper_Final.tex` and the PDF compiled from it |

The final paper is one LaTeX file of 160 pages: twelve chapters that follow the
prescribed textbook from the ISA to multicore sharing, and twenty appendices
that hold the plagiarism report, the reading indices, the extended
explanations, and the model study. Appendix R lists the eleven kernels in full;
Appendix S describes the simulator and its tools, which live in `study/` with
the SHA-256 digests given in Appendix T. The first
submission (`..._v0.1.tex`/`.pdf`) is kept for reference.

## Building the paper

With a full TeX distribution:

```
latexmk -pdf RISCV_Microarch_Security_TermPaper_Final.tex
```

or the same thing by hand: `pdflatex`, `bibtex`, `makeindex`, `pdflatex`,
`pdflatex`. The script

```
python3 tools/build_paper.py
```

runs the `latexmk` build in a scratch directory, copies the PDF next to the
source and reports the page count, unresolved references and overfull boxes,
followed by the submission checks listed under "Before submitting".
Where no TeX distribution is installed it falls back to Tectonic (also
available as `--tectonic`) and produces the index itself.
`refs.bib` is written at compile time by `filecontents*`; it is a build product
and is not part of the submission.

## The model study

`study/` holds the programs behind every table and plot of Chapters 5 to 11.

```
python3 study/run_study.py        # build, validate, run all experiments (about 2.5 minutes)
python3 study/make_fragments.py   # results/*.csv -> LaTeX tables, plots and numbers
python3 tools/readability.py      # reading indices of Appendix B
```

Requirements: a C compiler, Python 3 and `qemu-system-riscv64`. No RISC-V
cross-compiler is needed; the assembler is part of the study.

| File | Purpose |
| --- | --- |
| `study/rvmodel.c` | RV64IM instruction-set simulator with a first-order timing model, caches, TLB, predictors, and defense switches |
| `study/rvasm.py` | Two-pass assembler for the RV64IM subset the kernels use |
| `study/workloads/*.s` | Start-up code and eleven kernels in RISC-V assembly |
| `study/reference.py` | Independent Python implementation of each kernel |
| `study/run_study.py` | Validation (reference = QEMU = model, 35 timing tests against hand-derived values, 17 invariants) and experiments |
| `study/make_fragments.py` | Generates the tables, plots and number macros embedded in the paper |
| `study/results/` | CSV results and `manifest.json` with SHA-256 digests and tool versions |

The runs are deterministic: repeating them reproduces the CSV files byte for
byte. The tables, plots and numbers in the `.tex` sit between
`BEGIN GENERATED` / `END GENERATED` comments and come from these files.

## Before submitting

1. Make every other change first, compile, and submit that PDF to Turnitin.
   If an earlier version was already submitted, resubmit to the same assignment
   so that the new file replaces it; a second, separate submission is compared
   with the first one and will match it almost entirely.
2. Enter the figures of the Turnitin report in the `\Turnitin...` macros near
   the top of the `.tex` (Appendix A prints them; `\TurnitinSources` is
   optional) and recompile. Change nothing else after the Turnitin submission.
3. Upload the `.tex` and the PDF to Gradescope (single author: an individual
   submission; a team paper must name every author in the group submission).

`python3 tools/build_paper.py` checks what the compiler cannot:

- the fields above that are still empty;
- the pages of the copyright assignment and the acknowledgements (they must be
  ii and iii);
- the longest stretch of prose under one heading of the chapters (the half-page
  rule; the limit is 300 words);
- that no `\texttt`, `\verb`, `verbatim` or `\includegraphics` is left in the
  source, because all program text, inline or displayed, is typeset with
  `listings` (`\icode|...|`, `\code{...}` and `\tcode{...}` are `\lstinline`);
- that every figure, table and listing is referred to in the text.

The last build passes all of them except the two hand-filled items.

## Repository layout

```
RISCV_Microarch_Security_TermPaper_Final.tex   the submission
RISCV_Microarch_Security_TermPaper_Final.pdf   compiled from it
RISCV_Microarch_Security_TermPaper_v0.1.*      the first submission
study/                                         model study: programs and results
tools/                                         build and reading-index scripts
RISC-V-TermPaper-Vault/                        Obsidian vault with working notes
```

## Copyright

As page ii of the paper states, all intellectual property rights in the paper
and in the programs prepared for it are assigned to the Indian Institute of
Technology Delhi; rights in cited material remain with its authors. No license
is granted by publishing this repository.

## Prescribed textbook

S. R. Sarangi, *Basic Computer Architecture*, Version 3.09, 8 October 2025.
<https://srsarangi.github.io/archbook/archbook.pdf>

Chapters 6, 9, 10, 11 and 12 are the spine of the paper; Chapters 1 and 7 are
supporting. Section 1.1 of the paper sets out the relevance to ELL 305, Table
1.2 gives the mapping at chapter and section level, and Appendix D at
sub-section level.

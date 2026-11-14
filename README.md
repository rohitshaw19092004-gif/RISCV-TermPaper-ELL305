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

The final paper is one LaTeX file of 179 pages: twelve chapters that follow the
prescribed textbook from the ISA to multicore sharing, and twenty appendices
that hold the plagiarism report, the reading indices, the extended
explanations, and the complete model study with its programs. The first
submission (`..._v0.1.tex`/`.pdf`) is kept for reference.

## Building the paper

With a full TeX distribution:

```
latexmk -pdf RISCV_Microarch_Security_TermPaper_Final.tex
```

or the same thing by hand: `pdflatex`, `bibtex`, `makeindex`, `pdflatex`,
`pdflatex`. With only Tectonic installed:

```
python3 tools/build_paper.py
```

which runs Tectonic and produces the index (Tectonic has no `makeindex`).
`refs.bib` is written at compile time by `filecontents*`; it is a build product
and is not part of the submission.

## The model study

`study/` holds the programs behind every table and plot of Chapters 5 to 11.

```
python3 study/run_study.py        # build, validate, run all experiments (about 2 minutes)
python3 study/make_fragments.py   # results/*.csv -> LaTeX tables, plots and numbers
python3 tools/readability.py      # reading indices of Appendix B
```

Requirements: a C compiler, Python 3 and `qemu-system-riscv64`. No RISC-V
cross-compiler is needed; the assembler is part of the study.

| File | Purpose |
| --- | --- |
| `study/rvmodel.c` | RV64IM instruction-set simulator with a first-order timing model, caches, TLB, predictors, and defence switches |
| `study/rvasm.py` | Two-pass assembler for the RV64IM subset the kernels use |
| `study/workloads/*.s` | Start-up code and eleven kernels in RISC-V assembly |
| `study/reference.py` | Independent Python implementation of each kernel |
| `study/run_study.py` | Validation (reference = QEMU = model, timing unit tests, invariants) and experiments |
| `study/make_fragments.py` | Generates the tables, plots and number macros embedded in the paper |
| `study/results/` | CSV results and `manifest.json` with SHA-256 digests and tool versions |

The runs are deterministic: repeating them reproduces the CSV files byte for
byte. The tables, plots and numbers in the `.tex` sit between
`BEGIN GENERATED` / `END GENERATED` comments and come from these files.

## Before submitting

1. Compile the PDF and submit it to Turnitin.
2. Enter the figures of the Turnitin report in the `\Turnitin...` macros near
   the top of the `.tex` (Appendix A prints them) and recompile.
3. Upload the `.tex` and the PDF to Gradescope.

## Repository layout

```
RISCV_Microarch_Security_TermPaper_Final.tex   the submission
RISCV_Microarch_Security_TermPaper_Final.pdf   compiled from it
RISCV_Microarch_Security_TermPaper_v0.1.*      the first submission
study/                                         model study: programs and results
tools/                                         build and reading-index scripts
RISC-V-TermPaper-Vault/                        Obsidian vault with working notes
```

## Prescribed textbook

S. R. Sarangi, *Basic Computer Architecture*, Version 3.09, 8 October 2025.
<https://srsarangi.github.io/archbook/archbook.pdf>

Chapters 6, 9, 10, 11 and 12 are the spine of the paper; Chapters 1 and 7 are
supporting. Section 1.1 of the paper sets out the relevance to ELL 305, Table
1.2 gives the mapping at chapter and section level, and Appendix D at
sub-section level.

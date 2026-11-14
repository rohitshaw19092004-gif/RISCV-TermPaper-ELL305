---
tags: [index]
---

# Figure and table index

Every figure is drawn programmatically inside the single `.tex`: TikZ,
CircuiTikZ, pgfplots, `forest` and `tikz-timing`. There are **no external image
files**, which is what keeps the submission to one source file.

Labels below are the stable identifiers; printed numbers move between drafts, so
cross-reference by label. Regenerated from the v0.1 source after the correction
pass of 23 August 2026. See [[Correction pass v0.1]].

> [!warning] Figures still labelled *illustrative*
> `fig:hierarchy`, `fig:histogram`, `fig:overheads` and `fig:pareto` are not
> measured data. They must be replaced from [[E1 Latency characterisation]] and
> [[E5 Defense cost]] before the final version, or the labels must stay.

## Figures
| Label | Short caption | Chapter |
| --- | --- | --- |
| `fig:gap` | The architecture/microarchitectural gap | Ch. 1: Introduction and Scope |
| `fig:roadmap` | Textbook-to-paper chapter mapping | Ch. 1: Introduction and Scope |
| `fig:encoding` | RISC-V base instruction formats | Ch. 2: The Contract and the Machine: RISC-V as Architecture and as Implementation |
| `fig:sram` | Six-transistor SRAM cell | Ch. 3: The Physical Substrate: Memory Arrays That Remember Too Much |
| `fig:array` | Array organisation | Ch. 3: The Physical Substrate: Memory Arrays That Remember Too Much |
| `fig:readtiming` | Read timing of an SRAM array | Ch. 3: The Physical Substrate: Memory Arrays That Remember Too Much |
| `fig:datapath` | Single-cycle RISC-V datapath | Ch. 4: The Reference Machine: Datapath and Control |
| `fig:pipeline` | Five-stage pipeline | Ch. 5: Pipelining, Speculation and the Birth of Transient State |
| `fig:predictors` | Branch prediction structures | Ch. 5: Pipelining, Speculation and the Birth of Transient State |
| `fig:squash` | Squashed instructions leave state behind | Ch. 5: Pipelining, Speculation and the Birth of Transient State |
| `fig:ooo` | Out-of-order organisation | Ch. 5: Pipelining, Speculation and the Birth of Transient State |
| `fig:hierarchy` | Representative memory hierarchy latencies | Ch. 6: The Memory System as an Attack Surface |
| `fig:hitmiss` | Hit versus miss on the load interface | Ch. 6: The Memory System as an Attack Surface |
| `fig:addrsplit` | Cache address split | Ch. 6: The Memory System as an Attack Surface |
| `fig:primitives` | Flush+Reload and Prime+Probe | Ch. 6: The Memory System as an Attack Surface |
| `fig:histogram` | Bimodal timing distribution | Ch. 6: The Memory System as an Attack Surface |
| `fig:sv39` | Address translation and its channels | Ch. 6: The Memory System as an Attack Surface |
| `fig:multicore` | Multicore sharing | Ch. 7: Multicore Systems: Sharing, Coherence and Cross-Domain Leakage |
| `fig:mesi` | MESI states and their timing | Ch. 7: Multicore Systems: Sharing, Coherence and Cross-Domain Leakage |
| `fig:partition` | Two partitioning mechanisms | Ch. 7: Multicore Systems: Sharing, Coherence and Cross-Domain Leakage |
| `fig:anatomy` | Anatomy of a transient-execution attack | Ch. 8: Transient Execution Attacks |
| `fig:taxonomy` | Defense taxonomy | Ch. 9: Defenses: A Taxonomy with Residual Risk |
| `fig:overheads` | Indicative cost by defense class | Ch. 10: What Security Costs: Performance, Power and Area |
| `fig:pareto` | Cost versus breadth of guarantee | Ch. 10: What Security Costs: Performance, Power and Area |
| `fig:gantt` | Schedule to the final version | Ch. 11: Evaluation Plan for v0.2 and v0.3 |

## Tables
| Label | Short caption | Chapter |
| --- | --- | --- |
| `tab:tocmap` | Chapter- and section-level textbook mapping | Ch. 1: Introduction and Scope |
| `tab:extensions` | RISC-V features relevant to microarchitectural security | Ch. 2: The Contract and the Machine: RISC-V as Architecture and as Implementation |
| `tab:statepartition` | Partition of processor state | Ch. 2: The Contract and the Machine: RISC-V as Architecture and as Implementation |
| `tab:threat` | Threat model tiers | Ch. 2: The Contract and the Machine: RISC-V as Architecture and as Implementation |
| `tab:arrayzoo` | Array-based structures in a RISC-V core | Ch. 3: The Physical Substrate: Memory Arrays That Remember Too Much |
| `tab:stagestate` | Pipeline stages and the state added by optimisation | Ch. 4: The Reference Machine: Datapath and Control |
| `tab:hazards` | Hazards and their security consequence | Ch. 5: Pipelining, Speculation and the Birth of Transient State |
| `tab:primitives` | Comparison of cache attack primitives | Ch. 6: The Memory System as an Attack Surface |
| `tab:variants` | Transient-execution variants | Ch. 8: Transient Execution Attacks |
| `tab:defenses` | Comparison of defense mechanisms | Ch. 9: Defenses: A Taxonomy with Residual Risk |
| `tab:area` | Storage and logic overheads by defense class | Ch. 10: What Security Costs: Performance, Power and Area |
| `tab:platform` | Intended evaluation platform | Ch. 11: Evaluation Plan for v0.2 and v0.3 |
| `tab:experiments` | Planned experiments | Ch. 11: Evaluation Plan for v0.2 and v0.3 |
| `tab:tocdetail` | Sub-section-level mapping between the prescribed textbook and this paper | App. A: Detailed Mapping to the Textbook Table of Contents |

## Listings
| Label | Content |
| --- | --- |
| `lst:leak` | The canonical leak, in RISC-V assembly |
| `lst:spectre1` | The Spectre-v1 gadget in C |
| `lst:spectre1rv` | The same gadget compiled for RV64GC |

## Waveforms
The course requires WaveDrom. WaveDrom renders to SVG/PNG, which would break the
single-file submission rule, so the paper renders these with `tikz-timing`
instead and keeps the equivalent WaveDrom descriptions here:

- [[03-Figures/wavedrom/fig-readtiming-sram-array-read.json|SRAM array read]] → `fig:readtiming` (textbook §7.4.1)
- [[03-Figures/wavedrom/fig-hitmiss-load-interface.json|Hit vs miss on the load interface]] → `fig:hitmiss`

Paste either into <https://wavedrom.com/editor.html> to render. The reasoning for
the substitution is in Appendix E of the paper and in [[Open questions]].

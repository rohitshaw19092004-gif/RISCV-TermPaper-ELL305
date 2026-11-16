#!/usr/bin/env python3
"""make_fragments.py - turn the CSV results of run_study.py into the LaTeX
tables, plots and number macros that the term paper embeds.

Every number that the paper quotes from the model study is produced here, so
that no figure is ever copied into the text by hand. Output: build/fragments/.
"""
import csv
import json
import math
import os
import re
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
OUT = os.path.join(HERE, "build", "fragments")
KERNELS = ["matmul", "heapsort", "listwalk", "bsearch", "bstree", "crc32",
           "sieve", "hashtab", "stream", "fibcall", "strsearch"]
DEFS = ["nospec", "dom", "invis-e", "invis-v", "stt", "nda", "undo"]
DEFNAME = {"none": "none", "nospec": "NoSpecLoad", "dom": "DoM", "invis-e": "Invis-E",
           "invis-v": "Invis-V", "stt": "Taint", "nda": "NoFwd", "undo": "Undo"}
ISO = ["flush on-core state", "flush + coloring", "coloring only",
       "way partitioning", "randomized LLC"]
ISONAME = {"shared": "shared", "flush on-core state": "Flush", "flush + coloring": "Flush+Color",
           "coloring only": "Color", "way partitioning": "WayPart",
           "randomized LLC": "RandLLC"}
MACROS = {}


def rows(name):
    with open(os.path.join(RES, name)) as f:
        return list(csv.DictReader(f))


def emit(name, text):
    with open(os.path.join(OUT, name + ".tex"), "w") as f:
        f.write(text.rstrip("\n") + "\n")


def num(n):
    s = "%d" % int(n)
    out = ""
    while len(s) > 3:
        out = "\\," + s[-3:] + out
        s = s[:-3]
    return s + out


def tt(name):
    return "\\tcode{%s}" % name


def geo(ratios):
    return math.exp(sum(math.log(r) for r in ratios) / len(ratios))


def macro(key, value):
    MACROS[key] = value


def minus(cell):
    """Typeset a leading minus sign properly and never print a negative zero."""
    cell = re.sub(r"^(\\textbf\{)?-(0(\.0+)?)(\})?$", r"\1\2\4", cell)
    return re.sub(r"^(\\textbf\{)?-(\d)", r"\1$-$\2", cell)


def tabular(spec, header, body, rules=(), pre=None):
    lines = ["\\begin{tabular}{%s}" % spec, "\\toprule"]
    if pre:
        lines.append(pre)
    lines += [" & ".join(header) + " \\\\", "\\midrule"]
    for i, r in enumerate(body):
        if i in rules:
            lines.append("\\midrule")
        lines.append(" & ".join(minus(c) for c in r) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    return "\n".join(lines)


# ------------------------------------------------------------------ validation
def validation():
    r = rows("validation.csv")
    body = [[tt(x["kernel"]), "%.0f" % (int(x["image_bytes"]) / 1024), num(x["instructions"]),
             tt(x["reference"]), x["agree"]] for x in r]
    emit("tab_validation", tabular("@{}lrrlc@{}",
         ["\\textbf{Kernel}", "\\textbf{Image (KiB)}", "\\textbf{Instructions}",
          "\\textbf{Checksum}", "\\textbf{All three agree}"], body))
    macro("val.kernels", len(r))
    macro("val.instructions", num(sum(int(x["instructions"]) for x in r)))
    macro("val.instructions.m", "%.1f" % (sum(int(x["instructions"]) for x in r) / 1e6))
    u = rows("unit_tests.csv")
    unit = {"iter": "per iteration", "commit": "at commit", "switch": "per switch"}
    short = (("second-level load chain feeding a branch", "L2 load chain and branch"),
             ("slow mispredicted branch", "slow mispredict"),
             ("commit of a speculative first-level hit", "speculative first-level hit"),
             ("switch flushing the first-level data cache", "flush of L1D"),
             ("switch flushing the TLB", "flush of TLB"))
    def named(t):
        for a, b in short:
            t = t.replace(a, b)
        return re.sub(r"def=([a-z-]+)", lambda m: "no defense" if m.group(1) == "none"
                      else DEFNAME[m.group(1)], t)
    body = [[x["test"], named(x["description"]), unit[x["kind"]],
             "%.1f" % float(x["expected_cycles"]), "%.3f" % float(x["measured_cycles"]),
             x["pass"]] for x in u]
    group = lambda x: (x["kind"] if x["kind"] != "iter" else "core" if int(x["test"]) <= 15
                       else "walk" if "pages" in x["description"]
                       else "undo" if "wrong-path" in x["description"] else "defense")
    groups = [i for i in range(1, len(u)) if group(u[i]) != group(u[i - 1])]
    emit("tab_unit", tabular("@{}rllrrc@{}",
         ["\\textbf{\\#}", "\\textbf{Program under test}", "\\textbf{Cycles}",
          "\\textbf{Derived}", "\\textbf{Measured}", "\\textbf{Equal}"], body,
         rules=tuple(groups)))
    macro("val.unit", len(u))
    macro("val.unit.core", sum(1 for x in u if int(x["test"]) <= 15))
    macro("val.unit.new", sum(1 for x in u if int(x["test"]) > 15))
    inv = rows("invariants.csv")
    body = [[x["property"].capitalize(), num(x["measured"]),
             num(x["required"]) if x["required"].isdigit() else x["required"], x["holds"]] for x in inv]
    emit("tab_invariants", "\\begin{tabularx}{\\linewidth}{@{}Xrrc@{}}\n\\toprule\n"
         "\\textbf{Property} & \\textbf{Measured} & \\textbf{Required} & \\textbf{Holds} \\\\\n\\midrule\n"
         + "\n".join(" & ".join(b) + " \\\\" for b in body) + "\n\\bottomrule\n\\end{tabularx}")
    macro("val.invariants", len(inv))


# -------------------------------------------------------------------- baseline
def baseline():
    r = {x["kernel"]: x for x in rows("baseline.csv")}
    body = []
    for k in KERNELS:
        x = r[k]
        body.append([tt(k), "%.2f" % (int(x["instructions"]) / 1e6), "%.2f" % float(x["ipc"]),
                     "%.1f" % float(x["mispredict_pct"]), "%.1f" % float(x["l1_pct"]),
                     "%.1f" % float(x["l2_pct"]), "%.1f" % float(x["llc_pct"]),
                     "%.1f" % float(x["mem_pct"]), "%.2f" % float(x["amat_formula"]),
                     "%.2f" % float(x["walk_per_load"]), "%.2f" % float(x["wait_per_load"]),
                     "%.2f" % float(x["mean_load_latency"])])
        for f in ("ipc", "mispredict_pct", "l1_pct", "mean_load_latency", "amat_formula",
                  "walk_per_load", "wait_per_load", "tlb_miss_pct"):
            macro("base.%s.%s" % (k, f), "%.2f" % float(x[f]))
    emit("tab_baseline", tabular("@{}lrrr@{\\hspace{8pt}}rrrr@{\\hspace{8pt}}rrrr@{}",
         ["\\textbf{Kernel}", "\\textbf{Inst.}", "\\textbf{IPC}", "\\textbf{Mis.}",
          "\\textbf{L1}", "\\textbf{L2}", "\\textbf{LLC}", "\\textbf{Mem}",
          "\\textbf{AMAT}", "\\textbf{Walk}", "\\textbf{Wait}", "\\textbf{Mean}"], body))
    ipcs = [float(r[k]["ipc"]) for k in KERNELS]
    macro("base.ipc.geo", "%.2f" % geo(ipcs))
    macro("base.ipc.min", "%.2f" % min(ipcs))
    macro("base.ipc.max", "%.2f" % max(ipcs))
    # where the loads are served: stacked horizontal bars
    series = [("l1_pct", "L1", "defense!45"), ("l2_pct", "L2", "accent!40"),
              ("llc_pct", "LLC", "orange!55"), ("mem_pct", "memory", "attack!60")]
    plot = ["\\begin{tikzpicture}", "\\begin{axis}[xbar stacked, width=0.80\\linewidth, height=7.4cm,",
            "  bar width=7pt, xmin=0, xmax=100, enlarge y limits=0.07,",
            "  symbolic y coords={%s}, ytick=data," % ",".join(reversed(KERNELS)),
            "  yticklabels={%s}," % ",".join(tt(k) for k in reversed(KERNELS)) +
            " yticklabel style={font=\\scriptsize}, xticklabel style={font=\\scriptsize},",
            "  xlabel={share of loads served at each level (\\%)}, label style={font=\\small},",
            "  legend style={font=\\scriptsize, draw=black!25, at={(0.5,1.03)}, anchor=south,",
            "    legend columns=4}, xmajorgrids, grid style={draw=black!12}]"]
    for field, label, color in series:
        coords = " ".join("(%.3f,%s)" % (float(r[k][field]), k) for k in reversed(KERNELS))
        plot.append("\\addplot+[fill=%s, draw=black!40] coordinates {%s};" % (color, coords))
        plot.append("\\addlegendentry{%s}" % label)
    plot += ["\\end{axis}", "\\end{tikzpicture}"]
    emit("fig_service", "\n".join(plot))


def cache_sweep():
    r = rows("cache_sweep.csv")
    get = lambda k, p: [(int(x["value"]), x) for x in r if x["kernel"] == k and x["parameter"] == p]
    shown = ["heapsort", "bsearch", "bstree", "hashtab", "sieve", "listwalk"]
    marks = ["*", "square*", "triangle*", "diamond*", "o", "x"]
    plot = ["\\begin{tikzpicture}", "\\begin{groupplot}[group style={group size=2 by 1, horizontal sep=1.5cm},",
            "  width=0.50\\linewidth, height=6.0cm, ymode=log, ymin=0.05, ymax=100,",
            "  tick label style={font=\\scriptsize}, label style={font=\\small},",
            "  ymajorgrids, grid style={draw=black!12}, legend style={font=\\scriptsize, draw=black!25}]"]
    for param, xlabel, xmode in (("l1_size_kib", "first-level cache size (KiB), 8 ways", "xmode=log, log basis x=2, xtick={8,16,32,64,128}, xticklabels={8,16,32,64,128}"),
                                 ("l1_ways", "associativity at 32\\,KiB", "xmode=log, log basis x=2, xtick={1,2,4,8,16}, xticklabels={1,2,4,8,16}")):
        plot.append("\\nextgroupplot[%s, xlabel={%s}%s]" % (
            xmode, xlabel, ", ylabel={first-level miss rate (\\%)}" if param == "l1_size_kib"
            else ", legend pos=south west"))
        for k, m in zip(shown, marks):
            pts = " ".join("(%d,%.4f)" % (v, max(0.05, float(x["l1d_miss_pct"]))) for v, x in get(k, param))
            plot.append("\\addplot+[mark=%s, mark size=1.5pt, thick] coordinates {%s};" % (m, pts))
            if param == "l1_ways":
                plot.append("\\addlegendentry{\\tcode{%s}}" % k)
    plot += ["\\end{groupplot}", "\\end{tikzpicture}"]
    emit("fig_l1sweep", "\n".join(plot))
    # last-level capacity: execution time relative to the 2 MiB configuration
    shown = ["listwalk", "stream", "bsearch", "hashtab", "bstree"]
    plot = ["\\begin{tikzpicture}", "\\begin{axis}[width=0.74\\linewidth, height=6.0cm, xmode=log, log basis x=2,",
            "  xtick={256,512,1024,2048,4096}, xticklabels={0.25,0.5,1,2,4},",
            "  xlabel={last-level cache size (MiB), 16 ways}, ylabel={execution time\\\\relative to 2\\,MiB}, ylabel style={align=center},",
            "  tick label style={font=\\scriptsize}, label style={font=\\small}, ymin=0.8,",
            "  ymajorgrids, grid style={draw=black!12}, legend style={font=\\scriptsize, draw=black!25},",
            "  legend pos=north east]"]
    for k, m in zip(shown, marks):
        pts = dict(get(k, "llc_size_kib"))
        ref = int(pts[2048]["cycles"])
        plot.append("\\addplot+[mark=%s, mark size=1.5pt, thick] coordinates {%s};" % (
            m, " ".join("(%d,%.4f)" % (v, int(pts[v]["cycles"]) / ref) for v in sorted(pts))))
        plot.append("\\addlegendentry{\\tcode{%s}}" % k)
        macro("llc.half.%s" % k, "%.1f" % (100 * (int(pts[1024]["cycles"]) / ref - 1)))
        macro("llc.quarter.%s" % k, "%.1f" % (100 * (int(pts[512]["cycles"]) / ref - 1)))
    plot += ["\\end{axis}", "\\end{tikzpicture}"]
    emit("fig_llcsweep", "\n".join(plot))
    body = []
    for k in KERNELS:
        size = dict(get(k, "l1_size_kib"))
        ways = dict(get(k, "l1_ways"))
        body.append([tt(k)] + ["%.2f" % float(size[v]["l1d_miss_pct"]) for v in (8, 16, 32, 64, 128)]
                    + ["%.2f" % float(ways[v]["l1d_miss_pct"]) for v in (1, 2, 4, 8, 16)])
    emit("tab_cachesweep", tabular("@{}l@{\\hspace{10pt}}rrrrr@{\\hspace{14pt}}rrrrr@{}",
         ["\\textbf{Kernel}", "\\textbf{8}", "\\textbf{16}", "\\textbf{32}", "\\textbf{64}",
          "\\textbf{128}", "\\textbf{1}", "\\textbf{2}", "\\textbf{4}", "\\textbf{8}", "\\textbf{16}"], body,
         pre=" & \\multicolumn{5}{c}{\\textbf{size in KiB (8 ways)}}"
             " & \\multicolumn{5}{c}{\\textbf{ways (32\\,KiB)}} \\\\"))


# ------------------------------------------------------- predictors and window
def predictor_window():
    r = rows("predictor.csv")
    get = {(x["kernel"], x["predictor"]): x for x in r}
    body = []
    for k in KERNELS:
        row = [tt(k)]
        for bp in ("gshare", "bimodal", "nottaken"):
            row += ["%.1f" % float(get[(k, bp)]["mispredict_pct"]), "%.2f" % float(get[(k, bp)]["ipc"])]
        body.append(row)
        macro("bp.gshare.%s" % k, "%.1f" % float(get[(k, "gshare")]["mispredict_pct"]))
    emit("tab_predictor", tabular("@{}l@{\\hspace{12pt}}rr@{\\hspace{12pt}}rr@{\\hspace{12pt}}rr@{}",
         ["\\textbf{Kernel}", "\\textbf{mis.\\,\\%}", "\\textbf{IPC}", "\\textbf{mis.\\,\\%}",
          "\\textbf{IPC}", "\\textbf{mis.\\,\\%}", "\\textbf{IPC}"], body,
         pre=" & \\multicolumn{2}{c}{\\textbf{gshare}} & \\multicolumn{2}{c}{\\textbf{bimodal}}"
             " & \\multicolumn{2}{c}{\\textbf{static not-taken}} \\\\"))
    w = rows("window.csv")
    get = {(x["kernel"], int(x["rob"])): x for x in w}
    shown = ["bsearch", "hashtab", "bstree", "heapsort", "strsearch", "sieve"]
    marks = ["*", "square*", "triangle*", "diamond*", "o", "x"]
    plot = ["\\begin{tikzpicture}", "\\begin{groupplot}[group style={group size=2 by 1, horizontal sep=1.6cm},",
            "  width=0.48\\linewidth, height=6.0cm, xmode=log, log basis x=2,",
            "  xtick={16,32,64,128,256}, xticklabels={16,32,64,128,256},",
            "  xlabel={reorder-buffer entries}, tick label style={font=\\scriptsize},",
            "  label style={font=\\small}, ymajorgrids, grid style={draw=black!12},",
            "  legend style={font=\\scriptsize, draw=black!25}, ymin=0, ylabel style={align=center}]"]
    for field, ylabel, legend in (("executed_per_squash", "transient instructions\\\\executed per squash", False),
                                  ("loads_per_squash", "transient loads\\\\executed per squash", True)):
        plot.append("\\nextgroupplot[ylabel={%s}%s]" % (ylabel, ", legend pos=north west" if legend else ""))
        for k, m in zip(shown, marks):
            pts = " ".join("(%d,%.3f)" % (rob, float(get[(k, rob)][field])) for rob in (16, 32, 64, 128, 256))
            plot.append("\\addplot+[mark=%s, mark size=1.5pt, thick] coordinates {%s};" % (m, pts))
            if legend:
                plot.append("\\addlegendentry{\\tcode{%s}}" % k)
    plot += ["\\end{groupplot}", "\\end{tikzpicture}"]
    emit("fig_window", "\n".join(plot))
    body = []
    for k in KERNELS:
        x = get[(k, 128)]
        body.append([tt(k), num(x["squashes"]), "%.1f" % (int(x["wp_dispatched"]) / max(1, int(x["squashes"]))),
                     "%.1f" % float(x["executed_per_squash"]), "%.2f" % float(x["loads_per_squash"]),
                     num(x["wp_fills"]), num(x["wp_dependent_loads"]), num(x["wp_dependent_fills"])])
        macro("wp.exec.%s" % k, "%.1f" % float(x["executed_per_squash"]))
        macro("wp.fills.%s" % k, num(x["wp_fills"]))
        macro("wp.dep.%s" % k, num(x["wp_dependent_loads"]))
    emit("tab_window", tabular("@{}lrrrrrrr@{}",
         ["\\textbf{Kernel}", "\\textbf{Squashes}", "\\textbf{Disp.}", "\\textbf{Exec.}",
          "\\textbf{Loads}", "\\textbf{Fills}", "\\textbf{Dep.\\ loads}", "\\textbf{Dep.\\ fills}"], body))
    for k in ("bsearch", "hashtab"):
        macro("wp.exec16.%s" % k, "%.1f" % float(get[(k, 16)]["executed_per_squash"]))
        macro("wp.exec256.%s" % k, "%.1f" % float(get[(k, 256)]["executed_per_squash"]))
    body = []
    for k in KERNELS:
        for rob in (16, 32, 64, 128, 256):
            x = get[(k, rob)]
            body.append([tt(k) if rob == 16 else "", str(rob), "%.3f" % float(x["ipc"]),
                         num(x["wp_dispatched"]), num(x["wp_executed"]), num(x["wp_loads"]),
                         num(x["wp_fills"]), num(x["wp_dependent_loads"])])
    emit("tab_window_full", longtable(
        "@{}lrrrrrrr@{}", ["\\textbf{Kernel}", "\\textbf{ROB}", "\\textbf{IPC}", "\\textbf{Dispatched}",
                           "\\textbf{Executed}", "\\textbf{Loads}", "\\textbf{Fills}", "\\textbf{Dep.\\ loads}"],
        body, group=5))


def longtable(spec, header, body, group=0):
    ncol = len(header)
    head = " & ".join(header) + " \\\\"
    lines = ["\\begin{longtable}{%s}" % spec, "\\LTcaption\\\\", "\\toprule", head, "\\midrule", "\\endfirsthead",
             "\\multicolumn{%d}{@{}l}{\\footnotesize\\itshape \\tablename~\\thetable{} continued from previous page}\\\\" % ncol,
             "\\toprule", head, "\\midrule", "\\endhead",
             "\\midrule \\multicolumn{%d}{r@{}}{\\footnotesize\\itshape continued on next page}\\\\" % ncol,
             "\\endfoot", "\\bottomrule", "\\endlastfoot"]
    for i, r in enumerate(body):
        if group and i and i % group == 0:
            lines.append("\\addlinespace")
        lines.append(" & ".join(r) + " \\\\")
    lines.append("\\end{longtable}")
    return "\n".join(lines)


# -------------------------------------------------------------------- defenses
def defenses():
    r = rows("defense.csv")
    get = {(x["kernel"], x["model"], x["defense"]): x for x in r}
    for model in ("spectre", "futuristic"):
        body = []
        for k in KERNELS:
            body.append([tt(k)] + ["%.1f" % float(get[(k, model, d)]["slowdown_pct"]) for d in DEFS])
        g, worst = [], []
        for d in DEFS:
            ratios = [1 + float(get[(k, model, d)]["slowdown_pct"]) / 100 for k in KERNELS]
            g.append(100 * (geo(ratios) - 1))
            worst.append(100 * (max(ratios) - 1))
            macro("geo.%s.%s" % (model, d), "%.1f" % g[-1])
            macro("worst.%s.%s" % (model, d), "%.1f" % worst[-1])
            for k in KERNELS:
                macro("slow.%s.%s.%s" % (model, d, k), "%.1f" % float(get[(k, model, d)]["slowdown_pct"]))
                macro("speedup.%s.%s.%s" % (model, d, k), "%.1f" % -float(get[(k, model, d)]["slowdown_pct"]))
        body.append(["\\textbf{geometric mean}"] + ["\\textbf{%.1f}" % v for v in g])
        body.append(["worst kernel"] + ["%.1f" % v for v in worst])
        emit("tab_defcost_" + model, tabular("@{}l" + "r" * len(DEFS) + "@{}",
             ["\\textbf{Kernel}"] + ["\\textbf{%s}" % DEFNAME[d] for d in DEFS], body, rules=(len(KERNELS),)))
    order = list(reversed(DEFS))
    plot = ["\\begin{tikzpicture}", "\\begin{axis}[xbar, width=0.78\\linewidth, height=8.2cm, bar width=5.5pt,",
            "  xmin=-2, xmax=85, enlarge y limits=0.10,",
            "  symbolic y coords={%s}, ytick=data," % ",".join(DEFNAME[d] for d in order),
            "  yticklabel style={font=\\scriptsize}, xticklabel style={font=\\scriptsize},",
            "  xlabel={geometric-mean slowdown over the eleven kernels (\\%)}, label style={font=\\small},",
            "  nodes near coords, nodes near coords style={font=\\tiny, text=black!75},",
            "  every node near coord/.append style={/pgf/number format/fixed, /pgf/number format/precision=1},",
            "  legend style={font=\\scriptsize, draw=black!25, at={(0.97,0.05)}, anchor=south east},",
            "  xmajorgrids, grid style={draw=black!12}]"]
    for model, color, label in (("futuristic", "attack!45", "Futuristic model"),
                                 ("spectre", "accent!45", "Spectre model")):
        coords = " ".join("(%s,%s)" % (MACROS["geo.%s.%s" % (model, d)], DEFNAME[d]) for d in order)
        plot.append("\\addplot+[fill=%s, draw=black!45] coordinates {%s};" % (color, coords))
        plot.append("\\addlegendentry{%s}" % label)
    plot += ["\\end{axis}", "\\end{tikzpicture}"]
    emit("fig_overheads", "\n".join(plot))
    # residual transient footprint, summed over all kernels (Spectre model)
    fields = [("wp_loads", "Transient loads executed"), ("wp_fills", "First-level fills left behind"),
              ("wp_dependent_loads", "Dependent transient loads executed"),
              ("wp_dependent_fills", "Dependent fills left behind"),
              ("wp_hidden_fills", "Fills hidden or rolled back"),
              ("blocked_loads", "Committed loads delayed"),
              ("second_accesses", "Second (exposure) accesses")]
    total = {d: {f: sum(int(get[(k, "spectre", d)][f]) for k in KERNELS) for f, _ in fields}
             for d in ["none"] + DEFS}
    body = [[label] + [num(total[d][f]) for d in ["none"] + DEFS] for f, label in fields]
    emit("tab_footprint", "\\begin{tabularx}{\\linewidth}{@{}>{\\raggedright\\arraybackslash}X" + "r" * 8 + "@{}}\n\\toprule\n"
         + " & ".join(["\\textbf{Summed over all kernels}"] + ["\\textbf{%s}" % DEFNAME[d] for d in ["none"] + DEFS])
         + " \\\\\n\\midrule\n" + "\n".join(" & ".join(b) + " \\\\" for b in body) + "\n\\bottomrule\n\\end{tabularx}")
    for d in ["none"] + DEFS:
        for f, _ in fields:
            macro("foot.%s.%s" % (d, f), num(total[d][f]))
    # cost against what is left behind
    plot = ["\\begin{tikzpicture}", "\\begin{axis}[width=0.80\\linewidth, height=6.6cm,",
            "  xlabel={geometric-mean slowdown, Spectre model (\\%)},",
            "  ylabel={transient fills left in the cache\\\\(\\% of undefended)}, ylabel style={align=center},",
            "  xmin=-4, xmax=21, ymin=-26, ymax=120, ytick={0,20,...,120}, tick label style={font=\\scriptsize},",
            "  label style={font=\\small}, xmajorgrids, ymajorgrids, grid style={draw=black!12}]"]
    base = total["none"]["wp_fills"]
    # label positions chosen so that the two clusters of points stay legible
    anchors = {"none": "north east, xshift=-2pt, yshift=-2pt", "nospec": "south east",
               "dom": "south west", "invis-e": "north, yshift=-3pt", "invis-v": "north, yshift=-3pt",
               "stt": "south, xshift=-3pt, yshift=3pt", "nda": "west, xshift=4pt",
               "undo": "south west, xshift=1pt, yshift=1pt"}
    seen = {}
    for d in ["none"] + DEFS:
        x = 0.0 if d == "none" else float(MACROS["geo.spectre.%s" % d])
        y = 100.0 * total[d]["wp_fills"] / base
        macro("foot.pct.%s" % d, "%.1f" % y)
        mark = "*" if total[d]["wp_dependent_loads"] == 0 or d == "none" else "square*"
        color = "attack" if d == "none" else ("defense" if total[d]["wp_dependent_loads"] == 0 else "accent")
        plot.append("\\addplot[only marks, mark=%s, mark size=2.3pt, draw=%s, fill=%s] coordinates {(%.2f,%.2f)};"
                    % (mark, color, color, x, y))
        name = "no defense" if d == "none" else DEFNAME[d]
        if (x, y) in seen:                       # coincident points share one label
            plot[seen[(x, y)]] = plot[seen[(x, y)]].replace("};", ", %s};" % name)
            continue
        seen[(x, y)] = len(plot)
        plot.append("\\node[font=\\tiny, anchor=%s] at (axis cs:%.2f,%.2f) {%s};"
                    % (anchors[d], x, y, name))
    plot += ["\\end{axis}", "\\end{tikzpicture}"]
    emit("fig_pareto", "\n".join(plot))
    # memory-hierarchy traffic relative to the undefended machine
    body = []
    for d in DEFS:
        row = [DEFNAME[d]]
        for f in ("l1_accesses", "l2_accesses", "llc_accesses", "memory_accesses", "cycles"):
            new = sum(int(get[(k, "spectre", d)][f]) for k in KERNELS)
            old = sum(int(get[(k, "spectre", "none")][f]) for k in KERNELS)
            row.append("%+.1f" % (100.0 * (new / old - 1)))
            macro("traffic.%s.%s" % (d, f), "%+.1f" % (100.0 * (new / old - 1)))
        body.append(row)
    emit("tab_traffic", tabular("@{}lrrrrr@{}",
         ["\\textbf{Defense}", "\\textbf{L1 accesses}", "\\textbf{L2 accesses}", "\\textbf{LLC accesses}",
          "\\textbf{Memory accesses}", "\\textbf{Total cycles}"], body))
    # the per-kernel counts behind the sums of the footprint and traffic tables
    full = [(k, d) for k in KERNELS for d in ["none"] + DEFS]
    for model in ("spectre", "futuristic"):
        body = [[tt(k) if d == "none" else "", DEFNAME[d]] + [num(get[(k, model, d)][f]) for f, _ in fields]
                for k, d in full]
        emit("tab_footprint_full_" + model, longtable("@{}ll" + "r" * len(fields) + "@{}",
             ["\\textbf{Kernel}", "\\textbf{Mechanism}", "\\textbf{Loads}", "\\textbf{Fills}",
              "\\textbf{Dep.\\ loads}", "\\textbf{Dep.\\ fills}", "\\textbf{Hidden}", "\\textbf{Delayed}",
              "\\textbf{Second}"], body, group=len(DEFS) + 1))
        body = [[tt(k) if d == "none" else "", DEFNAME[d]] + [num(get[(k, model, d)][f]) for f in
                ("cycles", "l1_accesses", "l2_accesses", "llc_accesses", "memory_accesses")] for k, d in full]
        emit("tab_traffic_full_" + model, longtable("@{}llrrrrr@{}",
             ["\\textbf{Kernel}", "\\textbf{Mechanism}", "\\textbf{Cycles}", "\\textbf{First level}",
              "\\textbf{Second level}", "\\textbf{Last level}", "\\textbf{Memory}"], body, group=len(DEFS) + 1))


def sensitivity():
    r = rows("sensitivity.csv")
    get = {(x["parameter"], int(x["value"]), x["defense"]): x for x in r}
    body, rules, i = [], [], 0
    for param, label, values in (("width", "Width", (2, 4, 8)), ("rob", "ROB entries", (32, 64, 128, 256)),
                                 ("l1_latency", "L1 latency", (2, 4, 6))):
        if i:
            rules.append(i)
        for v in values:
            body.append(["%s = %d" % (label, v), get[(param, v, "nospec")]["baseline_geomean_ipc"]]
                        + ["%.1f" % float(get[(param, v, d)]["geomean_slowdown_pct"]) for d in DEFS])
            i += 1
            for d in DEFS:
                macro("sens.%s.%d.%s" % (param, v, d), "%.1f" % float(get[(param, v, d)]["geomean_slowdown_pct"]))
            macro("sens.%s.%d.ipc" % (param, v), "%.2f" % float(get[(param, v, "nospec")]["baseline_geomean_ipc"]))
    emit("tab_sensitivity", tabular("@{}lr" + "r" * len(DEFS) + "@{}",
         ["\\textbf{Baseline}", "\\textbf{IPC}"] + ["\\textbf{%s}" % DEFNAME[d] for d in DEFS],
         body, rules=tuple(rules)))
    plot = ["\\begin{tikzpicture}", "\\begin{groupplot}[group style={group size=2 by 1, horizontal sep=1.5cm},",
            "  width=0.50\\linewidth, height=5.8cm, tick label style={font=\\scriptsize},",
            "  label style={font=\\small}, ymajorgrids, grid style={draw=black!12}, ymin=0,",
            "  legend style={font=\\scriptsize, draw=black!25}]"]
    shown = ["nospec", "dom", "undo", "nda", "stt"]
    marks = ["*", "square*", "triangle*", "diamond*", "o"]
    for param, xlabel, values, extra in (
            ("width", "pipeline width (instructions per cycle)", (2, 4, 8),
             "xmode=log, log basis x=2, xtick={2,4,8}, xticklabels={2,4,8}, ylabel={geometric-mean slowdown (\\%)}"),
            ("rob", "reorder-buffer entries", (32, 64, 128, 256),
             "xmode=log, log basis x=2, xtick={32,64,128,256}, xticklabels={32,64,128,256}, legend style={at={(0.97,0.62)}, anchor=east}")):
        plot.append("\\nextgroupplot[%s, xlabel={%s}]" % (extra, xlabel))
        for d, m in zip(shown, marks):
            pts = " ".join("(%d,%.3f)" % (v, float(get[(param, v, d)]["geomean_slowdown_pct"])) for v in values)
            plot.append("\\addplot+[mark=%s, mark size=1.5pt, thick] coordinates {%s};" % (m, pts))
            if param == "rob":
                plot.append("\\addlegendentry{%s}" % DEFNAME[d])
    plot += ["\\end{groupplot}", "\\end{tikzpicture}"]
    emit("fig_sens", "\n".join(plot))


# ------------------------------------------------------------------- isolation
def isolation():
    r = rows("domains.csv")
    pairs = list(dict.fromkeys(x["pair"] for x in r))
    quanta = (10000, 30000, 100000, 300000)
    sel = lambda p, q, i: [x for x in r if x["pair"] == p and int(x["quantum"]) == q and x["isolation"] == i]
    stat = lambda xs, f: [float(x[f]) for x in xs]
    pname = lambda p: "\\tcode{%s}" % p.replace("+", " + ")
    body = []
    for p in pairs:
        row = [pname(p)]
        for i in ISO:
            v = stat(sel(p, 100000, i), "slowdown_pct")
            row.append("%s {\\tiny(%s to %s)}" % tuple(minus("%.1f" % t)
                       for t in (statistics.mean(v), min(v), max(v))))
            macro("iso.%s.%s" % (ISONAME[i], p), "%.1f" % statistics.mean(v))
            macro("iso.%s.%s.min" % (ISONAME[i], p), "%.1f" % min(v))
            macro("iso.%s.%s.max" % (ISONAME[i], p), "%.1f" % max(v))
        body.append(row)
    row = ["\\textbf{geometric mean}"]
    for i in ISO:
        ratios = [1 + statistics.mean(stat(sel(p, 100000, i), "slowdown_pct")) / 100 for p in pairs]
        row.append("\\textbf{%.1f}" % (100 * (geo(ratios) - 1)))
        macro("iso.%s.geo" % ISONAME[i], "%.1f" % (100 * (geo(ratios) - 1)))
    body.append(row)
    emit("tab_isolation", tabular("@{}l" + "r" * len(ISO) + "@{}",
         ["\\textbf{Pair of kernels}"] + ["\\textbf{%s}" % ISONAME[i] for i in ISO], body, rules=(len(pairs),)))
    # flushing: slowdown against the length of the time slice
    marks = ["*", "square*", "triangle*", "diamond*", "o"]
    plot = ["\\begin{tikzpicture}", "\\begin{groupplot}[group style={group size=2 by 1, horizontal sep=1.7cm},",
            "  width=0.48\\linewidth, height=6.0cm, xmode=log, tick label style={font=\\scriptsize},",
            "  xlabel={time slice (instructions)}, label style={font=\\small},",
            "  ymajorgrids, grid style={draw=black!12}, legend style={font=\\scriptsize, draw=black!25}, ylabel style={align=center}]"]
    plot.append("\\nextgroupplot[ymode=log, ylabel={slowdown from flushing\\\\on-core state (\\%)}]")
    for p, m in zip(pairs, marks):
        pts = " ".join("(%d,%.4f)" % (q, statistics.mean(stat(sel(p, q, ISO[0]), "slowdown_pct"))) for q in quanta)
        plot.append("\\addplot+[mark=%s, mark size=1.5pt, thick] coordinates {%s};" % (m, pts))
    plot.append("\\nextgroupplot[ylabel={extra cycles per switch}, ymin=0, legend pos=north west]")
    for p, m in zip(pairs, marks):
        pts = " ".join("(%d,%.1f)" % (q, statistics.mean(stat(sel(p, q, ISO[0]), "extra_cycles_per_switch")))
                       for q in quanta)
        plot.append("\\addplot+[mark=%s, mark size=1.5pt, thick] coordinates {%s};" % (m, pts))
        plot.append("\\addlegendentry{\\tcode{%s}}" % p)
    plot += ["\\end{groupplot}", "\\end{tikzpicture}"]
    emit("fig_flushq", "\n".join(plot))
    per = [statistics.mean(stat(sel(p, q, ISO[0]), "extra_cycles_per_switch")) for p in pairs for q in quanta]
    macro("flush.perswitch.min", num(round(min(per))))
    macro("flush.perswitch.max", num(round(max(per))))
    macro("flush.perswitch.mean", num(round(statistics.mean(per))))
    macro("flush.extrap.min", "%.3f" % (100.0 * min(per) / 1e7))    # 10^7-cycle time slice
    macro("flush.extrap.max", "%.3f" % (100.0 * max(per) / 1e7))
    for p in pairs:
        for q in quanta:
            macro("flush.%d.%s" % (q, p), "%.2f" % statistics.mean(stat(sel(p, q, ISO[0]), "slowdown_pct")))
    # what one domain can do to, and learn about, the other
    fields = [("l1d_cross_evictions", "L1D"), ("l2_cross_evictions", "L2"), ("llc_cross_evictions", "LLC"),
              ("tlb_cross_evictions", "TLB"), ("cross_predictions", "Pred."),
              ("residue_l1d", "L1D"), ("residue_tlb", "TLB"), ("residue_btb", "BTB"), ("residue_pht", "PHT")]
    body = []
    for i in ["shared"] + ISO:
        row = [ISONAME[i] if i != "shared" else "No isolation"]
        for f, _ in fields:
            xs = [x for x in r if int(x["quantum"]) == 100000 and x["isolation"] == i]
            if f.startswith("residue"):
                row.append("%.0f" % statistics.mean(stat(xs, f)))
            else:
                row.append("%.0f" % statistics.mean(float(x[f]) / int(x["switches"]) for x in xs))
            macro("inter.%s.%s" % (ISONAME[i], f), row[-1])
        body.append(row)
    emit("tab_interference", tabular("@{}l@{\\hspace{10pt}}rrrrr@{\\hspace{14pt}}rrrr@{}",
         ["\\textbf{Mechanism}"] + ["\\textbf{%s}" % n for _, n in fields], body, rules=(1,),
         pre=" & \\multicolumn{5}{c}{\\textbf{cross-domain evictions and uses}}"
             " & \\multicolumn{4}{c}{\\textbf{state left behind}} \\\\"))
    body = []
    for p in pairs:
        for i in ISO:
            row = [pname(p) if i == ISO[0] else "", ISONAME[i]]
            for q in quanta:
                v = stat(sel(p, q, i), "slowdown_pct")
                row.append("%.2f" % statistics.mean(v))
            v = stat(sel(p, 100000, i), "extra_cycles_per_switch")
            row.append(num(round(statistics.mean(v))))
            body.append(row)
    emit("tab_domains_full", longtable("@{}llrrrrr@{}",
         ["\\textbf{Pair}", "\\textbf{Mechanism}", "\\textbf{10\\,k}", "\\textbf{30\\,k}", "\\textbf{100\\,k}",
          "\\textbf{300\\,k}", "\\textbf{Cycles/switch}"], body, group=len(ISO)))
    s = rows("seeds.csv")
    body = []
    for k in KERNELS:
        c = [int(x["cycles"]) for x in s if x["kernel"] == k and x["defense"] == "none"]
        d = [float(x["slowdown_pct"]) for x in s if x["kernel"] == k and x["defense"] == "dom"]
        t = [float(x["slowdown_pct"]) for x in s if x["kernel"] == k and x["defense"] == "stt"]
        spread = 100.0 * (max(c) - min(c)) / statistics.mean(c)
        body.append([tt(k), num(min(c)), num(max(c)), "%.2f" % spread,
                     "%.1f to %.1f" % (min(d), max(d)), "%.1f to %.1f" % (min(t), max(t))])
        macro("seed.spread.%s" % k, "%.1f" % spread)
    emit("tab_seeds", tabular("@{}lrrrrr@{}",
         ["\\textbf{Kernel}", "\\textbf{Fewest cycles}", "\\textbf{Most cycles}", "\\textbf{Spread (\\%)}",
          "\\textbf{DoM (\\%)}", "\\textbf{Taint (\\%)}"], body))
    layouts = sorted({int(x["seed"]) for x in s})
    pick = {(x["kernel"], int(x["seed"]), x["defense"]): x for x in s}
    body = [[tt(k) if n == layouts[0] else "", str(n), num(pick[(k, n, "none")]["cycles"]),
             num(pick[(k, n, "none")]["memory_accesses"]), minus("%.2f" % float(pick[(k, n, "dom")]["slowdown_pct"])),
             minus("%.2f" % float(pick[(k, n, "stt")]["slowdown_pct"]))] for k in KERNELS for n in layouts]
    emit("tab_seeds_full", longtable("@{}lrrrrr@{}",
         ["\\textbf{Kernel}", "\\textbf{Layout}", "\\textbf{Cycles}", "\\textbf{Memory accesses}",
          "\\textbf{DoM (\\%)}", "\\textbf{Taint (\\%)}"], body, group=len(layouts)))


def randomized():
    r = rows("random.csv")
    get = {(x["kernel"], x["mode"], int(x["accesses_per_remapped_set"])): x for x in r}
    body, ratios = [], []
    for k in KERNELS:
        row = [tt(k), num(get[(k, "none", 0)]["llc_accesses"]),
               "%.2f" % float(get[(k, "static key, no latency", 0)]["slowdown_pct"])]
        for remap in (6400, 1600, 400, 100):
            row.append("%.2f" % float(get[(k, "remapped", remap)]["slowdown_pct"]))
        row.append(num(get[(k, "remapped", 1600)]["remap_evictions"]))
        body.append(row)
        ratios.append(1 + float(get[(k, "remapped", 1600)]["slowdown_pct"]) / 100)
        macro("rand.1600.%s" % k, "%.2f" % float(get[(k, "remapped", 1600)]["slowdown_pct"]))
        macro("rand.100.%s" % k, "%.1f" % float(get[(k, "remapped", 100)]["slowdown_pct"]))
    macro("rand.1600.geo", "%.2f" % (100 * (geo(ratios) - 1)))
    macro("rand.1600.worst", "%.1f" % (100 * (max(ratios) - 1)))
    macro("rand.100.worst", "%.1f" % max(float(get[(k, "remapped", 100)]["slowdown_pct"]) for k in KERNELS))
    emit("tab_random", tabular("@{}lrrrrrrr@{}",
         ["\\textbf{Kernel}", "\\textbf{LLC acc.}", "\\textbf{Static}", "\\textbf{6400}", "\\textbf{1600}",
          "\\textbf{400}", "\\textbf{100}", "\\textbf{Evictions}"], body,
         pre=" & & & \\multicolumn{4}{c}{\\textbf{accesses per remapped set}} & \\\\"))


def composition():
    r = rows("composition.csv")
    sg = lambda v: "0.0" if round(v, 1) == 0 else "%+.1f" % v     # no signed zeros in the table
    body, inter = [], []
    for x in r:
        lo, hi = float(x["excess_min_pct"]), float(x["excess_max_pct"])
        body.append(["\\tcode{%s}" % x["pair"].replace("+", " + "), ISONAME[x["isolation"]],
                     DEFNAME[x["speculation_defense"]], "%.1f" % float(x["s_a_pct"]),
                     "%.1f" % float(x["s_b_pct"]), "%.1f" % float(x["s_ab_pct"]),
                     "%.1f" % float(x["product_pct"]), sg(float(x["excess_pct"])),
                     "$%s$ to $%s$" % (sg(lo), sg(hi))])
        inter.append(float(x["excess_pct"]))
    emit("tab_composition", tabular("@{}lllrrrrrr@{}",
         ["\\textbf{Pair}", "\\textbf{A}", "\\textbf{B}", "$\\boldsymbol{S_A}$", "$\\boldsymbol{S_B}$",
          "$\\boldsymbol{S_{AB}}$",
          "\\textbf{Product}", "\\textbf{Excess}", "\\textbf{over layouts}"], body,
         rules=(5, 10, 15, 20)))
    over = [x for x in r if abs(float(x["excess_pct"])) > 1.0]
    macro("comp.n", len(r))
    macro("comp.maxabs", "%.1f" % max(abs(v) for v in inter))
    macro("comp.within1", sum(1 for v in inter if abs(v) <= 1.0))
    macro("comp.withinsum1", sum(1 for x in r if abs(float(x["excess_over_sum_pct"])) <= 1.0))
    macro("comp.over1", len(over))
    macro("comp.stable", sum(1 for x in over
                             if float(x["excess_min_pct"]) * float(x["excess_max_pct"]) > 0))
    macro("comp.max", "%+.1f" % max(inter))
    macro("comp.min", "%+.1f" % min(inter))
    big = [x for x in r if min(float(x["s_a_pct"]), float(x["s_b_pct"])) >= 1.0]   # neither part is negligible
    macro("comp.small", len(r) - len(big))
    macro("comp.big", len(big))
    macro("comp.big.prod1", sum(1 for x in big if abs(float(x["excess_pct"])) <= 1.0))
    macro("comp.big.sum1", sum(1 for x in big if abs(float(x["excess_over_sum_pct"])) <= 1.0))


def channel():
    """The binary timing channel of Appendix E: pure arithmetic, no simulation."""
    q = lambda x: 0.5 * math.erfc(x / math.sqrt(2.0))
    h2 = lambda e: 0.0 if e in (0.0, 1.0) else -e * math.log2(e) - (1 - e) * math.log2(1 - e)

    def majority_error(n, e):
        total = 0.0
        for k in range((n + 1) // 2, n + 1):
            total += math.exp(math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
                              + k * math.log(e) + (n - k) * math.log(1 - e))
        return total

    def repetitions(e, target):
        n = 1
        while majority_error(n, e) > target:
            n += 2
        return n

    body = []
    for d in (0.5, 1.0, 2.0, 3.0, 4.0, 6.0):
        e = q(d / 2.0)
        body.append(["%.1f" % d, "%.4f" % e, "%.3f" % (1 - h2(e)),
                     num(repetitions(e, 1e-3)), num(repetitions(e, 1e-6))])
        key = "%g" % d
        macro("chan.eps.%s" % key, "%.3f" % e)
        macro("chan.cap.%s" % key, "%.2f" % (1 - h2(e)))
        macro("chan.n6.%s" % key, num(repetitions(e, 1e-6)))
    emit("tab_channel", tabular("@{}rrrrr@{}",
         ["$d = \\Delta/\\sigma$", "$\\varepsilon = Q(d/2)$", "$C$ (bits)",
          "$n$ for $10^{-3}$", "$n$ for $10^{-6}$"], body))
    pts = " ".join("(%.2f,%.4f)" % (d / 10.0, 1 - h2(q(d / 20.0))) for d in range(0, 81, 2))
    emit("fig_capacity", "\n".join([
        "\\begin{tikzpicture}", "\\begin{axis}[width=0.66\\linewidth, height=5.2cm, xmin=0, xmax=8, ymin=0, ymax=1.05,",
        "  xlabel={separation $d = \\Delta/\\sigma$}, ylabel={capacity\\\\(bits per observation)}, ylabel style={align=center},",
        "  tick label style={font=\\scriptsize}, label style={font=\\small},",
        "  xmajorgrids, ymajorgrids, grid style={draw=black!12}]",
        "\\addplot[thick, accent] coordinates {%s};" % pts, "\\end{axis}", "\\end{tikzpicture}"]))


def manifest():
    m = json.load(open(os.path.join(RES, "manifest.json")))
    body = [[tt(f.replace("_", "\\_")), tt(h[:32])] for f, h in sorted(m["sources_sha256"].items())]
    emit("tab_manifest", tabular("@{}ll@{}", ["\\textbf{Source file}",
         "\\textbf{SHA-256 (first 32 hexadecimal digits)}"], body))
    macro("tool.qemu", m["qemu"].replace("QEMU emulator version ", ""))
    macro("tool.cc", m["cc"])
    macro("tool.python", m["python"])


def write_macros():
    lines = ["%% Numbers of the model study, generated by study/make_fragments.py."]
    for key in sorted(MACROS):
        lines.append("\\expandafter\\def\\csname R@%s\\endcsname{%s}" % (key, MACROS[key]))
    emit("macros", "\n".join(lines))


def main():
    os.makedirs(OUT, exist_ok=True)
    validation()
    baseline()
    cache_sweep()
    predictor_window()
    defenses()
    sensitivity()
    isolation()
    randomized()
    composition()
    channel()
    manifest()
    write_macros()
    print("wrote %d fragments and %d macros to %s" % (len(os.listdir(OUT)), len(MACROS), OUT))


if __name__ == "__main__":
    main()

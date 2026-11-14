#!/usr/bin/env python3
"""readability.py - reading indices for the body prose of the term paper.

Reads the single LaTeX source, extracts the running prose of Chapters 1-12,
and writes the tables and numbers that Appendix B embeds.

    python3 tools/readability.py
"""
import math
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SOURCE = os.path.join(ROOT, "RISCV_Microarch_Security_TermPaper_Final.tex")
OUT = os.path.join(ROOT, "study", "build", "fragments")

DROPPED = ["figure", "table", "lstlisting", "equation", "tocmapbox", "tabularx",
           "tabular", "tikzpicture", "longtable"]
WORDS = {"etal": "et al", "eg": "eg", "ie": "ie", "uarch": "microarchitecture",
         "Uarch": "Microarchitecture", "uarchadj": "microarchitectural",
         "Uarchadj": "Microarchitectural", "uarchadv": "microarchitecturally",
         "pc": " percent", "LaTeX": "LaTeX", "S": "section "}


def prose(tex):
    """Reduce LaTeX to plain sentences."""
    tex = re.sub(r"(?<!\\)%.*", "", tex)
    for env in DROPPED:
        tex = re.sub(r"\\begin\{%s\*?\}.*?\\end\{%s\*?\}" % (env, env), " ", tex, flags=re.S)
    tex = re.sub(r"\\(chapter|section|subsection)\*?\{[^{}]*(\{[^{}]*\}[^{}]*)*\}", "\n\n", tex)
    tex = re.sub(r"\\(label|index|glsadd)\{[^{}]*\}", "", tex)
    tex = re.sub(r"\\icode\|[^|]*\|", "code", tex)
    tex = re.sub(r"~?\\citep?\{[^{}]*\}", "", tex)
    tex = re.sub(r"\\citet\{[^{}]*\}", "they", tex)
    tex = re.sub(r"\\[Cc]ref\{[^{}]*\}", "ref", tex)
    tex = re.sub(r"\\SecRef\{[^{}]*\}", "section", tex)
    tex = re.sub(r"\\R\{[^{}]*\}", "ten", tex)
    tex = re.sub(r"\\(code|tcode|texttt|url|nolinkurl)\{[^{}]*\}", "code", tex)
    tex = re.sub(r"\$[^$]*\$", "x", tex)
    tex = re.sub(r"\\(begin|end)\{[^{}]*\}(\[[^\]]*\])?", " ", tex)
    tex = re.sub(r"\\item(\[[^\]]*\])?", " ", tex)
    tex = tex.replace("\\%", " percent").replace("\\&", "and").replace("\\_", "")
    tex = tex.replace("\\,", " ").replace("~", " ").replace("\\\\", " ")
    tex = re.sub(r"\\([A-Za-z]+)\b\s*(\{\})?",
                 lambda m: WORDS.get(m.group(1), ""), tex)
    tex = re.sub(r"[{}\\]", "", tex).replace("--", " ").replace("``", '"').replace("''", '"')
    for abbr in ("et al.", "e.g.", "i.e.", "etc.", "vs."):
        tex = tex.replace(abbr, abbr.replace(".", ""))
    return tex


def sentences(text):
    out = []
    for para in re.split(r"\n\s*\n", text):
        para = " ".join(para.split())
        for s in re.split(r"(?<=[.!?])[\"')]*\s+(?=[\"(]*[A-Z])", para):
            if re.search(r"[A-Za-z]", s):
                out.append(s)
    return out


def syllables(word):
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 1
    n = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and not re.search(r"[^aeiouy]le$", w) and n > 1:
        n -= 1
    return max(n, 1)


def counts(text):
    sents = sentences(text)
    words = [w for s in sents for w in re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*", s)]
    letters = sum(len(re.sub(r"[^A-Za-z0-9]", "", w)) for w in words)
    syl = [sum(syllables(p) for p in w.split("-")) for w in words]
    return {"S": len(sents), "W": len(words), "Y": sum(syl), "C": letters,
            "P": sum(1 for s in syl if s >= 3),
            "L": sum(1 for w in words if len(re.sub(r"[^A-Za-z0-9]", "", w)) > 6),
            "L6": sum(1 for w in words if len(re.sub(r"[^A-Za-z0-9]", "", w)) >= 6)}


def indices(c):
    wps, ypw = c["W"] / c["S"], c["Y"] / c["W"]
    return {
        "fre": 206.835 - 1.015 * wps - 84.6 * ypw,
        "fk": 0.39 * wps + 11.8 * ypw - 15.59,
        "fog": 0.4 * (wps + 100.0 * c["P"] / c["W"]),
        "smog": 1.0430 * math.sqrt(30.0 * c["P"] / c["S"]) + 3.1291,
        "cli": 0.0588 * (100.0 * c["C"] / c["W"]) - 0.296 * (100.0 * c["S"] / c["W"]) - 15.8,
        "ari": 4.71 * c["C"] / c["W"] + 0.5 * wps - 21.43,
        "lix": wps + 100.0 * c["L"] / c["W"],
        "rix": c["L"] / c["S"],
    }


# Grade bands of the reference page named in the course guidelines
# (analyzemywriting.com/readability_indices.html): lower bound, readers.
BANDS = [(16, "graduate and professional readers (grade 16 and above)"),
         (12, "undergraduate readers (grades 12 to 16)"),
         (8, "general adult readers (grades 8 to 12)"),
         (5, "young adult readers (grades 5 to 8)"),
         (3, "children's texts (grades 3 to 5)"),
         (-99, "emergent and early readers (grade 3 and below)")]


def band(grade):
    return next(text for low, text in BANDS if grade >= low)


def longest_unit(body):
    """Words of running prose under the longest single heading of Chapters 1-12."""
    parts = re.split(r"^\\(?:chapter|section|subsection|subsubsection|paragraph)\*?\{", body, flags=re.M)
    best = 0
    for part in parts:
        text = prose(part)
        best = max(best, len(re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*", text)))
    return best


def num(n):
    s, out = "%d" % n, ""
    while len(s) > 3:
        out, s = "\\," + s[-3:] + out, s[:-3]
    return s + out


def emit(name, text):
    with open(os.path.join(OUT, name + ".tex"), "w") as f:
        f.write(text.rstrip("\n") + "\n")


def main():
    tex = open(SOURCE).read()
    body = tex[tex.index("\\chapter{Introduction and Scope}"):tex.index("\\appendix")]
    c = counts(prose(body))
    ix = indices(c)
    rows = [("Sentences ($S$)", num(c["S"])), ("Words ($W$)", num(c["W"])),
            ("Syllables ($Y$)", num(c["Y"])), ("Words of three syllables or more ($P$)", num(c["P"])),
            ("Words longer than six letters ($L$)", num(c["L"])), ("Letters ($C$)", num(c["C"])),
            ("Words per sentence", "%.2f" % (c["W"] / c["S"])),
            ("Syllables per word", "%.3f" % (c["Y"] / c["W"])),
            ("Syllables per 100 words (Fry graph)", "%.1f" % (100.0 * c["Y"] / c["W"])),
            ("Sentences per 100 words (Fry graph, Raygor estimate)", "%.2f" % (100.0 * c["S"] / c["W"])),
            ("Words of six or more letters per 100 words (Raygor estimate)", "%.1f" % (100.0 * c["L6"] / c["W"]))]
    emit("read_counts", "\\begin{tabular}{@{}lr@{}}\n\\toprule\n\\textbf{Quantity} & \\textbf{Value} \\\\\n\\midrule\n"
         + "\n".join("%s & %s \\\\" % r for r in rows) + "\n\\bottomrule\n\\end{tabular}")
    five = sorted(ix[k] for k in ("fk", "fog", "smog", "cli", "ari"))
    mean, median = sum(five) / 5.0, five[2]
    table = [
        ("FRE (Flesch)", "$206.835 - 1.015\\,W/S - 84.6\\,Y/W$", ix["fre"], "higher is easier"),
        ("FKGL (Kincaid \\etal)", "$0.39\\,W/S + 11.8\\,Y/W - 15.59$", ix["fk"], "school grade"),
        ("Fog (Gunning)", "$0.4\\,(W/S + 100\\,P/W)$", ix["fog"], "years of schooling"),
        ("SMOG (McLaughlin)", "$1.043\\sqrt{30\\,P/S} + 3.1291$", ix["smog"], "school grade"),
        ("CLI (Coleman, Liau)", "$5.88\\,C/W - 29.6\\,S/W - 15.8$", ix["cli"], "school grade"),
        ("ARI (Smith, Senter)", "$4.71\\,C/W + 0.5\\,W/S - 21.43$", ix["ari"], "school grade"),
        ("LIX (Bj\\\"{o}rnsson)", "$W/S + 100\\,L/W$", ix["lix"], "50 to 60: difficult"),
        ("RIX (Anderson)", "$L/S$", ix["rix"], "from 7.2: college"),
    ]
    emit("read_indices", "\\begin{tabular}{@{}lrll@{}}\n\\toprule\n\\textbf{Index} & \\textbf{Value} & "
         "\\textbf{Scale} & \\textbf{Formula} \\\\\n\\midrule\n"
         + "\n".join("%s & %.1f & %s & %s \\\\" % (r[0], r[2], r[3], r[1]) for r in table) + "\n\\midrule\n"
         + "Average grade & %.1f & school grade & mean of the five grade levels \\\\\n" % mean
         + "Median grade & %.1f & school grade & median of the five grade levels \\\\\n" % median
         + "\\bottomrule\n\\end{tabular}")
    chapters = re.split(r"(?=\\chapter\{)", body)
    lines = []
    for i, ch in enumerate([x for x in chapters if x.startswith("\\chapter{")], 1):
        cc = counts(prose(ch))
        ii = indices(cc)
        lines.append("%d & %s & %s & %.1f & %.1f & %.1f \\\\" % (
            i, num(cc["W"]), num(cc["S"]), cc["W"] / cc["S"], ii["fre"], ii["fk"]))
    lines.append("\\midrule\nAll & %s & %s & %.1f & %.1f & %.1f \\\\" % (
        num(c["W"]), num(c["S"]), c["W"] / c["S"], ix["fre"], ix["fk"]))
    emit("read_chapters", "\\begin{tabular}{@{}rrrrrr@{}}\n\\toprule\n\\textbf{Chapter} & \\textbf{Words} & "
         "\\textbf{Sentences} & \\textbf{Words per sentence} & \\textbf{Reading Ease} & "
         "\\textbf{Flesch-Kincaid} \\\\\n\\midrule\n" + "\n".join(lines) + "\n\\bottomrule\n\\end{tabular}")
    grades = [ix[k] for k in ("fk", "fog", "smog", "cli", "ari")]
    macros = {"read.fre": "%.1f" % ix["fre"], "read.grade.min": "%.1f" % min(grades),
              "read.grade.max": "%.1f" % max(grades), "read.wps": "%.1f" % (c["W"] / c["S"]),
              "read.poly.pct": "%.1f" % (100.0 * c["P"] / c["W"]), "read.words": num(c["W"]),
              "read.grade.mean": "%.1f" % mean, "read.grade.median": "%.1f" % median,
              "read.grade.band": band(mean), "read.sentences": num(c["S"]),
              "read.unit.max": num(longest_unit(body))}
    emit("read_macros", "\n".join("\\expandafter\\def\\csname R@%s\\endcsname{%s}" % kv
                                  for kv in sorted(macros.items())))
    print("body prose: %d words, %d sentences; FRE %.1f, FK %.1f; grade mean %.1f, median %.1f; "
          "longest unit %d words" % (c["W"], c["S"], ix["fre"], ix["fk"], mean, median, longest_unit(body)))


if __name__ == "__main__":
    main()

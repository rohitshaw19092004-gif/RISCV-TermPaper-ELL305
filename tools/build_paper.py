#!/usr/bin/env python3
"""build_paper.py - compile the term paper with Tectonic.

Tectonic runs LaTeX and BibTeX to a fixed point by itself but has no index
processor. If a `makeindex` binary is on the PATH it is used; otherwise the
small routine below produces the same .ind file from the .idx file. On a full
TeX distribution none of this is needed: `latexmk -pdf` builds the paper.

    python3 tools/build_paper.py            # builds the PDF next to the .tex
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NAME = "RISCV_Microarch_Security_TermPaper_Final"
WORK = os.path.join(ROOT, "build", "tex")


def sort_key(text):
    plain = re.sub(r"\\[a-zA-Z]+|[{}$\\]", "", text).lower()
    plain = re.sub(r"[^a-z0-9 ]", "", plain).strip()
    return (0 if plain[:1].isdigit() or not plain else 1, plain)


def make_index(idx_path, ind_path):
    """A minimal makeindex: levels (!), sort keys (@) and page ranges."""
    entries = {}
    pattern = re.compile(r"\\indexentry\s*\{(.*)\}\{(\d+)\}\s*$")
    for line in open(idx_path):
        m = pattern.match(line.strip())
        if not m:
            continue
        key, page = m.group(1).split("|")[0], int(m.group(2))
        levels = []
        for part in key.split("!"):
            sort, _, shown = part.partition("@")
            levels.append((sort_key(sort), shown or sort))
        entries.setdefault(tuple(levels), set()).add(page)

    def pages(ps):
        ps, out, i = sorted(ps), [], 0
        while i < len(ps):
            j = i
            while j + 1 < len(ps) and ps[j + 1] == ps[j] + 1:
                j += 1
            out.append("%d--%d" % (ps[i], ps[j]) if j - i >= 2 else
                       ", ".join(str(p) for p in ps[i:j + 1]))
            i = j + 1
        return ", ".join(out)

    lines, last_top, last_sub, last_letter = ["\\begin{theindex}", ""], None, None, None
    for levels in sorted(entries, key=lambda ls: [l[0] for l in ls]):
        top = levels[0]
        letter = top[0][1][:1] if top[0][0] else "#"
        if letter != last_letter and last_letter is not None:
            lines += ["", "  \\indexspace", ""]
        last_letter = letter
        if len(levels) == 1:
            lines.append("  \\item %s, %s" % (top[1], pages(entries[levels])))
        else:
            if top != last_top and (top,) not in entries:
                lines.append("  \\item %s" % top[1])
            if len(levels) == 2:
                lines.append("    \\subitem %s, %s" % (levels[1][1], pages(entries[levels])))
            else:
                if levels[:2] != last_sub and levels[:2] not in entries:
                    lines.append("    \\subitem %s" % levels[1][1])
                lines.append("      \\subsubitem %s, %s" % (levels[2][1], pages(entries[levels])))
        last_top, last_sub = top, levels[:2]
    lines += ["", "\\end{theindex}", ""]
    with open(ind_path, "w") as f:
        f.write("\n".join(lines))
    return len(entries)


def tectonic():
    cmd = ["tectonic", "-X", "compile", "--keep-intermediates", "--keep-logs", NAME + ".tex"]
    r = subprocess.run(cmd, cwd=WORK, capture_output=True, text=True)
    if r.returncode:
        sys.stderr.write(r.stdout[-3000:] + r.stderr[-6000:])
        sys.exit("tectonic failed")
    return r.stderr


def main():
    os.makedirs(WORK, exist_ok=True)
    shutil.copy(os.path.join(ROOT, NAME + ".tex"), WORK)
    ind = os.path.join(WORK, NAME + ".ind")
    previous = None
    for attempt in range(4):
        tectonic()
        idx = os.path.join(WORK, NAME + ".idx")
        if shutil.which("makeindex"):
            subprocess.run(["makeindex", "-q", NAME + ".idx"], cwd=WORK, check=True)
        else:
            make_index(idx, ind)
        current = open(ind).read()
        if current == previous:
            break
        previous = current
    shutil.copy(os.path.join(WORK, NAME + ".pdf"), ROOT)
    log = open(os.path.join(WORK, NAME + ".log"), errors="replace").read()
    pages = re.findall(r"Output written on .*?\((\d+) pages", log)
    undefined = sorted(set(re.findall(r"(?:Reference|Citation) `([^']+)' on page", log)))
    overfull = re.findall(r"Overfull \\hbox \(([\d.]+)pt too wide\)", log)
    print("pages: %s   passes: %d" % (pages[-1] if pages else "?", attempt + 1))
    print("undefined references/citations: %d %s" % (len(undefined), undefined[:12]))
    worst = max((float(x) for x in overfull), default=0.0)
    print("overfull boxes: %d (worst %.1fpt)" % (len(overfull), worst))


if __name__ == "__main__":
    main()

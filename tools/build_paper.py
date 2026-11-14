#!/usr/bin/env python3
"""build_paper.py - compile the term paper and report on the result.

With a full TeX distribution on the PATH the paper is built by `latexmk -pdf`,
that is pdfLaTeX, BibTeX and makeindex, in a scratch directory, so that the
repository root receives only the PDF. Without one, or with --tectonic, the
paper is built with Tectonic. Tectonic runs LaTeX and BibTeX to a fixed point by
itself but has no index processor, so the small routine below produces the .ind
file when no `makeindex` binary is available.

    python3 tools/build_paper.py              # latexmk if installed, else Tectonic
    python3 tools/build_paper.py --tectonic   # force Tectonic
"""
import collections
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NAME = "RISCV_Microarch_Security_TermPaper_Final"
WORK = os.path.join(ROOT, "build", "tex")          # Tectonic
WORK_TL = os.path.join(ROOT, "build", "texlive")   # latexmk


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


def latexmk():
    """pdfLaTeX + BibTeX + makeindex to a fixed point; returns the pdfLaTeX passes."""
    cmd = ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error",
           "-file-line-error", NAME + ".tex"]
    r = subprocess.run(cmd, cwd=WORK_TL, capture_output=True, text=True, errors="replace")
    out = r.stdout + r.stderr
    if r.returncode:
        sys.stderr.write(out[-6000:])
        sys.exit("latexmk failed")
    return len(re.findall(r"Run number \d+ of rule 'pdflatex'", out))


def report(work, engine, passes):
    shutil.copy(os.path.join(work, NAME + ".pdf"), ROOT)
    log = open(os.path.join(work, NAME + ".log"), errors="replace").read()
    pages = re.findall(r"Output written on .*?\((\d+) pages", log.replace("\n", ""))
    undefined = sorted(set(re.findall(r"(?:Reference|Citation) `([^']+)' on page", log)))
    overfull = re.findall(r"Overfull \\hbox \(([\d.]+)pt too wide\)", log)
    print("engine: %s" % engine)
    print("pages: %s   passes: %s" % (pages[-1] if pages else "?", passes))
    print("undefined references/citations: %d %s" % (len(undefined), undefined[:12]))
    worst = max((float(x) for x in overfull), default=0.0)
    print("overfull boxes: %d (worst %.1fpt)" % (len(overfull), worst))
    readiness(work)


def unreferenced_floats(body):
    """Labels of figures, tables and listings without a reference in the text.
    A \\crefrange covers every label of its kind between its two ends."""
    where = {}
    for m in re.finditer(r"\\label\{((?:fig|tab):[^}]*)\}|label=\{?(lst:[A-Za-z0-9_.-]+)", body):
        where[m.group(1) or m.group(2)] = m.start()
    used = set()
    for m in re.finditer(r"\\(?:[Cc]ref|ref|pageref|autoref)\*?\{([^}]*)\}", body):
        used.update(k.strip() for k in m.group(1).split(","))
    for m in re.finditer(r"\\[Cc]refrange\{([^}]*)\}\{([^}]*)\}", body):
        a, b = m.group(1).strip(), m.group(2).strip()
        if a in where and b in where:
            lo, hi = sorted((where[a], where[b]))
            used.update(n for n, pos in where.items()
                        if lo <= pos <= hi and n.split(":")[0] == a.split(":")[0])
    return sorted(n for n in where if n not in used)


def _gs_text_pages(gs, pdf):
    """Per-page spans (x0, baseline y, x1, font, size, text) from Ghostscript's
    txtwrite device, which reports positions in points from the top-left corner."""
    import tempfile
    import xml.etree.ElementTree as ET
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "text.xml")
        subprocess.run([gs, "-q", "-dNOPAUSE", "-dBATCH", "-sDEVICE=txtwrite", "-dTextFormat=0",
                        "-sOutputFile=" + out, pdf], check=True, capture_output=True)
        raw = open(out, errors="replace").read()
    raw = re.sub(r"<\?xml[^>]*\?>", "", raw)

    def bad_ref(m):      # character references that XML 1.0 does not allow
        s = m.group(1)
        code = int(s[1:], 16) if s[:1] in "xX" else int(s)
        return " " if code < 32 or 0xD800 <= code <= 0xDFFF or code > 0x10FFFF else m.group(0)

    raw = re.sub(r"&#([xX]?[0-9a-fA-F]+);", bad_ref, raw)
    pages = []
    for page in ET.fromstring("<doc>" + raw + "</doc>").findall("page"):
        spans = []
        for s in page.findall("span"):
            b = [float(v) for v in s.get("bbox").split()]
            spans.append((b[0], b[1], b[2], s.get("font", "").split("+", 1)[-1],
                          float(s.get("size", "0")), "".join(c.get("c", "") for c in s.findall("char"))))
        pages.append(spans)
    return pages


def rendered_audit(pdf, pages=None):
    """Layout checks on the compiled PDF itself, made with Ghostscript: A4 page
    size, the 1 inch margins, and the half-page rule as a reader sees it. The
    word count in readiness() cannot see equations, lists or boxes; this measures
    the height of the body text under each (run-in) heading instead."""
    gs = shutil.which("gs")
    if not gs:
        print("rendered layout audit skipped: Ghostscript (gs) not found")
        return None
    inch, a4 = 72.0, (595.276, 841.89)
    escaped = pdf.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    sizes = subprocess.run(
        [gs, "-q", "-dNODISPLAY", "-dNOSAFER", "-c",
         "(%s) (r) file runpdfbegin 1 1 pdfpagecount {pdfgetpage /MediaBox pget pop == } for quit" % escaped],
        capture_output=True, text=True).stdout.split("\n")
    boxes = [tuple(float(v) for v in re.findall(r"[\d.]+", line)[:4]) for line in sizes if "[" in line]
    off_size = [i for i, b in enumerate(boxes, 1)
                if abs(b[2] - a4[0]) > 0.5 or abs(b[3] - a4[1]) > 0.5]
    ink = subprocess.run([gs, "-q", "-dNOPAUSE", "-dBATCH", "-sDEVICE=bbox", pdf],
                         capture_output=True, text=True).stderr
    hi = [tuple(float(v) for v in line.split()[1:5])
          for line in ink.split("\n") if line.startswith("%%HiResBoundingBox")]
    left = min(b[0] for b in hi)
    right = max(b[2] for b in hi)
    tol = 2.5      # microtype lets a few glyphs hang up to about 2 pt into a margin
    fits = left >= inch - tol and right <= a4[0] - inch + tol
    print("pages not A4: %d of %d (required: 0)" % (len(off_size), len(boxes)))
    print("painted content spans x = %.1f .. %.1f pt; the 1 inch margins allow %.1f .. %.1f "
          "(+/- %.1f pt of protrusion): %s" % (left, right, inch, a4[0] - inch, tol,
                                               "ok" if fits else "<-- OUTSIDE THE MARGINS"))
    # half-page rule on the rendered chapters
    pages = pages or _gs_text_pages(gs, pdf)

    def joined(row):
        text, prev = "", None
        for s in row:
            if prev is not None and s[0] - prev[2] > 1.6:
                text += " "
            text += s[5]
            prev = s
        return text.strip()

    def lines_of(spans):
        rows = {}
        for sp in spans:
            rows.setdefault(round(sp[1]), []).append(sp)
        return [(y, sorted(rows[y])) for y in sorted(rows) if 66 <= y <= 775]   # skip head and foot

    first = last = None
    for no, spans in enumerate(pages, 1):
        for y, row in lines_of(spans):
            text = joined(row)
            if first is None and re.fullmatch(r"CHAPTER\s*1", text):
                first = no
            if first is not None and last is None and re.fullmatch(r"APPENDIX\s*A", text):
                last = no - 1
    if first is None or last is None:
        print("half-page rule on the rendered chapters: skipped (chapter range not found)")
        return None
    count = collections.Counter()
    for spans in pages[first - 1:last]:
        for sp in spans:
            count[round(sp[4], 2)] += len(sp[5])
    body = count.most_common(1)[0][0]
    bold = re.compile(r"Bold|Medi|Demi|Black")
    line_h, gap_max, half = 14.45, 45.0, (a4[1] - 2 * inch) / 2.0
    runs, cur = [], None
    for no in range(first, last + 1):
        prev = None
        for y, row in lines_of(pages[no - 1]):
            fam, size = max(((s[3], s[4]) for s in row),
                            key=lambda fs: sum(len(s[5]) for s in row if (s[3], s[4]) == fs))
            text = joined(row)
            if bold.search(fam) and size >= body * 1.15:          # chapter, section, subsection
                if re.match(r"(CHAPTER|APPENDIX)\b", text):
                    continue
                cur, prev = [text[:60], no, 0.0], None
                runs.append(cur)
                continue
            if abs(size - body) > 0.15 or not text or cur is None:
                continue                                           # float, caption, code and so on
            first_span = row[0]
            if (bold.search(first_span[3]) and abs(first_span[4] - body) < 0.15 and first_span[0] < inch + 8
                    and cur[2] > 0):                               # a bold run-in heading starts a new unit
                cur, prev = [text[:60], no, 0.0], None
                runs.append(cur)
            cur[2] += line_h if prev is None or y - prev > gap_max else y - prev
            prev = y
    runs = [r for r in runs if r[2] > 0]
    worst = max(runs, key=lambda r: r[2])
    over = [r for r in runs if r[2] > half + 1]
    print("half-page rule on the rendered chapters (%d headings, run-in headings included): the "
          "longest body text under one heading is %.0f of %.0f pt, %.2f of a page, on PDF page %d%s"
          % (len(runs), worst[2], half, worst[2] / (a4[1] - 2 * inch), worst[1] + 0,
             "" if not over else "  <-- over half a page: " + "; ".join(r[0] for r in over[:4])))
    return {"runs": runs, "half": half, "first": first, "last": last, "left": left, "right": right,
            "off_size": off_size, "pages": len(boxes)}


def readiness(work):
    """Submission checks that the compiler cannot make: fields still to be
    filled in by hand, the page of the two required front-matter pages, and
    the half-page rule."""
    tex = open(os.path.join(ROOT, NAME + ".tex"), errors="replace").read()
    empty = [name for name, value in re.findall(
        r"\\newcommand\{\\(Turnitin[A-Za-z]*)\}\{([^{}]*)\}", tex)
        if not value.strip() and name not in ("TurnitinSources",)]
    toc = open(os.path.join(work, NAME + ".toc"), errors="replace").read()
    pages = dict(re.findall(r"\\contentsline \{chapter\}\{(Copyright Assignment|Acknowledgements)\}\{([^{}]*)\}", toc))
    unit = re.search(r"R@read\.unit\.max\\endcsname\{([\d\\,]+)\}", tex)
    words = int(unit.group(1).replace("\\,", "")) if unit else None
    print("copyright assignment on page %s, acknowledgements on page %s (required: ii, iii)"
          % (pages.get("Copyright Assignment", "?"), pages.get("Acknowledgements", "?")))
    if words is not None:
        print("longest prose under one heading in the chapters: %d words%s"
              % (words, "" if words <= 300 else "  <-- over half a page"))
    try:
        rendered_audit(os.path.join(work, NAME + ".pdf"))
    except Exception as exc:        # the audit must never hide the build result
        print("rendered layout audit failed: %s: %s" % (type(exc).__name__, exc))
    body = re.sub(r"(?<!\\)%.*", "", tex[tex.index("\\end{filecontents*}"):])
    plain = re.findall(r"\\texttt\b|\\verb[^a-zA-Z]|\\begin\{verbatim|\\includegraphics\s*[\[{]",
                       re.sub(r"\\icode(\[[^\]]*\])?\|[^|]*\|", "", body))
    print("typewriter text or images outside listings/TikZ (\\texttt, \\verb, verbatim, "
          "\\includegraphics): %d (required: 0)" % len(plain))
    lonely = unreferenced_floats(body)
    print("figures, tables and listings that the text never refers to: %d %s"
          % (len(lonely), lonely[:12]))
    if empty:
        print("STILL TO FILL IN before submission: " + ", ".join("\\" + e for e in empty))


def main():
    use_latexmk = "--tectonic" not in sys.argv[1:] and shutil.which("latexmk") \
        and shutil.which("pdflatex")
    if use_latexmk:
        os.makedirs(WORK_TL, exist_ok=True)
        shutil.copy(os.path.join(ROOT, NAME + ".tex"), WORK_TL)
        passes = latexmk()
        report(WORK_TL, "pdfLaTeX via latexmk", passes or "up to date")
        return
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
    report(WORK, "Tectonic", attempt + 1)


if __name__ == "__main__":
    main()

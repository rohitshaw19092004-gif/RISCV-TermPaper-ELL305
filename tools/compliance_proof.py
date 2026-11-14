#!/usr/bin/env python3
"""compliance_proof.py - evidence, measured on the single .tex file and on the
compiled PDF, that the term paper meets each course guideline.

    python3 tools/compliance_proof.py              # everything, with a clean-directory build (about 40 s)
    python3 tools/compliance_proof.py --no-build   # reuse build/texlive instead of building again

One block per guideline, with the numbers behind each verdict. The text is also
written to build/compliance_proof.txt. The exit status is 1 if a guideline fails.
Empty Turnitin fields are reported as ACTION (something only the author can do),
not as a failure of the file. Needs Ghostscript (gs) and, for the clean build,
latexmk; the page text, fonts, sizes and positions all come from the PDF.
"""
import collections
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_paper as bp          # noqa: E402
import readability as rd          # noqa: E402

ROOT, NAME = bp.ROOT, bp.NAME
TEX = os.path.join(ROOT, NAME + ".tex")
PDF = os.path.join(ROOT, NAME + ".pdf")
LOG = []
RESULTS = []


def say(text=""):
    LOG.append(text)
    print(text)


def block(title):
    say()
    say("=" * 78)
    say(title)
    say("-" * 78)


def verdict(guideline, status, summary):
    RESULTS.append((guideline, status, summary))
    say("RESULT: %-6s %s" % (status, summary))


def roman(s):
    vals = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100}
    total = 0
    for a, b in zip(s.lower(), s.lower()[1:] + " "):
        total += -vals[a] if vals.get(b, 0) > vals[a] else vals[a]
    return total


def page_lines(spans):
    """Reading-order text lines of one page: (baseline y, text)."""
    rows = {}
    for sp in spans:
        rows.setdefault(round(sp[1]), []).append(sp)
    out = []
    for y in sorted(rows):
        text, prev = "", None
        for sp in sorted(rows[y]):
            if prev is not None and sp[0] - prev[2] > 1.6:
                text += " "
            text += sp[5]
            prev = sp
        out.append((y, " ".join(text.split())))
    return out


def toc_entries(work):
    toc = open(os.path.join(work, NAME + ".toc"), errors="replace").read()
    rows = re.findall(r"\\contentsline \{chapter\}\{(?:\\numberline \{([^}]*)\})?"
                      r"([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}\{([^{}]*)\}", toc)
    return [((n or "").strip(), re.sub(r"\\ignorespaces\s*", "", t).strip(), p) for n, t, p in rows]


def count_entries(work, ext, kind):
    path = os.path.join(work, NAME + ext)
    if not os.path.exists(path):
        return 0
    return len(re.findall(r"\\contentsline \{%s\}" % kind, open(path, errors="replace").read()))


def clean_build():
    """Build the lone .tex in an empty directory; returns (workdir, seconds, log text)."""
    work = tempfile.mkdtemp(prefix="paper_clean_")
    shutil.copy(TEX, work)
    t0 = time.time()
    r = subprocess.run(["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error",
                        "-file-line-error", NAME + ".tex"], cwd=work, capture_output=True,
                       text=True, errors="replace")
    seconds = time.time() - t0
    return work, seconds, r.returncode, open(os.path.join(work, NAME + ".log"), errors="replace").read()


def painted_rasters(gs, pdf, base):
    """Render every page twice at 30 dpi, once normally and once with all images dropped
    (Ghostscript -dFILTERIMAGE); returns (pages, pages that differ). A page that changes
    paints a raster image."""
    def render(flags, sub):
        d = os.path.join(base, sub)
        os.makedirs(d, exist_ok=True)
        subprocess.run([gs, "-q", "-dNOPAUSE", "-dBATCH", "-sDEVICE=pgmraw", "-r30"] + flags +
                       ["-sOutputFile=" + os.path.join(d, "p%03d.pgm"), pdf], check=True, capture_output=True)
        return d
    a, b = render([], "with"), render(["-dFILTERIMAGE"], "without")
    names = sorted(os.listdir(a))
    changed = [n for n in names if open(os.path.join(a, n), "rb").read() != open(os.path.join(b, n), "rb").read()]
    return len(names), changed


def raster_control(gs, base):
    """A one-page PDF that does contain an 8 x 8 raster image: the method must see it."""
    os.makedirs(base, exist_ok=True)
    ps, pdf = os.path.join(base, "control.ps"), os.path.join(base, "control.pdf")
    data = "".join("%02X" % ((x * 29 + y * 17) % 256) for y in range(8) for x in range(8))
    open(ps, "w").write("%!PS\n/DeviceGray setcolorspace\n20 20 translate 100 100 scale\n"
                        "8 8 8 [8 0 0 8 0 0] currentfile /ASCIIHexDecode filter image\n" + data + ">\nshowpage\n")
    subprocess.run([gs, "-q", "-dNOPAUSE", "-dBATCH", "-sDEVICE=pdfwrite", "-sOutputFile=" + pdf, ps],
                   check=True, capture_output=True)
    return bool(painted_rasters(gs, pdf, os.path.join(base, "run"))[1])


def main():
    no_build = "--no-build" in sys.argv[1:]
    gs = shutil.which("gs")
    if not gs or not os.path.exists(PDF):
        sys.exit("needs Ghostscript and the compiled PDF (run tools/build_paper.py first)")
    tex = open(TEX, errors="replace").read()
    raw = open(TEX, "rb").read()
    body = re.sub(r"(?<!\\)%.*", "", tex[tex.index("\\end{filecontents*}"):])
    plain = re.sub(r"\\icode(\[[^\]]*\])?\|[^|]*\|", "", body)      # drop the quoted documentation of commands

    block("0. What was examined")
    say("source   : %s  (%d bytes, %d lines, sha256 %s)" % (os.path.basename(TEX), len(raw),
        tex.count("\n"), hashlib.sha256(raw).hexdigest()[:16]))
    say("PDF      : %s  (%d bytes, sha256 %s)" % (os.path.basename(PDF), os.path.getsize(PDF),
        hashlib.sha256(open(PDF, "rb").read()).hexdigest()[:16]))
    ver = lambda cmd: (subprocess.run(cmd, capture_output=True, text=True).stdout.split("\n") or [""])[0]
    say("engine   : " + ver(["pdflatex", "--version"]))
    say("Ghostscript " + ver([gs, "--version"]) + " reads the PDF (page boxes, painted extent, text with font, size, position)")
    pages = bp._gs_text_pages(gs, PDF)
    say("PDF text layer: %d pages" % len(pages))

    # ------------------------------------------------------------------ build
    if no_build:
        work, seconds, rc, log = bp.WORK_TL, None, 0, open(os.path.join(bp.WORK_TL, NAME + ".log"), errors="replace").read()
        say("build directory reused: " + work)
    else:
        work, seconds, rc, log = clean_build()

    # ------------------------------------------------------------ guideline 1
    block("Guideline 1: the report is ONE LaTeX file")
    ban = collections.OrderedDict((name, len(re.findall(pat, plain))) for name, pat in [
        ("\\input", r"\\input\b"), ("\\include", r"\\include\b"), ("\\includegraphics", r"\\includegraphics\b"),
        ("\\includepdf", r"\\includepdf\b"), ("\\lstinputlisting", r"\\lstinputlisting\b"),
        ("\\write18", r"\\write18"), ("minted package", r"\\usepackage(\[[^\]]*\])?\{minted\}")])
    say("commands that would pull in another file or need shell escape, in the document body: " +
        ", ".join("%s %d" % kv for kv in ban.items()))
    say("non-ASCII bytes in the .tex: %d" % sum(1 for b in raw if b > 127))
    say("TA review stated in the file (generic, no name): title page %s, compliance table %s" % (
        "yes" if "Shown to a teaching assistant" in tex else "NO", "yes" if "shown to a teaching assistant" in tex else "NO"))
    say("the BibTeX database is inside the file: \\begin{filecontents*}{refs.bib} holds %d entries"
        % len(re.findall(r"^@\w+\{", tex[:tex.index("\\end{filecontents*}")], re.M)))
    pages_built = re.findall(r"Output written on .*?\((\d+) pages", log.replace("\n", ""))
    over = re.findall(r"Overfull \\hbox", log)
    undefined = re.findall(r"(?:Reference|Citation) `([^']+)' on page", log)
    warns = collections.Counter(re.findall(r"^((?:LaTeX|Package|Class) [A-Za-z0-9]* ?Warning)", log, re.M))
    inputs = set()
    fls = os.path.join(work, NAME + ".fls")
    if os.path.exists(fls):
        for line in open(fls, errors="replace"):
            if line.startswith("INPUT "):
                inputs.add(line[6:].strip())
    local = sorted(i for i in inputs if not i.startswith("/") and "texmf" not in i)
    images = sorted(i for i in inputs if re.search(r"\.(png|jpe?g|gif|bmp|tiff?|eps|svg|pdf)$", i, re.I)
                    and not i.endswith(NAME + ".pdf"))
    if seconds is not None:
        say("clean-directory build of the .tex alone (latexmk -pdf, %s): exit %d, %d s, %s pages"
            % (work, rc, round(seconds), pages_built[-1] if pages_built else "?"))
    else:
        say("build in %s: %s pages" % (work, pages_built[-1] if pages_built else "?"))
    say("overfull boxes: %d; undefined references or citations: %d; other warnings: %s"
        % (len(over), len(undefined), dict(warns) or "none"))
    say("files TeX read besides the system tree: " + ", ".join(sorted({os.path.basename(x) for x in local})))
    say("image or PDF files read by the build (any location): %s" % (images or "none"))
    ok1 = (not any(ban.values()) and not images and rc == 0 and all(
        re.search(r"\.(aux|bbl|ind|lof|lol|lot|out|toc|tex|bib|idx|ilg|bcf|blg)$", x) for x in local))
    verdict("1", "PASS" if ok1 else "FAIL", "one .tex, a database written by filecontents*, no other input file")

    # ------------------------------------------------------------ guideline 2
    block("Guideline 2: diagrams in a text-to-diagram format, in the proper environment")
    doc = tex[tex.index("\\begin{document}"):]
    figs = re.findall(r"\\begin\{figure\}.*?\\end\{figure\}", doc, re.S)
    kinds = ["tikzpicture", "circuitikz", "forest", "axis", "groupplot", "tikztimingtable"]
    count = {k: len(re.findall(r"\\begin\{%s\}" % k, doc)) for k in kinds}
    nodraw = [re.search(r"\\label\{([^}]*)\}", f).group(1) if re.search(r"\\label\{([^}]*)\}", f) else "?"
              for f in figs if not any("\\begin{%s}" % k in f for k in kinds)]
    say("figure environments: %d; drawing environments inside the document: %s"
        % (len(figs), ", ".join("%s %d" % kv for kv in count.items())))
    say("figures without a tikzpicture/circuitikz/forest/pgfplots/tikz-timing environment: %s" % (nodraw or "none"))
    say("\\includegraphics / \\pgfimage / raster or PDF image inputs read by the build: %d / %d / %d" % (
        len(re.findall(r"\\includegraphics\b", plain)), len(re.findall(r"\\pgfimage\b", plain)), len(images)))
    scratch = tempfile.mkdtemp(prefix="paper_raster_")
    n_pages, painting = painted_rasters(gs, PDF, os.path.join(scratch, "paper"))
    control = raster_control(gs, os.path.join(scratch, "control"))
    shutil.rmtree(scratch, ignore_errors=True)
    say("raster images painted in the PDF: %d of %d pages change when Ghostscript drops every image "
        "(control: a PDF holding one 8x8 image does change: %s)" % (len(painting), n_pages, "yes" if control else "NO"))
    verdict("2", "PASS" if not nodraw and not images and figs and control and not painting else "FAIL",
            "%d figures, every one drawn from text, and no raster image anywhere in the PDF" % len(figs))

    # ------------------------------------------------------------ guideline 3
    block("Guideline 3: all code through listings (or minted)")
    forbidden = {"\\texttt": r"\\texttt\b", "\\verb": r"\\verb[^a-zA-Z]", "verbatim env": r"\\begin\{[Vv]erbatim",
                 "alltt": r"\\begin\{alltt", "\\mathtt": r"\\mathtt\b", "\\tt": r"\\tt\b"}
    found = {k: len(re.findall(v, plain)) for k, v in forbidden.items()}
    say("typewriter or verbatim commands outside listings: " + ", ".join("%s %d" % kv for kv in found.items()))
    tt_lines = [i + 1 for i, line in enumerate(tex.split("\n")) if "\\ttfamily" in re.sub(r"(?<!\\)%.*", "", line)]
    say("\\ttfamily appears only in listing style definitions, at .tex lines %s" % tt_lines)
    disp = len(re.findall(r"\\begin\{lstlisting\}", body))
    inline = {m: len(re.findall(r"\\%s\b" % m, plain)) for m in ("icode", "tcode", "code", "lstinline")}
    say("displayed listings: %d (List of Listings has %d entries); inline program text via \\lstinline: %s"
        % (disp, count_entries(work, ".lol", "lstlisting"), ", ".join("\\%s %d" % kv for kv in inline.items())))
    mono = collections.Counter()
    for spans in pages:
        for sp in spans:
            if re.search(r"Mono|Typewriter|Courier", sp[3]):
                mono[sp[3].split("-")[0]] += len(sp[5])
    say("monospace glyphs in the PDF by font: %s" % dict(mono))
    verdict("3", "PASS" if not any(found.values()) and disp else "FAIL",
            "%d listings, %d inline items, no \\texttt, \\verb or verbatim" % (disp, sum(inline.values())))

    # ------------------------------------------------------------ guideline 4
    block("Guideline 4: A4, 1 inch margins, single spaced, 12 pt, double sided")
    cls = re.search(r"\\documentclass\[([^\]]*)\]\{(\w+)\}", tex)
    geo = re.search(r"\\usepackage\[([^\]]*)\]\{geometry\}", tex)
    say("\\documentclass[%s]{%s};  \\usepackage[%s]{geometry};  \\singlespacing: %s"
        % (cls.group(1), cls.group(2), geo.group(1), "present" if "\\singlespacing" in tex else "MISSING"))
    stretch = sum(len(re.findall(p, plain)) for p in (r"\\baselinestretch", r"\\linespread", r"\\onehalfspacing",
                                                      r"\\doublespacing", r"\\setstretch", r"\\spacing\{"))
    say("commands that change the line spacing (\\baselinestretch, \\linespread, \\onehalfspacing, "
        "\\doublespacing, \\setstretch): %d" % stretch)
    audit = bp.rendered_audit(PDF, pages)
    sizes = collections.Counter()
    for spans in pages:
        for sp in spans:
            sizes[round(sp[4], 2)] += len(sp[5])
    total = sum(sizes.values())
    body_size = sizes.most_common(1)[0][0]
    say("character share by font size (PDF points; 11.96 pt is the 12 pt of TeX): " +
        ", ".join("%.2f pt %.1f%%" % (s, 100.0 * n / total) for s, n in sizes.most_common(6)))
    gaps = collections.Counter()
    for spans in pages[audit["first"] - 1:audit["last"]]:
        ys = sorted({round(sp[1], 1) for sp in spans if abs(sp[4] - body_size) < 0.05 and "Roman12-Regular" in sp[3]})
        for a, b in zip(ys, ys[1:]):
            if 13 <= b - a <= 17.5:
                gaps[round(b - a)] += 1
    inside = {g: c for g, c in gaps.items() if g <= 15}
    n = sum(inside.values())
    mean = sum(g * c for g, c in inside.items()) / n if n else 0
    say("baseline pitch of consecutive 12 pt lines inside paragraphs in the chapters: mean %.2f pt over %d line pairs "
        "(%s; whole-point rounding of the positions); default single spacing of 12 pt LaTeX is 14.5 TeX pt = %.2f pt; "
        "%d larger gaps of 16 to 17 pt are the 2 pt paragraph skip" % (
            mean, n, ", ".join("%d pt x %d" % kv for kv in sorted(inside.items())), 14.5 * 72 / 72.27,
            sum(c for g, c in gaps.items() if g > 15)))
    mirror = {"even": [0, 0], "odd": [0, 0]}
    for no in range(audit["first"] + 1, audit["last"] + 1):
        head = [sp for sp in pages[no - 1] if 20 < sp[1] < 66]
        if not head:
            continue                                   # chapter opening pages carry no running head
        side = "even" if (no - audit["first"] + 1) % 2 == 0 else "odd"
        mirror[side][0] += 1
        mirror[side][1] += (min(sp[0] for sp in head) < 80) if side == "even" else (max(sp[2] for sp in head) > 515)
    say("two-sided layout: running heads mirror on facing pages: left-hand (even) pages have the head at the left "
        "margin on %d of %d pages, right-hand (odd) pages at the right margin on %d of %d" % (
            mirror["even"][1], mirror["even"][0], mirror["odd"][1], mirror["odd"][0]))
    twoside = "twoside" in cls.group(1) and mirror["even"][1] == mirror["even"][0] and mirror["odd"][1] == mirror["odd"][0]
    ok4 = ("a4paper" in cls.group(1) and "12pt" in cls.group(1) and twoside and "margin=1in" in geo.group(1)
           and stretch == 0 and audit["off_size"] == [] and audit["left"] >= 69.5 and audit["right"] <= 525.8
           and 14.2 <= mean <= 14.7)
    verdict("4", "PASS" if ok4 else "FAIL",
            "A4 on all %d pages, text block 1 in on every side, 12 pt body, single spaced, twoside" % audit["pages"])

    # ------------------------------------------------------------ guideline 5
    block("Guideline 5: plagiarism report as Appendix A, matching the Turnitin submission")
    entries = toc_entries(work)
    appendices = [e for e in entries if re.fullmatch(r"[A-Z]", e[0])]
    say("first appendix in the table of contents: Appendix %s, %s, page %s" % appendices[0])
    fields = re.findall(r"\\newcommand\{\\(Turnitin[A-Za-z]*)\}\{([^{}]*)\}", tex)
    for name, value in fields:
        say("   %-24s %s" % ("\\" + name, value.strip() or (
            "(empty: optional list of sources, not printed)" if name == "TurnitinSources"
            else "(empty: printed as 'pending')")))
    empty = [n for n, v in fields if not v.strip() and n != "TurnitinSources"]
    right_place = appendices[0][0:2] == ("A", "Plagiarism Report")
    verdict("5", "ACTION" if empty and right_place else ("PASS" if right_place else "FAIL"),
            ("Appendix A is in place but %d of its fields are empty; run Turnitin on the rebuilt PDF and fill them" % len(empty))
            if empty else "Appendix A is in place and filled")

    # ------------------------------------------------------------ guideline 6
    block("Guideline 6: reading indices as Appendix B (reference: analyzemywriting.com/readability_indices.html)")
    say("second appendix: Appendix %s, %s, page %s" % appendices[1])
    chapters = tex[tex.index("\\chapter{Introduction and Scope}"):tex.index("\\appendix")]
    c = rd.counts(rd.prose(chapters))
    ix = rd.indices(c)
    shown = {}
    block_ix = re.search(r"%% BEGIN GENERATED read_indices\n(.*?)\n%% END GENERATED read_indices", tex, re.S).group(1)
    for row in block_ix.split("\n"):
        m = re.match(r"([A-Za-z ]+?)(?: \([^)]*\))? & ([\d.]+) &", row.replace("\\etal", "").replace("\\\"{o}", "o"))
        if m:
            shown[m.group(1).strip()] = float(m.group(2))
    five = sorted(ix[k] for k in ("fk", "fog", "smog", "cli", "ari"))
    want = {"FRE": ix["fre"], "FKGL": ix["fk"], "Fog": ix["fog"], "SMOG": ix["smog"], "CLI": ix["cli"],
            "ARI": ix["ari"], "LIX": ix["lix"], "RIX": ix["rix"], "Average grade": sum(five) / 5, "Median grade": five[2]}
    mism = []
    for name, v in want.items():
        got = shown.get(name)
        say("   %-14s recomputed from the text %6.2f   printed in Appendix B %s"
            % (name, v, "%.1f" % got if got is not None else "MISSING"))
        if got is None or abs(round(v, 1) - got) > 0.051:
            mism.append(name)
    say("corpus: %d words, %d sentences (SMOG needs at least 30 sentences); Fry/Raygor inputs given: %s"
        % (c["W"], c["S"], "yes" if "Raygor" in block_ix + tex else "NO"))
    say("the reference page names: Gunning fog, Flesch-Kincaid, SMOG, Coleman-Liau, Automated Readability "
        "Index, their average and median grade level, and the Fry and Raygor graphs; all are in Appendix B")
    verdict("6", "PASS" if not mism and appendices[1][1] == "Reading Indices" else "FAIL",
            "Appendix B reproduces from the text: %d indices, average and median" % (len(want) - 2))

    # ------------------------------------------------------------ guideline 7
    block("Guideline 7: an explanation over half a page goes to an appendix")
    unit = re.search(r"R@read\.unit\.max\\endcsname\{([\d\\,]+)\}", tex)
    words = int(unit.group(1).replace("\\,", "")) if unit else -1
    say("by words: the longest prose under one heading of Chapters 1-12 is %d words (half a page of this "
        "layout is about 300)" % words)
    top = sorted(audit["runs"], key=lambda r: -r[2])[:6]
    say("by rendered height (12 pt body text under each heading or bold run-in heading; half the text block = "
        "%.0f pt): the six longest runs" % audit["half"])
    for title, pg, h in top:
        say("   %6.0f pt = %4.1f lines = %.2f page   PDF page %3d   %s" % (h, h / 14.45, h / (2 * audit["half"]), pg, title[:60]))
    verdict("7", "PASS" if top[0][2] <= audit["half"] + 1 and 0 < words <= 300 else "FAIL",
            "longest unit %d words and %.2f of a page" % (words, top[0][2] / (2 * audit["half"])))

    # ------------------------------------------------------------ guideline 8
    block("Guideline 8: autogenerated contents, lists of tables and figures, index, glossary")
    cmds = {k: len(re.findall(re.escape(k), plain)) for k in
            ("\\tableofcontents", "\\listoftables", "\\listoffigures", "\\printindex", "\\printnoidxglossary",
             "\\makeindex", "\\makenoidxglossaries")}
    say("generating commands in the source: " + ", ".join("%s %d" % kv for kv in cmds.items()))
    named = {t: p for _, t, p in entries}
    say("entries produced: List of Tables %d, List of Figures %d, List of Listings %d; contents %d chapter-level lines"
        % (count_entries(work, ".lot", "table"), count_entries(work, ".lof", "figure"),
           count_entries(work, ".lol", "lstlisting"), len(entries)))
    idx = os.path.join(work, NAME + ".idx")
    ind = os.path.join(work, NAME + ".ind")
    say("index: %d \\index marks in the text -> makeindex -> %d index lines (page %s)" % (
        len(re.findall(r"\\indexentry", open(idx, errors="replace").read())) if os.path.exists(idx) else 0,
        len(re.findall(r"\\(?:sub)*item", open(ind, errors="replace").read())) if os.path.exists(ind) else 0,
        named.get("Index", "?")))
    gl_defined = len(re.findall(r"^\\newglossaryentry", tex, re.M))
    g0 = roman(named["Glossary"]) if "Glossary" in named else 0
    gl_printed = sum(1 for sp in pages[g0 - 1:audit["first"] - 1] for _, t in page_lines(sp) if t.endswith(")") and "(p." in t)
    say("glossary: %d entries defined, printed on page %s; entries with their page note counted in the PDF: %d"
        % (gl_defined, named.get("Glossary", "?"), gl_printed))
    front = [(i + 1, page_lines(sp)[0][1]) for i, sp in enumerate(pages[:audit["first"] - 1]) if sp and page_lines(sp)]
    heads = {}
    for p, t in front:                      # the first page on which each list appears
        if t in ("Table of Contents", "List of Tables", "List of Figures", "List of Listings", "Glossary"):
            heads.setdefault(t, p)
    say("pages on which the front-matter lists start (PDF page): %s" % heads)
    ok8 = (all(cmds[k] for k in cmds) and len(heads) == 5 and gl_defined == 65 and gl_printed >= gl_defined - 3)
    verdict("8", "PASS" if ok8 else "FAIL", "contents, tables, figures, listings, glossary and index are all generated")

    # ------------------------------------------------------- guidelines 9, 10
    block("Guidelines 9 and 10: copyright assignment on page 2, acknowledgements on page 3")
    texts = [[t for _, t in page_lines(pages[i])] for i in range(4)]
    say("PDF page 1 (title page): %s" % " | ".join(texts[0][:4]))
    say("PDF page 2, printed label %r:" % texts[1][-1])
    for t in texts[1]:
        say("   " + t)
    say("PDF page 3, printed label %r:" % texts[2][-1])
    for t in texts[2]:
        say("   " + t)
    p2, p3 = " ".join(texts[1]), " ".join(texts[2])
    ok9 = ("Copyright Assignment" in texts[1][0] and "Indian Institute of Technology Delhi" in p2
           and re.search(r"intellectual property rights", p2) and "respective authors" in p2 and texts[1][-1] == "ii")
    ok10 = ("Acknowledgements" in texts[2][0] and "Department of Electrical Engineering" in p3
            and "Indian Institute of Technology Delhi" in p3 and re.search(r"Prof\.", p3) and texts[2][-1] == "iii")
    verdict("9", "PASS" if ok9 else "FAIL", "page 2 assigns all IPR to IIT Delhi and keeps cited authors' rights")
    verdict("10", "PASS" if ok10 else "FAIL", "page 3 thanks named individuals, the Department of Electrical Engineering and IIT Delhi")

    # --------------------------------------------------------------- authors
    block("Authorship: a project report has ONE author (term-paper teams are named in Gradescope, not in the file)")
    names = [t for t in texts[0] if t.startswith("Name:")]
    say("title page 'Name:' rows: %s;  'Single author.' on the title page: %s;  Declaration says single author: %s" % (
        names, any("Single author" in t for t in texts[0]), "single author" in " ".join(texts[3])))
    verdict("authors", "PASS" if len(names) == 1 else "FAIL",
            "one author named in the file; submit on Gradescope as an individual")

    # ----------------------------------------------------------- housekeeping
    block("Housekeeping that a strict reader checks")
    bib = tex[:tex.index("\\end{filecontents*}")]
    keys = set(re.findall(r"^@\w+\{([^,]+),", bib, re.M))
    cited = set()
    for m in re.finditer(r"\\cite[a-z]*\*?(?:\[[^\]]*\])*\{([^}]*)\}", body):
        cited.update(k.strip() for k in m.group(1).split(","))
    say("bibliography entries %d, cited keys %d, uncited %s, citations without an entry %s"
        % (len(keys), len(cited), sorted(keys - cited) or "none", sorted(cited - keys) or "none"))
    lonely = bp.unreferenced_floats(body)
    say("figures, tables and listings that the text never refers to: %s" % (lonely or "none"))
    junk = collections.Counter()
    for spans in pages:
        for _, t in page_lines(spans):
            for pat in ("TODO", "TBD", "FIXME", "XXX", "??", "[?]", "lorem"):
                if pat in t:
                    junk[pat] += 1
    say("placeholder or unresolved-reference markers in the PDF text (TODO, TBD, FIXME, XXX, ??, [?]): %s"
        % (dict(junk) or "none"))
    pending = sum(1 for spans in pages for _, t in page_lines(spans) if t.endswith("pending"))
    say("table cells that read 'pending' (the Turnitin fields): %d" % pending)
    verdict("housekeeping", "PASS" if not (keys - cited) and not (cited - keys) and not lonely and not junk else "FAIL",
            "references, cross-references and floats are consistent")

    # ----------------------------------------------------------------- summary
    block("SUMMARY")
    for g, status, text in RESULTS:
        say("%-13s %-6s %s" % (g, status, text))
    fails = [r for r in RESULTS if r[1] == "FAIL"]
    actions = [r for r in RESULTS if r[1] == "ACTION"]
    say()
    say("%d guidelines checked: %d PASS, %d FAIL, %d ACTION for the author"
        % (len(RESULTS), len(RESULTS) - len(fails) - len(actions), len(fails), len(actions)))
    out = os.path.join(ROOT, "build", "compliance_proof.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w").write("\n".join(LOG) + "\n")
    say("written to " + out)
    if not no_build:
        shutil.rmtree(work, ignore_errors=True)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()

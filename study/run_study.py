#!/usr/bin/env python3
"""run_study.py - build the tools, validate them, and run every experiment of
the model study reported in the term paper.

    python3 run_study.py            # everything
    python3 run_study.py validate   # only the validation steps

Outputs are CSV files in results/. Every run is deterministic, so a second
invocation reproduces the files byte for byte.
"""
import csv
import hashlib
import json
import math
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import reference
import rvasm

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")
RESULTS = os.path.join(HERE, "results")
MODEL = os.path.join(BUILD, "rvmodel")
KERNELS = reference.KERNELS
DEFENSES = ["none", "nospec", "dom", "invis-e", "invis-v", "stt", "nda", "undo"]
PAIRS = [("crc32", "hashtab"), ("bsearch", "stream"), ("heapsort", "matmul"),
         ("listwalk", "sieve"), ("bstree", "strsearch")]
QEMU = ["qemu-system-riscv64", "-machine", "virt", "-cpu", "rv64", "-m", "128M",
        "-display", "none", "-monitor", "none", "-serial", "stdio", "-bios", "none"]


def sh(cmd, timeout=600):
    return subprocess.run(cmd, check=True, capture_output=True, text=True,
                          timeout=timeout).stdout


def assemble_text(name, text):
    asm = rvasm.Assembler()
    image = asm.assemble(text)
    with open(os.path.join(BUILD, name + ".bin"), "wb") as f:
        f.write(image)
    with open(os.path.join(BUILD, name + ".elf"), "wb") as f:
        f.write(rvasm.make_elf(image))


def crt():
    return open(os.path.join(HERE, "workloads", "crt.s")).read()


def build():
    os.makedirs(BUILD, exist_ok=True)
    os.makedirs(RESULTS, exist_ok=True)
    sh(["cc", "-O2", "-std=c11", "-Wall", "-Wextra", "-o", MODEL,
        os.path.join(HERE, "rvmodel.c")])
    for k in KERNELS:
        src = open(os.path.join(HERE, "workloads", k + ".s")).read()
        assemble_text(k, crt() + "\n" + src)


def model(progs, **opts):
    """Run rvmodel on one or two programs; returns its statistics as a dict."""
    if isinstance(progs, str):
        progs = [progs]
    cmd = [MODEL] + [os.path.join(BUILD, p + ".bin") for p in progs]
    cmd += ["%s=%s" % kv for kv in opts.items()]
    stats = {}
    for token in sh(cmd).split():
        key, value = token.split("=", 1)
        stats[key] = value if key.startswith("out") else int(value)
    return stats


def run_many(jobs):
    """jobs: list of (progs, opts). Runs them in parallel, keeps the order."""
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
        return list(pool.map(lambda j: model(j[0], **j[1]), jobs))


def write_csv(name, header, rows):
    with open(os.path.join(RESULTS, name), "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)
    print("wrote results/%s (%d rows)" % (name, len(rows)))


def pct(new, old):
    return "%.3f" % (100.0 * (new / old - 1.0))


# ------------------------------------------------------------------ validation
def validate_kernels():
    rows, ok = [], True
    for k in KERNELS:
        ref = reference.expected(k)
        emu = sh(QEMU + ["-kernel", os.path.join(BUILD, k + ".elf")], 300).strip()
        st = model(k)
        good = ref == emu == st["out0"]
        ok &= good
        size = os.path.getsize(os.path.join(BUILD, k + ".bin"))
        rows.append([k, size, st["inst"], ref, emu, st["out0"], "yes" if good else "NO"])
    write_csv("validation.csv", ["kernel", "image_bytes", "instructions", "reference",
                                 "qemu", "model", "agree"], rows)
    return ok


LOOP = """
main:
    {setup}
    li    t0, {n}
loop:
    {body}
    addi  t0, t0, -1
    bnez  t0, loop
    li    a0, 0
    ret
.data
.align 6
cell: .dword cell
"""

RING = """
.equ P, {p}
.equ STRIDE, {stride}
main:
    la    s0, ring
    li    s1, P
    li    t3, STRIDE
    li    t0, 0
build:
    addi  t2, t0, 1
    remu  t2, t2, s1
    mul   t4, t2, t3
    add   t4, s0, t4
    mul   t5, t0, t3
    add   t5, s0, t5
    sd    t4, 0(t5)
    addi  t0, t0, 1
    blt   t0, s1, build
    mv    t1, s0
    li    t0, {n}
loop:
    ld    t1, 0(t1)
    addi  t0, t0, -1
    bnez  t0, loop
    li    a0, 0
    ret
.data
.align 12
ring: .zero P * STRIDE
"""

# As RING, with a branch that waits for each loaded value (never taken).
RINGB = RING.replace("    ld    t1, 0(t1)\n    addi  t0, t0, -1",
                     "    ld    t1, 0(t1)\n    beqz  t1, out\n    addi  t0, t0, -1").replace(
                     "    li    a0, 0\n    ret", "out:\n    li    a0, 0\n    ret")

# A divide feeds a branch; behind the branch one load supplies the address of
# a second, whose value is the divide's operand in the next iteration.
SLOW = """
main:
    la    a1, cell
    li    t5, 1
    li    t2, 5
    li    t0, {n}
loop:
    divu  t3, t2, t5
    beqz  t3, out
    ld    t1, 0(a1)
    ld    t2, 0(t1)
    addi  t0, t0, -1
    bnez  t0, loop
out:
    li    a0, 0
    ret
.data
.align 6
cell: .dword cell2
.align 6
cell2: .dword 5
"""

# The loop branch waits for a divide and is always mispredicted (bp=nottaken).
# Its wrong path begins with {k} loads from lines that the set-up has pushed
# out of the first-level cache into the second.
WRONG = """
main:
    la    s0, pad
    li    t3, 4096
    add   s1, s0, t3
    add   s2, s1, t3
    add   s3, s2, t3
    add   s4, s3, t3
    li    t2, 13
    mv    t1, s0
touch:
    ld    t4, 0(t1)
    add   t1, t1, t3
    addi  t2, t2, -1
    bnez  t2, touch
    li    t5, 1
    li    t0, {n}
loop:
    divu  t0, t0, t5
    addi  t0, t0, -1
    bnez  t0, loop
    {loads}
    {nops}
    li    a0, 0
    ret
.data
.align 12
pad: .zero 13 * 4096
"""

# One load behind a branch that waits for a divide, which in turn waits for
# the first, cold load, so that nothing older is left to commit when the branch
# resolves. The run is stopped when the second load has been committed.
FLOOR = """
main:
    la    a1, cell
    ld    t4, 0(a1)
    li    t5, 1
    divu  t3, t4, t5
    beqz  t3, out
    ld    t1, 0(a1)
out:
    li    a0, 0
    ret
.data
.align 6
cell: .dword cell
"""


def unit_tests():
    """Timing tests: a cost derived by hand from the rules of the timing model
    must equal the cost that the simulator reports. Three kinds of cost are
    used: cycles per additional loop iteration (kind "iter"), the commit time
    of one instruction with a defense minus the same without (kind "commit"),
    and cycles per additional context switch with a flush minus the same
    without (kind "switch")."""
    indep = lambda k: "\n    ".join("addi  a%d, zero, %d" % (i + 1, i) for i in range(k))
    chain = lambda k: "\n    ".join(["addi  t1, t1, 1"] * k)
    loop = lambda body, setup="nop": lambda n: LOOP.format(n=n, body=body, setup=setup)
    ring = lambda p, stride: lambda n: RING.format(n=n, p=p, stride=stride)
    big = {"tlb": 4096}
    exact = {"frames": 0}     # unscattered page frames keep the sums hand-checkable
    tests = [
        ("2 independent adds, width 4", loop(indep(2)), {}, 1.0, 4000),
        ("6 independent adds, width 4", loop(indep(6)), {}, 2.0, 4000),
        ("6 independent adds, width 2", loop(indep(6)), {"width": 2}, 4.0, 4000),
        ("chain of 6 dependent adds", loop(chain(6)), {}, 6.0, 4000),
        ("multiply chain", loop("mul   t1, t1, t2", "li    t2, 3"), {}, 3.0, 4000),
        ("divide chain", loop("divu  t1, t1, t2", "li    t2, 1"), {}, 20.0, 4000),
        ("load chain, first-level hit", loop("ld    t1, 0(t1)", "la    t1, cell"), {}, 4.0, 4000),
        ("load chain, second-level hit", ring(1024, 64), big, 14.0, 2048),
        ("load chain, last-level hit", ring(8192, 64), big, 45.0, 16384),
        ("load chain, memory", ring(65536, 64), big, 220.0, 131072),
        ("8 lines in one 8-way set", ring(8, 4096), {}, 4.0, 4000),
        ("9 lines in one 8-way set", ring(9, 4096), {}, 14.0, 4005),
        ("9 lines in one 16-way set", ring(9, 4096), {"l1sets": 32, "l1ways": 16}, 4.0, 4005),
        ("always-mispredicted branch, depth 4", loop("nop"), {"bp": "nottaken"}, 8.0, 4000),
        ("always-mispredicted branch, depth 6", loop("nop"),
         {"bp": "nottaken", "fdepth": 6}, 10.0, 4000),
    ]
    tests = [("iter",) + t for t in tests]
    # --- the page walk: three first-level hits of 4 cycles before the load
    tests += [
        ("iter", "load chain over 33 pages, 32-entry TLB", ring(33, 4160), {}, 16.0, 3300),
        ("iter", "load chain over 32 pages, 32-entry TLB", ring(32, 4160), {}, 4.0, 3200),
    ]
    # --- committed-path rules of the speculation defenses
    slow = lambda n: SLOW.format(n=n)
    ringb = lambda n: RINGB.format(n=n, p=1024, stride=64)
    for d, cost in (("none", 2.0), ("dom", 2.0), ("invis-e", 2.0), ("invis-v", 2.0),
                    ("stt", 25.0), ("nda", 25.0), ("nospec", 29.0)):
        tests.append(("iter", "two loads behind a slow branch, def=%s" % d, slow,
                      {"def": d}, cost, 4000))
    for d, cost in (("none", 14.0), ("dom", 15.0), ("nospec", 15.0)):
        tests.append(("iter", "second-level load chain feeding a branch, def=%s" % d, ringb,
                      dict(big, **{"def": d}), cost, 2048))
    # --- the redirect of the undo scheme: 14 cycles for every four rolled-back fills
    def wrong(k):
        loads = "\n    ".join("ld    t2, 0(s%d)" % j for j in range(k))
        return lambda n: WRONG.format(n=n, loads=loads, nops="\n    ".join(["nop"] * 100))
    tests += [
        ("iter", "slow mispredicted branch, 1 wrong-path miss, def=none", wrong(1),
         {"bp": "nottaken"}, 28.0, 3000),
        ("iter", "slow mispredicted branch, 1 wrong-path miss, def=undo", wrong(1),
         {"bp": "nottaken", "def": "undo"}, 42.0, 3000),
        ("iter", "slow mispredicted branch, 5 wrong-path misses, def=undo", wrong(5),
         {"bp": "nottaken", "def": "undo"}, 56.0, 3000),
    ]
    # --- the commit floor of the validating invisible scheme
    tests += [
        ("commit", "commit of a speculative first-level hit, def=invis-v", FLOOR,
         {"def": "invis-v"}, 3.0, 2),
        ("commit", "commit of a speculative first-level hit, def=invis-e", FLOOR,
         {"def": "invis-e"}, 0.0, 2),
    ]
    # --- the context switch: 322 cycles for a flush, plus what must be refetched
    tests += [
        ("switch", "switch flushing the TLB, register-only loop", loop(indep(2)),
         {"flush": 4}, 322.0, 3000),
        ("switch", "switch flushing the first-level data cache, load chain",
         loop("ld    t1, 0(t1)", "la    t1, cell"), {"flush": 1}, 332.0, 4000),
        ("switch", "switch flushing the TLB, load chain",
         loop("ld    t1, 0(t1)", "la    t1, cell"), {"flush": 4}, 334.0, 4000),
    ]
    rows, ok = [], True
    for i, (kind, name, gen, opts, expect, n) in enumerate(tests):
        if kind == "iter":
            cycles = []
            for count in (n, 2 * n):
                assemble_text("unit", crt() + gen(count))
                cycles.append(model("unit", **dict(exact, **opts))["cycles"])
            got = (cycles[1] - cycles[0]) / n
        elif kind == "commit":           # n = which load to stop at
            assemble_text("unit", crt() + gen)
            stop = next(k for k in range(1, 200)
                        if model("unit", maxinst=k, **exact)["load"] == n)
            got = (model("unit", maxinst=stop, **dict(exact, **opts))["cycles"]
                   - model("unit", maxinst=stop, **exact)["cycles"])
        else:                            # two copies of the loop, 1000 instructions a slice
            delta, switches = [], []
            for count in (n, 2 * n):
                assemble_text("unit", crt() + gen(count))
                run = lambda **o: model(["unit", "unit"], quantum=1000, **dict(exact, **o))
                with_flush, without = run(**opts), run()
                delta.append(with_flush["cycles"] - without["cycles"])
                switches.append(with_flush["nswitch"])
            got = (delta[1] - delta[0]) / (switches[1] - switches[0])
        good = abs(got - expect) <= 0.002 * expect
        ok &= good
        rows.append([i + 1, kind, name, "%.3f" % expect, "%.3f" % got, "yes" if good else "NO"])
    write_csv("unit_tests.csv", ["test", "kind", "description", "expected_cycles",
                                 "measured_cycles", "pass"], rows)
    return ok


def invariants():
    """Properties that must hold exactly if the defense models are coded as
    specified: a hiding defense leaves no transient fills, a restricting
    defense executes no dependent transient loads, and so on."""
    rows, ok = [], True

    def check(name, value, want):
        nonlocal ok
        good = value == want
        ok &= good
        rows.append([name, value, want, "yes" if good else "NO"])

    for d in ("nospec", "dom", "invis-e", "invis-v", "undo"):
        total = sum(model(k, **{"def": d})["wp_fill"] for k in KERNELS)
        check("transient first-level fills under %s, all kernels" % d, total, 0)
    for d in ("nospec", "stt", "nda"):
        total = sum(model(k, **{"def": d})["wp_dep"] for k in KERNELS)
        check("dependent transient loads executed under %s, all kernels" % d, total, 0)
    base = sum(model(k)["wp_dep"] for k in KERNELS)
    rows.append(["dependent transient loads executed with no defense", base, "> 0",
                 "yes" if base > 0 else "NO"])
    ok &= base > 0
    pair = ["bsearch", "stream"]
    st = model(pair, quantum=50000, part=1, isolbp=1)
    check("cross-domain evictions, way partitioning (all levels + TLB)",
          st["l1d_xev"] + st["l2_xev"] + st["llc_xev"] + st["tlb_xev"], 0)
    check("predictions made from the other domain's entries, partitioned predictors",
          st["xpred"], 0)
    st = model(pair, quantum=50000, color=1)
    check("cross-domain evictions in L2 and LLC, page colouring",
          st["l2_xev"] + st["llc_xev"], 0)
    st = model(pair, quantum=50000, flush=15)
    check("first-level, TLB and predictor residue after a flush",
          st["res_l1d"] + st["res_l1i"] + st["res_tlb"] + st["res_btb"] + st["res_pht"], 0)
    check("predictions made from the other domain's entries, flushed predictors",
          st["xpred"], 0)
    shared = model(pair, quantum=50000)
    rows.append(["cross-domain evictions with no isolation (first level)",
                 shared["l1d_xev"], "> 0", "yes" if shared["l1d_xev"] > 0 else "NO"])
    ok &= shared["l1d_xev"] > 0
    for k in ("matmul", "bstree"):
        a, b = model(k), model(k)
        check("repeatability of cycle count, %s" % k, a["cycles"], b["cycles"])
    write_csv("invariants.csv", ["property", "measured", "required", "holds"], rows)
    return ok


# ----------------------------------------------------------------- experiments
def exp_baseline():
    """E1: where the loads of each kernel are served, and what that costs."""
    rows = []
    for k, st in zip(KERNELS, run_many([(k, {}) for k in KERNELS])):
        n = st["dl_n"]
        p = [st["dl_l1"] / n, st["dl_l2"] / n, st["dl_llc"] / n, st["dl_mem"] / n]
        m1 = 1 - p[0]
        m2 = (p[2] + p[3]) / m1 if m1 else 0.0
        m3 = p[3] / (p[2] + p[3]) if p[2] + p[3] else 0.0
        amat = 4 + m1 * (10 + m2 * (31 + m3 * 175))
        walk, wait = st["dl_walk"] / n, st["dl_wait"] / n
        assert abs(amat + walk + wait - st["dl_sum"] / n) < 1e-6      # exact identity
        rows.append([k, st["inst"], st["cycles"], "%.3f" % (st["inst"] / st["cycles"]),
                     st["load"], st["store"], st["br"],
                     "%.3f" % (100 * st["mis"] / max(1, st["br"])),
                     "%.3f" % (100 * p[0]), "%.3f" % (100 * p[1]), "%.3f" % (100 * p[2]),
                     "%.3f" % (100 * p[3]), "%.3f" % (st["dl_sum"] / n), "%.3f" % amat,
                     "%.3f" % walk, "%.3f" % wait,
                     "%.4f" % (100 * st["tlb_miss"] / max(1, st["tlb_acc"])),
                     st["fwd"], st["jalr"], st["jmis"]])
    write_csv("baseline.csv", ["kernel", "instructions", "cycles", "ipc", "loads", "stores",
                               "branches", "mispredict_pct", "l1_pct", "l2_pct", "llc_pct",
                               "mem_pct", "mean_load_latency", "amat_formula",
                               "walk_per_load", "wait_per_load",
                               "tlb_miss_pct", "forwarded", "indirect", "indirect_mis"], rows)


def exp_cache():
    """E2: sensitivity of each kernel to cache size and associativity."""
    jobs, tags = [], []
    for k in KERNELS:
        for sets in (16, 32, 64, 128, 256):
            jobs.append((k, {"l1sets": sets}))
            tags.append((k, "l1_size_kib", sets * 8 * 64 // 1024))
        for ways in (1, 2, 4, 8, 16):
            jobs.append((k, {"l1ways": ways, "l1sets": 512 // ways}))
            tags.append((k, "l1_ways", ways))
        for sets in (256, 512, 1024, 2048, 4096):
            jobs.append((k, {"llcsets": sets}))
            tags.append((k, "llc_size_kib", sets * 16 * 64 // 1024))
    rows = []
    for (k, what, value), st in zip(tags, run_many(jobs)):
        rows.append([k, what, value, st["cycles"],
                     "%.4f" % (100 * st["l1d_miss"] / st["l1d_acc"]),
                     "%.4f" % (100 * st["llc_miss"] / max(1, st["llc_acc"])),
                     "%.4f" % (1000 * st["llc_miss"] / st["inst"]),
                     "%.3f" % (st["dl_sum"] / st["dl_n"])])
    write_csv("cache_sweep.csv", ["kernel", "parameter", "value", "cycles", "l1d_miss_pct",
                                  "llc_local_miss_pct", "llc_mpki", "mean_load_latency"], rows)


def exp_window():
    """E3: how much transient work fits in the window, against ROB size."""
    jobs, tags = [], []
    for k in KERNELS:
        for rob in (16, 32, 64, 128, 256):
            jobs.append((k, {"rob": rob})); tags.append((k, rob))
    rows = []
    for (k, rob), st in zip(tags, run_many(jobs)):
        squashes = max(1, st["mis"] + st["jmis"])
        rows.append([k, rob, st["cycles"], "%.3f" % (st["inst"] / st["cycles"]),
                     st["mis"] + st["jmis"], st["wp_disp"], st["wp_exec"], st["wp_load"],
                     st["wp_fill"], st["wp_dep"], st["wp_depfill"],
                     "%.3f" % (st["wp_exec"] / squashes), "%.3f" % (st["wp_load"] / squashes),
                     "%.4f" % (st["wp_fill"] / squashes)])
    write_csv("window.csv", ["kernel", "rob", "cycles", "ipc", "squashes", "wp_dispatched",
                             "wp_executed", "wp_loads", "wp_fills", "wp_dependent_loads",
                             "wp_dependent_fills", "executed_per_squash", "loads_per_squash",
                             "fills_per_squash"], rows)
    jobs, tags = [], []
    for k in KERNELS:
        for bp in ("gshare", "bimodal", "nottaken"):
            jobs.append((k, {"bp": bp})); tags.append((k, bp))
    rows = []
    for (k, bp), st in zip(tags, run_many(jobs)):
        rows.append([k, bp, st["cycles"], "%.3f" % (st["inst"] / st["cycles"]),
                     "%.3f" % (100 * st["mis"] / max(1, st["br"])), st["wp_exec"], st["wp_fill"]])
    write_csv("predictor.csv", ["kernel", "predictor", "cycles", "ipc", "mispredict_pct",
                                "wp_executed", "wp_fills"], rows)


def exp_defense():
    """E5: cost and residual transient footprint of each speculation defense."""
    jobs, tags = [], []
    for k in KERNELS:
        for fut in (0, 1):
            for d in DEFENSES:
                jobs.append((k, {"def": d, "fut": fut})); tags.append((k, fut, d))
    res = dict(zip(tags, run_many(jobs)))
    rows = []
    for (k, fut, d), st in res.items():
        base = res[(k, fut, "none")]
        rows.append([k, "futuristic" if fut else "spectre", d, st["cycles"],
                     pct(st["cycles"], base["cycles"]), st["blocked"], st["second"],
                     st["wp_exec"], st["wp_load"], st["wp_fill"], st["wp_dep"],
                     st["wp_depfill"], st["wp_hidden"], st["undo_lines"],
                     st["l1d_acc"] + st["x_l1"], st["l2_acc"] + st["x_l2"],
                     st["llc_acc"] + st["x_llc"], st["llc_miss"] + st["x_mem"]])
    write_csv("defense.csv", ["kernel", "model", "defense", "cycles", "slowdown_pct",
                              "blocked_loads", "second_accesses", "wp_executed", "wp_loads",
                              "wp_fills", "wp_dependent_loads", "wp_dependent_fills",
                              "wp_hidden_fills", "undo_lines", "l1_accesses", "l2_accesses",
                              "llc_accesses", "memory_accesses"], rows)


def exp_sensitivity():
    """How the price of a defense moves with the baseline it is measured on."""
    jobs, tags = [], []
    for name, opts in (("rob", {"rob": r}) for r in (32, 64, 128, 256)):
        for d in DEFENSES:
            for k in KERNELS:
                jobs.append((k, dict(opts, **{"def": d}))); tags.append(("rob", opts["rob"], d, k))
    for width in (2, 4, 8):
        for d in DEFENSES:
            for k in KERNELS:
                jobs.append((k, {"width": width, "def": d})); tags.append(("width", width, d, k))
    for l1 in (2, 4, 6):
        for d in DEFENSES:
            for k in KERNELS:
                jobs.append((k, {"l1": l1, "def": d})); tags.append(("l1_latency", l1, d, k))
    res = dict(zip(tags, run_many(jobs)))
    rows = []
    for what, value in sorted({(t[0], t[1]) for t in tags}):
        base_ipc = [res[(what, value, "none", k)]["inst"] / res[(what, value, "none", k)]["cycles"]
                    for k in KERNELS]
        for d in DEFENSES[1:]:
            ratios = [res[(what, value, d, k)]["cycles"] / res[(what, value, "none", k)]["cycles"]
                      for k in KERNELS]
            geo = math.exp(sum(math.log(r) for r in ratios) / len(ratios))
            rows.append([what, value, d, "%.3f" % (100 * (geo - 1)),
                         "%.3f" % (100 * (max(ratios) - 1)),
                         "%.3f" % math.exp(sum(math.log(i) for i in base_ipc) / len(base_ipc))])
    write_csv("sensitivity.csv", ["parameter", "value", "defense", "geomean_slowdown_pct",
                                  "worst_slowdown_pct", "baseline_geomean_ipc"], rows)


ISOLATION = [
    ("shared", {}),
    ("flush on-core state", {"flush": 15}),
    ("flush + colouring", {"flush": 15, "color": 1}),
    ("colouring only", {"color": 1}),
    ("way partitioning", {"part": 1, "isolbp": 1}),
    ("randomised LLC", {"rnd": 1}),
]


SEEDS = (1, 2, 3, 4, 5)


def exp_domains():
    """E4: two domains sharing one core, under each isolation mechanism. Every
    point is repeated for five page-frame layouts (seeds)."""
    jobs, tags = [], []
    for pair in PAIRS:
        for q in (10000, 30000, 100000, 300000):
            for name, opts in ISOLATION:
                for seed in SEEDS:
                    jobs.append((list(pair), dict(opts, quantum=q, seed=seed)))
                    tags.append((pair, q, name, seed))
    res = dict(zip(tags, run_many(jobs)))
    rows = []
    for (pair, q, name, seed), st in res.items():
        base = res[(pair, q, "shared", seed)]
        sw = max(1, st["nswitch"])
        rows.append(["+".join(pair), q, name, seed, st["cycles"], pct(st["cycles"], base["cycles"]),
                     st["nswitch"], "%.1f" % ((st["cycles"] - base["cycles"]) / sw),
                     st["l1d_xev"], st["l2_xev"], st["llc_xev"], st["tlb_xev"], st["xpred"],
                     "%.1f" % (st["res_l1d"] / sw), "%.1f" % (st["res_l2"] / sw),
                     "%.1f" % (st["res_llc"] / sw), "%.1f" % (st["res_tlb"] / sw),
                     "%.1f" % (st["res_btb"] / sw), "%.1f" % (st["res_pht"] / sw),
                     "%.3f" % (100 * st["mis"] / max(1, st["br"])), st["llc_miss"]])
    write_csv("domains.csv", ["pair", "quantum", "isolation", "seed", "cycles", "slowdown_pct",
                              "switches", "extra_cycles_per_switch", "l1d_cross_evictions",
                              "l2_cross_evictions", "llc_cross_evictions", "tlb_cross_evictions",
                              "cross_predictions", "residue_l1d", "residue_l2", "residue_llc",
                              "residue_tlb", "residue_btb", "residue_pht", "mispredict_pct",
                              "memory_accesses"], rows)


def exp_seeds():
    """Spread of the single-program results over page-frame layouts."""
    jobs, tags = [], []
    for k in KERNELS:
        for seed in SEEDS:
            for d in ("none", "dom", "stt"):
                jobs.append((k, {"seed": seed, "def": d})); tags.append((k, seed, d))
    res = dict(zip(tags, run_many(jobs)))
    rows = [[k, seed, d, st["cycles"], pct(st["cycles"], res[(k, seed, "none")]["cycles"]),
             st["llc_miss"]] for (k, seed, d), st in res.items()]
    write_csv("seeds.csv", ["kernel", "seed", "defense", "cycles", "slowdown_pct",
                            "memory_accesses"], rows)


def exp_random():
    """Cost of an encrypted, gradually remapped last-level cache index."""
    jobs, tags = [], []
    for k in KERNELS:
        jobs.append((k, {})); tags.append((k, "none", 0))
        jobs.append((k, {"rnd": 1, "rndlat": 0, "remap": 1 << 30}))
        tags.append((k, "static key, no latency", 0))
        for remap in (100, 400, 1600, 6400):
            jobs.append((k, {"rnd": 1, "remap": remap})); tags.append((k, "remapped", remap))
    res = dict(zip(tags, run_many(jobs)))
    rows = []
    for (k, mode, remap), st in res.items():
        base = res[(k, "none", 0)]
        rows.append([k, mode, remap, st["cycles"], pct(st["cycles"], base["cycles"]),
                     st["llc_acc"], st["llc_miss"], st["llc_remapev"]])
    write_csv("random.csv", ["kernel", "mode", "accesses_per_remapped_set", "cycles",
                             "slowdown_pct", "llc_accesses", "llc_misses", "remap_evictions"], rows)


def exp_composition():
    """E7: do the costs of two defenses add when both are switched on? Every
    combination is run for five page-frame layouts; the means are reported
    together with the spread of the excess over the product."""
    combos = [("flush + colouring", {"flush": 15, "color": 1}, "stt", {"def": "stt"}),
              ("flush + colouring", {"flush": 15, "color": 1}, "dom", {"def": "dom"}),
              ("way partitioning", {"part": 1, "isolbp": 1}, "stt", {"def": "stt"}),
              ("way partitioning", {"part": 1, "isolbp": 1}, "invis-v", {"def": "invis-v"}),
              ("randomised LLC", {"rnd": 1}, "nda", {"def": "nda"})]
    jobs, tags = [], []
    for pair in PAIRS:
        for na, oa, nb, ob in combos:
            for label, opts in (("none", {}), ("a", oa), ("b", ob), ("ab", dict(oa, **ob))):
                for seed in SEEDS:
                    jobs.append((list(pair), dict(opts, quantum=100000, seed=seed)))
                    tags.append((pair, na, nb, label, seed))
    res = dict(zip(tags, run_many(jobs)))
    mean = lambda xs: sum(xs) / len(xs)
    rows = []
    for pair in PAIRS:
        for na, _, nb, _ in combos:
            sa, sb, sab, prod, excess = [], [], [], [], []
            for seed in SEEDS:
                c = {l: res[(pair, na, nb, l, seed)]["cycles"] for l in ("none", "a", "b", "ab")}
                a, b, ab = (100 * (c[l] / c["none"] - 1) for l in ("a", "b", "ab"))
                p = 100 * ((1 + a / 100) * (1 + b / 100) - 1)
                sa.append(a); sb.append(b); sab.append(ab); prod.append(p); excess.append(ab - p)
            rows.append(["+".join(pair), na, nb, "%.3f" % mean(sa), "%.3f" % mean(sb),
                         "%.3f" % mean(sab), "%.3f" % mean(prod), "%.3f" % mean(excess),
                         "%.3f" % min(excess), "%.3f" % max(excess),
                         "%.3f" % (mean(sab) - mean(sa) - mean(sb))])
    write_csv("composition.csv", ["pair", "isolation", "speculation_defense", "s_a_pct",
                                  "s_b_pct", "s_ab_pct", "product_pct", "excess_pct",
                                  "excess_min_pct", "excess_max_pct", "excess_over_sum_pct"], rows)


def manifest():
    def digest(path):
        return hashlib.sha256(open(path, "rb").read()).hexdigest()

    files = ["rvmodel.c", "rvasm.py", "reference.py", "run_study.py"]
    files += ["workloads/%s.s" % k for k in ["crt"] + KERNELS]
    info = {
        "sources_sha256": {f: digest(os.path.join(HERE, f)) for f in files},
        "results_sha256": {f: digest(os.path.join(RESULTS, f))
                           for f in sorted(os.listdir(RESULTS)) if f.endswith(".csv")},
        "qemu": sh(["qemu-system-riscv64", "--version"]).splitlines()[0],
        "cc": sh(["cc", "--version"]).splitlines()[0],
        "python": sys.version.split()[0],
    }
    with open(os.path.join(RESULTS, "manifest.json"), "w") as f:
        json.dump(info, f, indent=1, sort_keys=True)
        f.write("\n")


def main():
    build()
    good = validate_kernels() and unit_tests() and invariants()
    print("validation:", "PASS" if good else "FAIL")
    if not good:
        sys.exit(1)
    if len(sys.argv) > 1 and sys.argv[1] == "validate":
        return
    exp_baseline()
    exp_cache()
    exp_window()
    exp_defense()
    exp_sensitivity()
    exp_domains()
    exp_seeds()
    exp_random()
    exp_composition()
    manifest()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""rvasm.py - a small two-pass assembler for the RV64IM subset used by the
study kernels of the ELL 305 term paper.

It produces a flat memory image (loaded at 0x80000000, the RAM base of the
QEMU 'virt' machine) and a minimal ELF64 executable wrapping the same image,
so that one binary runs both on the timing model (rvmodel) and on QEMU.

Supported: all RV64I integer instructions, the M extension, the usual
pseudo-instructions (li, la, mv, j, call, ret, beqz, bgt, ...), labels,
.text/.data, .equ, .align, .byte/.half/.word/.dword and .zero.
"""
import re
import struct
import sys

BASE = 0x80000000
PAGE = 4096

ABI = ("zero ra sp gp tp t0 t1 t2 s0 s1 a0 a1 a2 a3 a4 a5 a6 a7 "
       "s2 s3 s4 s5 s6 s7 s8 s9 s10 s11 t3 t4 t5 t6").split()
REG = {"x%d" % i: i for i in range(32)}
REG.update({n: i for i, n in enumerate(ABI)})
REG["fp"] = 8

# name: (funct7, funct3, opcode)
RTYPE = {
    "add": (0x00, 0, 0x33), "sub": (0x20, 0, 0x33), "sll": (0x00, 1, 0x33),
    "slt": (0x00, 2, 0x33), "sltu": (0x00, 3, 0x33), "xor": (0x00, 4, 0x33),
    "srl": (0x00, 5, 0x33), "sra": (0x20, 5, 0x33), "or": (0x00, 6, 0x33),
    "and": (0x00, 7, 0x33),
    "addw": (0x00, 0, 0x3B), "subw": (0x20, 0, 0x3B), "sllw": (0x00, 1, 0x3B),
    "srlw": (0x00, 5, 0x3B), "sraw": (0x20, 5, 0x3B),
    "mul": (0x01, 0, 0x33), "mulh": (0x01, 1, 0x33), "mulhsu": (0x01, 2, 0x33),
    "mulhu": (0x01, 3, 0x33), "div": (0x01, 4, 0x33), "divu": (0x01, 5, 0x33),
    "rem": (0x01, 6, 0x33), "remu": (0x01, 7, 0x33),
    "mulw": (0x01, 0, 0x3B), "divw": (0x01, 4, 0x3B), "divuw": (0x01, 5, 0x3B),
    "remw": (0x01, 6, 0x3B), "remuw": (0x01, 7, 0x3B),
}
# name: (funct3, opcode)
ITYPE = {
    "addi": (0, 0x13), "slti": (2, 0x13), "sltiu": (3, 0x13), "xori": (4, 0x13),
    "ori": (6, 0x13), "andi": (7, 0x13), "addiw": (0, 0x1B),
}
# name: (upper immediate bits, funct3, opcode, shamt width)
SHIFT = {
    "slli": (0x00, 1, 0x13, 6), "srli": (0x00, 5, 0x13, 6),
    "srai": (0x10, 5, 0x13, 6),
    "slliw": (0x00, 1, 0x1B, 5), "srliw": (0x00, 5, 0x1B, 5),
    "sraiw": (0x20, 5, 0x1B, 5),
}
LOAD = {"lb": 0, "lh": 1, "lw": 2, "ld": 3, "lbu": 4, "lhu": 5, "lwu": 6}
STORE = {"sb": 0, "sh": 1, "sw": 2, "sd": 3}
BRANCH = {"beq": 0, "bne": 1, "blt": 4, "bge": 5, "bltu": 6, "bgeu": 7}


class AsmError(Exception):
    pass


def sext(value, bits):
    value &= (1 << bits) - 1
    return value - (1 << bits) if value >> (bits - 1) else value


def li_sequence(rd, value):
    """Instructions that load the signed 64-bit constant `value` into rd."""
    value = sext(value, 64)
    if -2048 <= value < 2048:
        return [("addi", [rd, "x0", str(value)])]
    if -(1 << 31) <= value < (1 << 31):
        hi = ((value + 0x800) >> 12) & 0xFFFFF
        lo = sext(value, 12)
        seq = [("lui", [rd, str(hi)])]
        if lo:
            seq.append(("addiw", [rd, rd, str(lo)]))
        return seq
    lo = sext(value, 12)
    hi = (value - lo) >> 12
    shift = 12
    while hi & 1 == 0:
        hi >>= 1
        shift += 1
    seq = li_sequence(rd, hi) + [("slli", [rd, rd, str(shift)])]
    if lo:
        seq.append(("addi", [rd, rd, str(lo)]))
    return seq


class Assembler:
    def __init__(self):
        self.sym = {}
        self.items = {"text": [], "data": []}   # (kind, payload, line number)
        self.size = {"text": 0, "data": 0}
        self.labels = []                         # (name, section, offset)

    # ---------------------------------------------------------------- values
    def value(self, expr, lineno):
        expr = expr.strip()
        if not re.fullmatch(r"[\w\s+\-*/()<>&|^~']+", expr):
            raise AsmError("line %d: bad expression %r" % (lineno, expr))
        expr = re.sub(r"'(.)'", lambda m: str(ord(m.group(1))), expr)

        def symbol(m):
            if m.group(1):                       # a numeric literal
                return m.group(1)
            if m.group(2) not in self.sym:
                raise AsmError("line %d: undefined symbol %r" % (lineno, m.group(2)))
            return str(self.sym[m.group(2)])

        expr = re.sub(r"(0[xX][0-9a-fA-F]+|\d+)|([A-Za-z_.][\w.]*)", symbol, expr)
        try:
            return int(eval(expr, {"__builtins__": {}}, {}))
        except AsmError:
            raise
        except Exception as exc:
            raise AsmError("line %d: cannot evaluate %r (%s)" % (lineno, expr, exc))

    @staticmethod
    def reg(name, lineno):
        try:
            return REG[name.strip()]
        except KeyError:
            raise AsmError("line %d: unknown register %r" % (lineno, name))

    # ------------------------------------------------------------- pseudo-ops
    def expand(self, mn, ops, lineno):
        """Rewrite a pseudo-instruction as a list of base instructions."""
        zero = "x0"
        if mn == "nop":
            return [("addi", [zero, zero, "0"])]
        if mn == "li":
            return li_sequence(ops[0], self.value(ops[1], lineno))
        if mn == "la":
            return [("la_hi", ops), ("la_lo", ops)]
        if mn == "mv":
            return [("addi", [ops[0], ops[1], "0"])]
        if mn == "not":
            return [("xori", [ops[0], ops[1], "-1"])]
        if mn == "neg":
            return [("sub", [ops[0], zero, ops[1]])]
        if mn == "negw":
            return [("subw", [ops[0], zero, ops[1]])]
        if mn == "sext.w":
            return [("addiw", [ops[0], ops[1], "0"])]
        if mn == "seqz":
            return [("sltiu", [ops[0], ops[1], "1"])]
        if mn == "snez":
            return [("sltu", [ops[0], zero, ops[1]])]
        if mn == "sltz":
            return [("slt", [ops[0], ops[1], zero])]
        if mn == "sgtz":
            return [("slt", [ops[0], zero, ops[1]])]
        if mn in ("beqz", "bnez", "bgez", "bltz"):
            return [({"beqz": "beq", "bnez": "bne", "bgez": "bge",
                      "bltz": "blt"}[mn], [ops[0], zero, ops[1]])]
        if mn in ("blez", "bgtz"):
            return [({"blez": "bge", "bgtz": "blt"}[mn], [zero, ops[0], ops[1]])]
        if mn in ("bgt", "ble", "bgtu", "bleu"):
            return [({"bgt": "blt", "ble": "bge", "bgtu": "bltu",
                      "bleu": "bgeu"}[mn], [ops[1], ops[0], ops[2]])]
        if mn == "j":
            return [("jal", [zero, ops[0]])]
        if mn == "jr":
            return [("jalr", [zero, "0(%s)" % ops[0]])]
        if mn == "ret":
            return [("jalr", [zero, "0(ra)"])]
        if mn == "call":
            return [("jal", ["ra", ops[0]])]
        if mn == "tail":
            return [("jal", [zero, ops[0]])]
        if mn == "jal" and len(ops) == 1:
            return [("jal", ["ra", ops[0]])]
        return [(mn, ops)]

    # ----------------------------------------------------------------- pass 1
    def parse(self, text):
        sec = "text"
        for lineno, raw in enumerate(text.splitlines(), 1):
            line = raw.split("#", 1)[0].strip()
            while True:
                m = re.match(r"^([A-Za-z_.][\w.]*):\s*", line)
                if not m:
                    break
                self.labels.append((m.group(1), sec, self.size[sec]))
                line = line[m.end():]
            if not line:
                continue
            parts = line.split(None, 1)
            mn = parts[0].lower()
            ops = [o.strip() for o in parts[1].split(",")] if len(parts) > 1 else []
            if mn in (".text", ".data"):
                sec = mn[1:]
            elif mn in (".globl", ".global", ".section", ".type", ".size"):
                pass
            elif mn == ".equ":
                self.sym[ops[0]] = self.value(ops[1], lineno)
            elif mn == ".align":
                align = 1 << self.value(ops[0], lineno)
                pad = -self.size[sec] % align
                self.emit(sec, "zero", pad, lineno)
            elif mn == ".zero":
                self.emit(sec, "zero", self.value(ops[0], lineno), lineno)
            elif mn in (".byte", ".half", ".word", ".dword"):
                width = {".byte": 1, ".half": 2, ".word": 4, ".dword": 8}[mn]
                for op in ops:
                    self.emit(sec, "data", (width, op), lineno)
            elif mn.startswith("."):
                raise AsmError("line %d: unknown directive %s" % (lineno, mn))
            else:
                for base_mn, base_ops in self.expand(mn, ops, lineno):
                    self.emit(sec, "insn", (base_mn, base_ops), lineno)

    def emit(self, sec, kind, payload, lineno):
        size = {"insn": 4, "zero": payload if kind == "zero" else 0,
                "data": payload[0] if kind == "data" else 0}[kind]
        self.items[sec].append((kind, payload, lineno, self.size[sec]))
        self.size[sec] += size

    # ----------------------------------------------------------------- pass 2
    def encode(self, mn, ops, pc, lineno):
        reg, val = self.reg, self.value

        def mem_operand(text):
            m = re.fullmatch(r"(.*)\((\w+)\)", text.strip())
            if not m:
                raise AsmError("line %d: bad memory operand %r" % (lineno, text))
            off = val(m.group(1), lineno) if m.group(1).strip() else 0
            return off, reg(m.group(2), lineno)

        def check(imm, bits, what):
            if not -(1 << (bits - 1)) <= imm < (1 << (bits - 1)):
                raise AsmError("line %d: %s %d out of range" % (lineno, what, imm))
            return imm & ((1 << bits) - 1)

        if mn in RTYPE:
            f7, f3, opc = RTYPE[mn]
            return (f7 << 25 | reg(ops[2], lineno) << 20 | reg(ops[1], lineno) << 15
                    | f3 << 12 | reg(ops[0], lineno) << 7 | opc)
        if mn in ITYPE:
            f3, opc = ITYPE[mn]
            imm = check(val(ops[2], lineno), 12, "immediate")
            return (imm << 20 | reg(ops[1], lineno) << 15 | f3 << 12
                    | reg(ops[0], lineno) << 7 | opc)
        if mn in SHIFT:
            top, f3, opc, width = SHIFT[mn]
            sh = val(ops[2], lineno)
            if not 0 <= sh < (1 << width):
                raise AsmError("line %d: shift amount %d out of range" % (lineno, sh))
            imm = (top << 6 | sh) if width == 6 else (top << 5 | sh)
            return (imm << 20 | reg(ops[1], lineno) << 15 | f3 << 12
                    | reg(ops[0], lineno) << 7 | opc)
        if mn in LOAD:
            off, base = mem_operand(ops[1])
            return (check(off, 12, "offset") << 20 | base << 15 | LOAD[mn] << 12
                    | reg(ops[0], lineno) << 7 | 0x03)
        if mn in STORE:
            off, base = mem_operand(ops[1])
            imm = check(off, 12, "offset")
            return ((imm >> 5) << 25 | reg(ops[0], lineno) << 20 | base << 15
                    | STORE[mn] << 12 | (imm & 31) << 7 | 0x23)
        if mn in BRANCH:
            off = val(ops[2], lineno) - pc
            if off & 1:
                raise AsmError("line %d: odd branch offset" % lineno)
            imm = check(off, 13, "branch offset")
            return ((imm >> 12 & 1) << 31 | (imm >> 5 & 0x3F) << 25
                    | reg(ops[1], lineno) << 20 | reg(ops[0], lineno) << 15
                    | BRANCH[mn] << 12 | (imm >> 1 & 0xF) << 8
                    | (imm >> 11 & 1) << 7 | 0x63)
        if mn == "jal":
            imm = check(val(ops[1], lineno) - pc, 21, "jump offset")
            return ((imm >> 20 & 1) << 31 | (imm >> 1 & 0x3FF) << 21
                    | (imm >> 11 & 1) << 20 | (imm >> 12 & 0xFF) << 12
                    | reg(ops[0], lineno) << 7 | 0x6F)
        if mn == "jalr":
            if len(ops) == 2:
                off, base = mem_operand(ops[1])
            else:
                off, base = val(ops[2], lineno), reg(ops[1], lineno)
            return (check(off, 12, "offset") << 20 | base << 15
                    | reg(ops[0], lineno) << 7 | 0x67)
        if mn in ("lui", "auipc"):
            imm = val(ops[1], lineno)
            if not 0 <= imm < (1 << 20):
                raise AsmError("line %d: upper immediate out of range" % lineno)
            return imm << 12 | reg(ops[0], lineno) << 7 | (0x37 if mn == "lui" else 0x17)
        if mn in ("la_hi", "la_lo"):
            off = val(ops[1], lineno) - (pc if mn == "la_hi" else pc - 4)
            hi = (off + 0x800) >> 12
            rd = reg(ops[0], lineno)
            if mn == "la_hi":
                return (hi & 0xFFFFF) << 12 | rd << 7 | 0x17
            return ((off - (hi << 12)) & 0xFFF) << 20 | rd << 15 | rd << 7 | 0x13
        if mn == "ecall":
            return 0x00000073
        if mn == "ebreak":
            return 0x00100073
        if mn == "fence":
            return 0x0FF0000F
        raise AsmError("line %d: unknown instruction %r" % (lineno, mn))

    def assemble(self, text):
        self.parse(text)
        data_base = BASE + (self.size["text"] + PAGE - 1) // PAGE * PAGE
        start = {"text": BASE, "data": data_base}
        for name, sec, off in self.labels:
            if name in self.sym:
                raise AsmError("duplicate symbol %s" % name)
            self.sym[name] = start[sec] + off
        image = bytearray(data_base - BASE + self.size["data"])
        for sec in ("text", "data"):
            for kind, payload, lineno, off in self.items[sec]:
                addr = start[sec] + off
                pos = addr - BASE
                if kind == "insn":
                    word = self.encode(payload[0], payload[1], addr, lineno)
                    image[pos:pos + 4] = struct.pack("<I", word & 0xFFFFFFFF)
                elif kind == "data":
                    width, expr = payload
                    value = self.value(expr, lineno) & ((1 << (8 * width)) - 1)
                    image[pos:pos + width] = value.to_bytes(width, "little")
        return bytes(image)


def make_elf(image):
    """Wrap the image in a minimal static ELF64 with one loadable segment."""
    filesz = len(image.rstrip(b"\0"))
    filesz = (filesz + 7) // 8 * 8
    ehdr = struct.pack("<16sHHIQQQIHHHHHH", b"\x7fELF\x02\x01\x01" + bytes(9),
                       2, 243, 1, BASE, 64, 0, 0, 64, 56, 1, 0, 0, 0)
    phdr = struct.pack("<IIQQQQQQ", 1, 7, PAGE, BASE, BASE, filesz, len(image), PAGE)
    return (ehdr + phdr).ljust(PAGE, b"\0") + image[:filesz]


def assemble_files(paths):
    asm = Assembler()
    text = "\n".join(open(p).read() for p in paths)
    return asm.assemble(text), asm.sym


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("usage: rvasm.py OUT_PREFIX file.s [file.s ...]")
    try:
        img, symbols = assemble_files(sys.argv[2:])
    except AsmError as err:
        sys.exit("rvasm: %s" % err)
    with open(sys.argv[1] + ".bin", "wb") as f:
        f.write(img)
    with open(sys.argv[1] + ".elf", "wb") as f:
        f.write(make_elf(img))
    with open(sys.argv[1] + ".sym", "w") as f:
        for name in sorted(symbols, key=lambda n: symbols[n]):
            f.write("%016x %s\n" % (symbols[name] & (2**64 - 1), name))

#!/usr/bin/env python3
"""reference.py - independent Python implementations of the ten study kernels.

Each function recomputes, in ordinary Python, the 64-bit checksum that the
corresponding assembly kernel returns in a0. A kernel is accepted only if this
value, the value printed by QEMU and the value printed by rvmodel all agree.
"""
import zlib

M64 = (1 << 64) - 1
LCG_A = 0x5851F42D4C957F2D
LCG_C = 0x14057B7EF767814F


def lcg(x):
    return (x * LCG_A + LCG_C) & M64


def s32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v >> 31 else v


def matmul():
    n = 64
    a = [[i + 2 * j + 1 for j in range(n)] for i in range(n)]
    b = [[3 * i - j + 2 for j in range(n)] for i in range(n)]
    acc = 0
    for i in range(n):
        for j in range(n):
            c = s32(sum(a[i][k] * b[k][j] for k in range(n)))
            acc = (acc * 31 + c) & M64
    return acc


def heapsort():
    x, keys = 12345, []
    for _ in range(8192):
        x = lcg(x)
        keys.append(x >> 16)
    keys.sort()
    return sum(v * (i + 1) for i, v in enumerate(keys)) & M64


def listwalk():
    n = 16384
    perm, x = list(range(n)), 2024
    for i in range(n - 1, 0, -1):
        x = lcg(x)
        j = (x >> 33) % (i + 1)
        perm[i], perm[j] = perm[j], perm[i]
    acc = 0
    for _ in range(6):
        for idx in perm:
            acc = (acc * 31 + 7 * idx + 1) & M64
    return acc


def bsearch():
    n = 65536
    keys = [3 * i + 1 for i in range(n)]
    x, acc = 777, 0
    for _ in range(16000):
        x = lcg(x)
        key = (x >> 40) % 196608
        lo, hi, found = 0, n - 1, 0
        while lo <= hi:
            mid = (lo + hi) >> 1
            if keys[mid] == key:
                found = mid + 1
                break
            if keys[mid] < key:
                lo = mid + 1
            else:
                hi = mid - 1
        acc = (acc * 31 + found) & M64
    return acc


def crc32():
    x, buf = 99, bytearray()
    for _ in range(32768):
        x = lcg(x)
        buf += x.to_bytes(8, "little")
    return zlib.crc32(bytes(buf)) & 0xFFFFFFFF


def sieve():
    n = 200000
    flags = bytearray(n)
    p = 2
    while p * p < n:
        if not flags[p]:
            for m in range(p * p, n, p):
                flags[m] = 1
        p += 1
    return sum(i for i in range(2, n) if not flags[i]) & M64


def hashtab():
    slots, mask = 16384, 16383
    keys, vals = [0] * slots, [0] * slots

    def slot_of(key):
        return ((key * 0x9E3779B97F4A7C15) & M64) >> 50

    x = 4242
    for i in range(10000):
        x = lcg(x)
        key = (x >> 20) | 1
        s = slot_of(key)
        while keys[s] and keys[s] != key:
            s = (s + 1) & mask
        keys[s], vals[s] = key, i
    xa, xb, acc = 4242, 1717, 0
    for q in range(80000):
        if q & 1:
            xb = lcg(xb)
            key = (xb >> 20) | 1
        else:
            xa = lcg(xa)
            key = (xa >> 20) | 1
        s, found = slot_of(key), 0
        while keys[s]:
            if keys[s] == key:
                found = vals[s] + 1
                break
            s = (s + 1) & mask
        acc = (acc * 31 + found) & M64
    return acc


def stream():
    n = 49152
    b = list(range(n))
    c = [2 * i + 1 for i in range(n)]
    a = [0] * n
    for left in (3, 2, 1):
        for i in range(n):
            a[i] = b[i] = (b[i] + 3 * c[i] + left) & M64
    acc = 0
    for v in a:
        acc = (acc * 31 + v) & M64
    return acc


def fibcall():
    a, b = 0, 1
    for _ in range(25):
        a, b = b, a + b
    return a


def strsearch():
    n, plen = 120000, 6
    x, text = 31337, bytearray()
    for _ in range(n):
        x = lcg(x)
        text.append(97 + (x >> 62))
    pat = bytes(text[1000:1000 + plen])
    acc = 0
    for i in range(n - plen + 1):
        if text[i:i + plen] == pat:
            acc = (acc * 31 + i + 1) & M64
    return acc


def bstree():
    key, left, right, val = [0], [0], [0], [0]     # node 0 is the root

    def insert(k, number):
        node = 0
        while True:
            if key[node] == k:
                return
            child = left if k < key[node] else right
            if not child[node]:
                child[node] = len(key)
                key.append(k), left.append(0), right.append(0), val.append(number)
                return
            node = child[node]

    x = lcg(5150)
    key[0] = x >> 24
    for number in range(1, 8192):
        x = lcg(x)
        insert(x >> 24, number)
    xa, xb, acc = 5150, 8086, 0
    for q in range(30000):
        if q & 1:
            xb = lcg(xb)
            k = xb >> 24
        else:
            xa = lcg(xa)
            k = xa >> 24
        node, found = 0, 0
        while True:
            if key[node] == k:
                found = val[node] + 1
                break
            node = left[node] if k < key[node] else right[node]
            if not node:
                break
        acc = (acc * 31 + found) & M64
    return acc


KERNELS = ["matmul", "heapsort", "listwalk", "bsearch", "bstree", "crc32",
           "sieve", "hashtab", "stream", "fibcall", "strsearch"]


def expected(name):
    return "%016x" % globals()[name]()


if __name__ == "__main__":
    for kernel in KERNELS:
        print(kernel, expected(kernel))
